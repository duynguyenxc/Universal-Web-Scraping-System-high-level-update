from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

@dataclass
class QualityGates:
    entities_rows: int | None = None
    entities_blank_type: int | None = None
    entities_corrupt_title: int | None = None
    relationships_rows: int | None = None
    relationships_cmo_edges: int | None = None
    relationships_cmo_pct: float | None = None


@dataclass
class ClaimsStats:
    rows: int = 0
    with_page: int = 0
    with_cmo_tag: int = 0
    missing_subject: int = 0
    missing_object: int = 0
    missing_source_text: int = 0


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.upper()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _parse_quality_gates(md: str) -> QualityGates:
    q = QualityGates()
    m = re.search(r"### Entities.*?- rows:\s+\*\*(\d+)\*\*", md, flags=re.S)
    if m:
        q.entities_rows = int(m.group(1))
    m = re.search(r"blank type count:\s+\*\*(\d+)\*\*", md, flags=re.I)
    if m:
        q.entities_blank_type = int(m.group(1))
    m = re.search(r"corrupt title count:\s+\*\*(\d+)\*\*", md, flags=re.I)
    if m:
        q.entities_corrupt_title = int(m.group(1))

    m = re.search(r"### Relationships.*?- rows:\s+\*\*(\d+)\*\*", md, flags=re.S)
    if m:
        q.relationships_rows = int(m.group(1))
    # Legacy format
    m = re.search(r"CMO-ish edges:\s+\*\*(\d+)\s*/\s*(\d+)\s*=\s*([0-9.]+)%\*\*", md, flags=re.I)
    if m:
        q.relationships_cmo_edges = int(m.group(1))
        q.relationships_cmo_pct = float(m.group(3))
        if q.relationships_rows is None:
            q.relationships_rows = int(m.group(2))
    # Current format (prefer normalized types if present)
    m2 = re.search(r"CMOC-family edges \(normalized types\):\s+\*\*(\d+)\s*/\s*(\d+)\s*=\s*([0-9.]+)%\*\*", md, flags=re.I)
    if m2:
        q.relationships_cmo_edges = int(m2.group(1))
        q.relationships_cmo_pct = float(m2.group(3))
        if q.relationships_rows is None:
            q.relationships_rows = int(m2.group(2))
    return q


def _iter_markdown_table_rows(md: str) -> Iterable[list[str]]:
    """
    Minimal markdown table parser:
    - Finds a header row starting with | ... |
    - Skips separator rows like |---|
    - Returns row cells with stripped values
    """
    lines = [ln.rstrip("\n") for ln in md.splitlines()]
    for ln in lines:
        if not (ln.startswith("|") and ln.endswith("|")):
            continue
        # separator row
        if re.fullmatch(r"\|\s*:?[- ]+:?\s*(\|\s*:?[- ]+:?\s*)+\|", ln):
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        yield cells


def _parse_claims_fixed_md(md: str) -> ClaimsStats:
    stats = ClaimsStats()

    # Try to extract declared rows, if present.
    m = re.search(r"- rows:\s+\*\*(\d+)\*\*", md)
    declared_rows = int(m.group(1)) if m else None

    header = None
    idx = {}
    rows_seen = 0

    for cells in _iter_markdown_table_rows(md):
        # header detection (must include type/status/subject/object/source_text)
        if header is None:
            h = [_norm(c) for c in cells]
            if "TYPE" in h and ("SUBJECT_ID" in h or "SUBJECT" in h) and ("OBJECT_ID" in h or "OBJECT" in h):
                header = h
                for i, name in enumerate(header):
                    idx[name] = i
                continue
            else:
                continue

        # data rows
        if len(cells) != len(header):
            # markdown tables can wrap; skip malformed line
            continue

        rows_seen += 1
        subj = cells[idx.get("SUBJECT_ID", idx.get("SUBJECT", -1))] if ("SUBJECT_ID" in idx or "SUBJECT" in idx) else ""
        obj = cells[idx.get("OBJECT_ID", idx.get("OBJECT", -1))] if ("OBJECT_ID" in idx or "OBJECT" in idx) else ""
        source_text = cells[idx.get("SOURCE_TEXT", -1)] if "SOURCE_TEXT" in idx else ""
        desc = cells[idx.get("DESCRIPTION", -1)] if "DESCRIPTION" in idx else ""

        if not subj.strip():
            stats.missing_subject += 1
        if not obj.strip():
            stats.missing_object += 1
        if not source_text.strip():
            stats.missing_source_text += 1
        if "[PAGE " in source_text.upper():
            stats.with_page += 1
        if "CMO[" in desc.upper():
            stats.with_cmo_tag += 1

    stats.rows = declared_rows if declared_rows is not None else rows_seen
    return stats


