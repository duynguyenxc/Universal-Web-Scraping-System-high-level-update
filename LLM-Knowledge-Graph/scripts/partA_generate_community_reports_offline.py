from __future__ import annotations

import argparse
import ast
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


def _as_list(v: Any) -> list[str]:
    if v is None:
        return []
    # numpy/pandas arrays
    if hasattr(v, "tolist") and callable(getattr(v, "tolist")):
        try:
            out = v.tolist()
            if isinstance(out, list):
                return [str(x) for x in out if str(x).strip()]
        except Exception:
            return []
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    if isinstance(v, tuple):
        return [str(x) for x in v if str(x).strip()]
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return []
        # Parquet can round-trip lists as python lists, but be defensive in case of stringified lists.
        if (s.startswith("[") and s.endswith("]")) or (s.startswith("(") and s.endswith(")")):
            try:
                out = ast.literal_eval(s)
                if isinstance(out, (list, tuple)):
                    return [str(x) for x in out if str(x).strip()]
            except Exception:
                return []
        return [s]
    return [str(v)]


def _md_escape(s: str) -> str:
    return (s or "").replace("\r\n", "\n").replace("\r", "\n")


@dataclass(frozen=True)
class ReportRow:
    community: int
    level: int
    title: str
    size: int
    rank: float
    summary: str
    full_content: str


def _build_report(
    *,
    com: pd.Series,
    entities: pd.DataFrame,
    rels: pd.DataFrame,
    e_by_id: dict[str, dict[str, Any]],
    r_by_id: dict[str, dict[str, Any]],
    max_entities: int,
    max_relationships: int,
) -> ReportRow:
    cid = int(com.get("community", 0))
    level = int(com.get("level", 0))
    title = str(com.get("title") or "").strip() or f"Community {cid}"
    size = int(com.get("size", 0) or 0)
    rank = float(size)

    eids = _as_list(com.get("entity_ids"))
    rids = _as_list(com.get("relationship_ids"))

    ent_rows: list[dict[str, Any]] = [e_by_id[eid] for eid in eids if eid in e_by_id]
    rel_rows: list[dict[str, Any]] = [r_by_id[rid] for rid in rids if rid in r_by_id]

    # Entities: prioritize hubs
    def ekey(r: dict[str, Any]) -> tuple[float, float, str]:
        return (float(r.get("degree") or 0), float(r.get("frequency") or 0), str(r.get("title") or ""))

    ent_rows = sorted(ent_rows, key=ekey, reverse=True)
    top_ents = ent_rows[:max_entities]

    # Relationships: prioritize heavier edges (GraphRAG weight is already aggregated)
    def rkey(r: dict[str, Any]) -> tuple[float, float]:
        return (float(r.get("weight") or 0), float(r.get("combined_degree") or 0))

    rel_rows = sorted(rel_rows, key=rkey, reverse=True)
    top_rels = rel_rows[:max_relationships]

    types = [str(r.get("type") or "").strip() for r in top_ents if str(r.get("type") or "").strip()]
    type_counts = Counter(types)
    top_types = ", ".join([f"{t}={n}" for t, n in type_counts.most_common(6)]) if type_counts else "n/a"

    ent_lines = []
    for r in top_ents:
        et = str(r.get("type") or "").strip()
        tt = str(r.get("title") or "").strip()
        deg = int(r.get("degree") or 0)
        freq = int(r.get("frequency") or 0)
        if not tt:
            continue
        ent_lines.append(f"- **{_md_escape(tt)}** ({et or 'UNKNOWN'}; degree={deg}, freq={freq})")

    rel_lines = []
    for r in top_rels:
        src = str(r.get("source") or "").strip()
        tgt = str(r.get("target") or "").strip()
        desc = str(r.get("description") or "").strip()
        w = float(r.get("weight") or 0)
        hid = r.get("human_readable_id", "")
        rel_lines.append(f"- **{_md_escape(src)} → {_md_escape(tgt)}** (w={w:g}, rel={hid}): {_md_escape(desc)}")

    summary = (
        f"Offline (no-LLM) community report. size={size}, level={level}. "
        f"Type mix (top): {top_types}. "
        f"Top entities/edges are selected by degree/frequency and weight."
    )

    md: list[str] = []
    md.append(f"# {title}")
    md.append("")
    md.append(summary)
    md.append("")
    md.append("## Key entities (auto-picked)")
    md.append("")
    md.extend(ent_lines if ent_lines else ["- _(none)_"])
    md.append("")
    md.append("## Key relationships (auto-picked)")
    md.append("")
    md.extend(rel_lines if rel_lines else ["- _(none)_"])
    md.append("")
    md.append("## Traceability")
    md.append("")
    md.append("- These findings are derived from `communities.parquet` membership lists.")
    md.append("- Use `rel=<human_readable_id>` to locate the exact row in `relationships.parquet` / `human_readable/relationships.md`.")
    md.append("- This report is a fallback when LLM-based `create_community_reports` cannot run (quota/rate limits).")
    md.append("")

    full_content = "\n".join(md).strip() + "\n"

    return ReportRow(
        community=cid,
        level=level,
        title=title,
        size=size,
        rank=rank,
        summary=summary,
        full_content=full_content,
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate community_reports.parquet without LLM calls (fallback for quota/rate limit failures)."
    )
    ap.add_argument("--out-dir", type=Path, required=True, help="GraphRAG output directory.")
    ap.add_argument("--max-entities", type=int, default=12, help="Top entities to include per community.")
    ap.add_argument("--max-relationships", type=int, default=12, help="Top relationships to include per community.")
    args = ap.parse_args()

    out_dir: Path = args.out_dir
    com_p = out_dir / "communities.parquet"
    ent_p = out_dir / "entities.parquet"
    rel_p = out_dir / "relationships.parquet"
    if not com_p.exists():
        raise SystemExit(f"Missing: {com_p}")
    if not ent_p.exists():
        raise SystemExit(f"Missing: {ent_p}")
    if not rel_p.exists():
        raise SystemExit(f"Missing: {rel_p}")

    communities = pd.read_parquet(com_p)
    entities = pd.read_parquet(ent_p)
    rels = pd.read_parquet(rel_p)

    # Indexes for fast lookup
    e_by_id: dict[str, dict[str, Any]] = (
        entities.set_index("id")[["human_readable_id", "title", "type", "frequency", "degree"]]
        .fillna("")
        .to_dict(orient="index")
    )
    r_by_id: dict[str, dict[str, Any]] = (
        rels.set_index("id")[["human_readable_id", "source", "target", "description", "weight", "combined_degree"]]
        .fillna("")
        .to_dict(orient="index")
    )

    rows: list[ReportRow] = []
    # Prefer level 0 communities (leaf-ish) for readability; keep all levels to match GraphRAG output shape.
    for _, com in communities.iterrows():
        rows.append(
            _build_report(
                com=com,
                entities=entities,
                rels=rels,
                e_by_id=e_by_id,
                r_by_id=r_by_id,
                max_entities=args.max_entities,
                max_relationships=args.max_relationships,
            )
        )

    out_df = pd.DataFrame([r.__dict__ for r in rows])
    out_p = out_dir / "community_reports.parquet"
    out_df.to_parquet(out_p, index=False)
    print(f"Wrote: {out_p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

