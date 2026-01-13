from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


CORRUPT_PATTERNS = [
    re.compile(r"<\\|DIFF_MARKER\\|>"),
    re.compile(r"\\(\\\"ENTITY\\\""),
    re.compile(r"\\(\"ENTITY\"\\)"),
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
    ap.add_argument("--min-cmo_edge_pct", type=float, default=15.0, help="Minimum % of CMO-ish edges.")
    args = ap.parse_args()

    out = args.out_dir
    ent_p = out / "entities.parquet"
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

    # --- Relationships gates (CMO-ish proxy) ---
    emap = ent.set_index("title")["type"].to_dict()
    rel["source_type"] = rel["source"].map(emap).fillna("")
    rel["target_type"] = rel["target"].map(emap).fillna("")
    rel["pair"] = list(zip(rel["source_type"], rel["target_type"]))
    want = {
        ("INTERVENTION", "MECHANISM"),
        ("INTERVENTION", "OUTCOME"),
        ("COMPARATOR", "OUTCOME"),
        ("LEARNER_CONTEXT", "MECHANISM"),
        ("LEARNER_CONTEXT", "OUTCOME"),
        ("COGNITIVE_STATE", "MECHANISM"),
        ("COGNITIVE_STATE", "OUTCOME"),
        ("MOTIVATION_AFFECT", "MECHANISM"),
        ("MOTIVATION_AFFECT", "OUTCOME"),
        ("SETTING_CONTEXT", "MECHANISM"),
        ("SETTING_CONTEXT", "OUTCOME"),
        ("TASK_CASE", "MECHANISM"),
        ("TASK_CASE", "OUTCOME"),
    }
    cmo_edges = int(rel["pair"].isin(want).sum())
    cmo_pct = float((cmo_edges / len(rel) * 100.0) if len(rel) else 0.0)

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
    lines.append(f"- CMO-ish edges: **{cmo_edges} / {len(rel)} = {cmo_pct:.2f}%** (threshold >= {args.min_cmo_edge_pct}%)\n")

    report_path = out / "human_readable" / "quality_gates.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(f"Wrote: {report_path}")

    failed = False
    failed = failed or (blank_types > args.max_blank_types)
    failed = failed or (corrupt_titles > args.max_corrupt_titles)
    failed = failed or (cmo_pct < args.min_cmo_edge_pct)

    if failed and args.fail:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