def _parse_claims_fixed_parquet(p: Path) -> ClaimsStats:
    df = pd.read_parquet(p)
    stats = ClaimsStats()
    stats.rows = int(len(df))
    if not len(df):
        return stats

    subj_col = "subject_id" if "subject_id" in df.columns else ("subject" if "subject" in df.columns else None)
    obj_col = "object_id" if "object_id" in df.columns else ("object" if "object" in df.columns else None)
    src_col = "source_text" if "source_text" in df.columns else ("text" if "text" in df.columns else None)
    desc_col = "description" if "description" in df.columns else None

    if subj_col:
        stats.missing_subject = int((df[subj_col].fillna("").astype(str).str.strip() == "").sum())
    if obj_col:
        stats.missing_object = int((df[obj_col].fillna("").astype(str).str.strip() == "").sum())
    if src_col:
        src = df[src_col].fillna("").astype(str)
        stats.missing_source_text = int((src.str.strip() == "").sum())
        stats.with_page = int(src.str.contains(r"\[PAGE\s+\d+\]", regex=True, case=False).sum())
    if desc_col:
        desc = df[desc_col].fillna("").astype(str)
        stats.with_cmo_tag = int(desc.str.contains(r"CMO\[(?:.|\n)*?\]", regex=True, case=False).sum())
    return stats


def _load_gold_targets(p: Path) -> dict:
    return json.loads(_read_text(p))


def _keyword_recall(haystack: str, keywords: list[str]) -> tuple[int, int, list[str]]:
    h = _norm(haystack)
    hits = []
    for k in keywords:
        kk = _norm(k)
        if kk and kk in h:
            hits.append(k)
    return (len(hits), len(keywords), hits)


