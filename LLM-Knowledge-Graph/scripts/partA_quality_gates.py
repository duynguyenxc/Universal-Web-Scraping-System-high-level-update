from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


CORRUPT_PATTERNS = [
    # GraphRAG / LLM "diff marker" artifact
    re.compile(r"<\|DIFF_MARKER\|>"),
    # Common "ENTITY" echo artifacts (sometimes with escaped quotes)
    re.compile(r'\("ENTITY"'),
    re.compile(r'\(\\\"ENTITY\\\"'),
]


def _is_corrupt_title(s: str) -> bool:
    s = (s or "").strip()
    if not s:
        return False
    return any(p.search(s) for p in CORRUPT_PATTERNS)


def main() -> int:
    ap = argparse.ArgumentParser(description="Part A: post-run quality gates for entities/relationships (avoid silent regressions).")
    ap.add_argument("--out-dir", type=Path, default=Path("LLM-Knowledge-Graph/graphrag-project/output_partA_v2"))
    ap.add_argument("--fail", action="store_true", help="Exit non-zero if gates fail.")
    ap.add_argument("--max-blank-types", type=int, default=0)
    ap.add_argument("--max-corrupt-titles", type=int, default=0)
    ap.add_argument("--min-cmo_edge_pct", type=float, default=15.0, help="Minimum % of CMOC-family edges.")
    ap.add_argument("--max-outcome-source-pct", type=float, default=10.0, help="Maximum % of edges with OUTCOME as source (should be a sink).")
    args = ap.parse_args()

    out = args.out_dir
    # Prefer CMOC-normalized outputs if present (postprocess step).
    ent_p = out / "entities_cmoc_normalized.parquet"
    if not ent_p.exists():
        ent_p = out / "entities.parquet"
    rel_p = out / "relationships_cmoc_normalized.parquet"
    if not rel_p.exists():
        rel_p = out / "relationships.parquet"
    if not ent_p.exists() or not rel_p.exists():
        raise FileNotFoundError(f"Missing entities/relationships parquet under: {out}")

    ent = pd.read_parquet(ent_p)
    rel = pd.read_parquet(rel_p)

    # --- Entities gates ---
    ent["type"] = ent.get("type", "").fillna("")
    blank_types = int((ent["type"].astype(str).str.strip() == "").sum())
    corrupt_titles = int(ent["title"].fillna("").astype(str).map(_is_corrupt_title).sum())
    assessment_ratio = float((ent["type"] == "ASSESSMENT_MEASURE").mean() * 100.0) if len(ent) else 0.0

    # --- Relationships gates (CMOC-family proxy) ---
    emap = ent.set_index("title")["type"].to_dict()
    rel["source_type"] = rel["source"].map(emap).fillna("")
    rel["target_type"] = rel["target"].map(emap).fillna("")
    rel["pair"] = list(zip(rel["source_type"], rel["target_type"]))
    # v4-friendly: minimal ontology + robust mapping (treat specific contexts as CONTEXT family).
    src_t = rel["source_type"].astype(str)
    tgt_t = rel["target_type"].astype(str)
    src_norm = src_t.replace(
        {
            "LEARNER_CONTEXT": "CONTEXT",
            "COGNITIVE_STATE": "MECHANISM",
            "MOTIVATION_AFFECT": "MECHANISM",
            "SETTING_CONTEXT": "CONTEXT",
        }
    )
    tgt_norm = tgt_t.replace(
        {
            "LEARNER_CONTEXT": "CONTEXT",
            "COGNITIVE_STATE": "MECHANISM",
            "MOTIVATION_AFFECT": "MECHANISM",
            "SETTING_CONTEXT": "CONTEXT",
        }
    )
    rel["pair_norm"] = list(zip(src_norm, tgt_norm))

    want = {
        ("CONTEXT", "MECHANISM"),
        ("CONTEXT", "OUTCOME"),
        ("INTERVENTION", "MECHANISM"),
        ("MECHANISM", "OUTCOME"),
        ("INTERVENTION", "OUTCOME"),
        ("COMPARATOR", "OUTCOME"),
    }
    cmo_edges = int(rel["pair"].isin(want).sum())
    cmo_pct = float((cmo_edges / len(rel) * 100.0) if len(rel) else 0.0)
    cmo_edges_norm = int(rel["pair_norm"].isin(want).sum())
    cmo_pct_norm = float((cmo_edges_norm / len(rel) * 100.0) if len(rel) else 0.0)

    outcome_source = int((src_norm == "OUTCOME").sum())
    outcome_source_pct = float((outcome_source / len(rel) * 100.0) if len(rel) else 0.0)

    # --- Report ---
    lines = []
    lines.append("## Part A — Quality gates (entities/relationships)\n")
    lines.append(f"- out_dir: `{out.as_posix()}`\n")
    lines.append("### Entities\n")
    lines.append(f"- rows: **{len(ent)}**")
    lines.append(f"- blank type count: **{blank_types}** (threshold <= {args.max_blank_types})")
    lines.append(f"- corrupt title count: **{corrupt_titles}** (threshold <= {args.max_corrupt_titles})")
    lines.append(f"- ASSESSMENT_MEASURE ratio: **{assessment_ratio:.2f}%** (diagnostic only; not a hard fail)\n")
    lines.append("### Relationships\n")
    lines.append(f"- rows: **{len(rel)}**")
    lines.append(f"- CMOC-family edges (raw types): **{cmo_edges} / {len(rel)} = {cmo_pct:.2f}%** (threshold >= {args.min_cmo_edge_pct}%)")
    lines.append(f"- CMOC-family edges (normalized types): **{cmo_edges_norm} / {len(rel)} = {cmo_pct_norm:.2f}%** (threshold >= {args.min_cmo_edge_pct}%)")
    lines.append(f"- OUTCOME-as-source edges (normalized types): **{outcome_source} / {len(rel)} = {outcome_source_pct:.2f}%** (threshold <= {args.max_outcome_source_pct}%)\n")

    report_path = out / "human_readable" / "quality_gates.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(f"Wrote: {report_path}")

    failed = False
    failed = failed or (blank_types > args.max_blank_types)
    failed = failed or (corrupt_titles > args.max_corrupt_titles)
    failed = failed or (cmo_pct_norm < args.min_cmo_edge_pct)
    failed = failed or (outcome_source_pct > args.max_outcome_source_pct)

    if failed and args.fail:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