def _pct(n: int, d: int) -> float:
    return (n / d * 100.0) if d else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description="Part A: scorecard from human_readable markdown outputs (no parquet required).")
    ap.add_argument("--out-dir", type=Path, required=True, help="GraphRAG output directory (e.g., graphrag-project/output_partA_subset5_v3)")
    ap.add_argument(
        "--gold-targets",
        type=Path,
        default=Path("LLM-Knowledge-Graph/artifacts/partA/richmond_gold_targets_v1.json"),
        help="Gold keyword targets JSON",
    )
    ap.add_argument(
        "--out-md",
        type=Path,
        default=None,
        help="Optional output markdown path. Default: artifacts/partA/scorecard_<runname>.md",
    )
    args = ap.parse_args()

    out_dir = args.out_dir
    hr = out_dir / "human_readable"
    if not out_dir.exists():
        print(f"ERROR: out-dir not found: {out_dir}")
        return 1
    if not hr.exists():
        print(f"ERROR: human_readable dir not found: {hr}")
        return 1

    gold = _load_gold_targets(args.gold_targets)
    run_name = out_dir.name
    out_md = args.out_md or Path("LLM-Knowledge-Graph/artifacts/partA") / f"scorecard_{run_name}.md"

    # Read files (best-effort)
    quality_md = _read_text(hr / "quality_gates.md") if (hr / "quality_gates.md").exists() else ""
    entities_md = _read_text(hr / "entities.md") if (hr / "entities.md").exists() else ""
    rel_md = _read_text(hr / "relationships.md") if (hr / "relationships.md").exists() else ""
    comm_md = _read_text(hr / "community_reports.md") if (hr / "community_reports.md").exists() else ""
    claims_md = _read_text(hr / "claims_fixed.md") if (hr / "claims_fixed.md").exists() else ""

    q = _parse_quality_gates(quality_md) if quality_md else QualityGates()

    # Prefer parquet for claim stats (markdown is usually truncated head-only).
    claims_parquet = out_dir / "claims_fixed.parquet"
    if not claims_parquet.exists():
        # older runs may store as covariates.parquet
        claims_parquet = out_dir / "covariates.parquet"
    c = _parse_claims_fixed_parquet(claims_parquet) if claims_parquet.exists() else (_parse_claims_fixed_md(claims_md) if claims_md else ClaimsStats())

    # Gold recall checks (keyword proxy)
    # Prefer parquet sources for better coverage; fall back to markdown text.
    parts: list[str] = []
    ent_p = out_dir / "entities.parquet"
    rel_p = out_dir / "relationships.parquet"
    rep_p = out_dir / "community_reports.parquet"
    if ent_p.exists():
        ent = pd.read_parquet(ent_p)
        for col in ["title", "type", "description"]:
            if col in ent.columns:
                parts.extend(ent[col].fillna("").astype(str).tolist())
    else:
        parts.append(entities_md)
    if rel_p.exists():
        rel = pd.read_parquet(rel_p)
        for col in ["source", "target", "description"]:
            if col in rel.columns:
                parts.extend(rel[col].fillna("").astype(str).tolist())
    else:
        parts.append(rel_md)
    if rep_p.exists():
        rep = pd.read_parquet(rep_p)
        for col in ["title", "summary", "findings"]:
            if col in rep.columns:
                parts.extend(rep[col].fillna("").astype(str).tolist())
    else:
        parts.append(comm_md)
    if claims_parquet.exists():
        dfc = pd.read_parquet(claims_parquet)
        for col in ["subject_id", "object_id", "description"]:
            if col in dfc.columns:
                parts.extend(dfc[col].fillna("").astype(str).tolist())
    else:
        parts.append(claims_md)

    haystack = "\n".join(parts)
    ctx_hit, ctx_total, ctx_hits = _keyword_recall(haystack, gold.get("contexts", []))
    mech_hit, mech_total, mech_hits = _keyword_recall(haystack, gold.get("mechanisms", []))
    out_hit, out_total, out_hits = _keyword_recall(haystack, gold.get("outcomes", []))

    md: list[str] = []
    md.append(f"## Part A — Scorecard (markdown-based) — `{run_name}`\n")
    md.append(f"- output dir: `{out_dir.as_posix()}`")
    md.append(f"- generated from: `human_readable/*.md` (no parquet required)\n")

    md.append("### A) Quality gates (run health)\n")
    if q.entities_rows is not None:
        md.append(f"- entities rows: **{q.entities_rows}**")
    if q.entities_blank_type is not None:
        md.append(f"- blank entity types: **{q.entities_blank_type}** (target 0)")
    if q.entities_corrupt_title is not None:
        md.append(f"- corrupt entity titles: **{q.entities_corrupt_title}** (target 0)")
    if q.relationships_rows is not None:
        md.append(f"- relationships rows: **{q.relationships_rows}**")
    if q.relationships_cmo_pct is not None and q.relationships_cmo_edges is not None:
        md.append(f"- CMO-ish edges: **{q.relationships_cmo_edges}** (**{q.relationships_cmo_pct:.2f}%**, target ≥ 15%)")
    md.append("")

    md.append("### B) Claim traceability (verification gate)\n")
    if c.rows:
        src_name = claims_parquet.name if claims_parquet.exists() else "human_readable/claims_fixed.md"
        md.append(f"- claims source: `{src_name}`")
        md.append(f"- claims rows: **{c.rows}**")
        md.append(f"- claims with `[PAGE N]`: **{c.with_page}** (**{_pct(c.with_page, c.rows):.2f}%**, target ≥ 90%)")
        md.append(f"- claims with `CMO[...]` tag: **{c.with_cmo_tag}** (**{_pct(c.with_cmo_tag, c.rows):.2f}%**)")
        md.append(f"- missing subject: **{c.missing_subject}**")
        md.append(f"- missing object: **{c.missing_object}**")
        md.append(f"- missing source_text: **{c.missing_source_text}**")
    else:
        md.append("- claims_fixed.md not found (cannot compute traceability stats)")
    md.append("")

    md.append("### C) Richmond gold target recall (keyword proxy)\n")
    md.append(f"- contexts hit: **{ctx_hit}/{ctx_total}** (**{_pct(ctx_hit, ctx_total):.2f}%**)")
    md.append(f"- mechanisms hit: **{mech_hit}/{mech_total}** (**{_pct(mech_hit, mech_total):.2f}%**)")
    md.append(f"- outcomes hit: **{out_hit}/{out_total}** (**{_pct(out_hit, out_total):.2f}%**)")
    md.append("")
    if ctx_hits:
        md.append(f"- context hits: {', '.join(sorted(ctx_hits))}")
    if mech_hits:
        md.append(f"- mechanism hits: {', '.join(sorted(mech_hits))}")
    if out_hits:
        md.append(f"- outcome hits: {', '.join(sorted(out_hits))}")
    md.append("")

    md.append("### D) Notes / next iteration hints\n")
    if q.entities_blank_type is not None and q.entities_blank_type > 0:
        md.append("- Blank entity types > 0: refine typing prompts or postprocess typing inference.")
    if c.rows and _pct(c.with_page, c.rows) < 90.0:
        md.append("- `[PAGE N]` coverage < 90%: enforce evidence spans earlier (ingestion + claim prompt).")
    md.append("- Keyword recall is only a proxy; final judgement requires sample audit against Richmond CMOCs.\n")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(md).strip() + "\n", encoding="utf-8")
    print(f"Wrote: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

