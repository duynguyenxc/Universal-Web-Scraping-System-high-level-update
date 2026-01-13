from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


_PAREN_RECORD_RE = re.compile(r"\(([^()]*)\)", re.DOTALL)


def _split_records(packed: str) -> list[str]:
    s = (packed or "").strip()
    if not s:
        return []

    # Prefer explicit "(...)" records if present (some rows contain multiple claims).
    recs = [m.strip() for m in _PAREN_RECORD_RE.findall(s) if m and m.strip()]
    if recs:
        return recs

    # Fallback: treat entire string as one record.
    return [s]


def _clean_field(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s).strip()
    # remove trailing unmatched right-parens which sometimes leak from formatting
    s = s.rstrip(" )")
    return s


def _parse_record(rec: str) -> dict[str, str] | None:
    """
    Expected (per prompts_partA/extract_claims.txt):
      subject|object|claim_type|claim_status|start_date|end_date|description|source_text

    Reality (in output_partA_v2/covariates.parquet):
      - sometimes missing parentheses
      - sometimes multiple records joined with newlines and "(...)"
      - sometimes the last field contains extra pipes (rare) -> join remainder into source_text
    """
    rec = (rec or "").strip().strip("()").strip()
    if not rec:
        return None

    parts = [p.strip() for p in rec.split("|")]
    if len(parts) < 4:
        return None

    # Minimum required
    subject = _clean_field(parts[0])
    obj = _clean_field(parts[1])
    claim_type = _clean_field(parts[2])
    status = _clean_field(parts[3])

    start_date = _clean_field(parts[4]) if len(parts) >= 5 else "NONE"
    end_date = _clean_field(parts[5]) if len(parts) >= 6 else "NONE"
    description = _clean_field(parts[6]) if len(parts) >= 7 else ""
    source_text = _clean_field("|".join(parts[7:])) if len(parts) >= 8 else ""

    # Normalize common sentinel
    start_date = "NONE" if not start_date else start_date
    end_date = "NONE" if not end_date else end_date

    return {
        "subject_id": subject,
        "object_id": obj,
        "type": claim_type,
        "status": status,
        "start_date": start_date,
        "end_date": end_date,
        "description": description,
        "source_text": source_text,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Part A: repair GraphRAG covariates/claims parquet when claim tuples are packed into subject_id."
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=Path("LLM-Knowledge-Graph/graphrag-project/output_partA_v2"),
        help="GraphRAG output directory containing covariates.parquet.",
    )
    ap.add_argument(
        "--in-parquet",
        type=str,
        default="covariates.parquet",
        help="Input parquet name (covariates.parquet or claims.parquet).",
    )
    ap.add_argument(
        "--out-parquet",
        type=str,
        default="claims_fixed.parquet",
        help="Output parquet name to write.",
    )
    ap.add_argument("--out-md", type=str, default="human_readable/claims_fixed.md")
    ap.add_argument("--max-md-rows", type=int, default=120)
    args = ap.parse_args()

    out_dir = args.out_dir
    src_path = out_dir / args.in_parquet
    if not src_path.exists():
        raise FileNotFoundError(src_path)

    df = pd.read_parquet(src_path)
    if "subject_id" not in df.columns:
        raise RuntimeError(f"Expected subject_id in {src_path.name}. cols={df.columns.tolist()}")

    repaired_rows: list[dict] = []
    for _, r in df.iterrows():
        packed = str(r.get("subject_id", "") or "")
        recs = _split_records(packed)
        if not recs:
            continue

        for i, rec in enumerate(recs):
            parsed = _parse_record(rec)
            if parsed is None:
                continue

            base_id = str(r.get("id", "") or "").strip()
            rid = base_id if i == 0 else f"{base_id}__{i}"

            repaired_rows.append(
                {
                    "id": rid,
                    "human_readable_id": None,  # filled below
                    "covariate_type": str(r.get("covariate_type", "") or "claim"),
                    "type": parsed["type"],
                    "description": parsed["description"],
                    "subject_id": parsed["subject_id"],
                    "object_id": parsed["object_id"],
                    "status": parsed["status"],
                    "start_date": parsed["start_date"],
                    "end_date": parsed["end_date"],
                    "source_text": parsed["source_text"],
                    "text_unit_id": r.get("text_unit_id"),
                    # keep provenance for debugging
                    "orig_row_id": base_id,
                }
            )

    out = pd.DataFrame(repaired_rows)
    if out.empty:
        raise RuntimeError("No records could be repaired; check delimiter/format assumptions.")

    out["human_readable_id"] = list(range(len(out)))
    # Basic cleanup: drop blank subjects/types (not verification-grade)
    out = out[(out["subject_id"].fillna("").astype(str).str.strip() != "")]
    out = out[(out["type"].fillna("").astype(str).str.strip() != "")]
    out = out.reset_index(drop=True)

    dst_path = out_dir / args.out_parquet
    out.to_parquet(dst_path, index=False)

    # Write a small readable view for review/meeting
    md_path = out_dir / args.out_md
    md_path.parent.mkdir(parents=True, exist_ok=True)
    cols = [
        "type",
        "status",
        "subject_id",
        "object_id",
        "start_date",
        "end_date",
        "source_text",
        "description",
        "text_unit_id",
    ]
    cols = [c for c in cols if c in out.columns]
    md = []
    md.append("## Part A — claims_fixed (repaired from packed subject_id)\n")
    md.append(f"- input: `{src_path.as_posix()}`")
    md.append(f"- output: `{dst_path.as_posix()}`")
    md.append(f"- rows: **{len(out)}**\n")
    md.append(out[cols].head(int(args.max_md_rows)).to_markdown(index=False))
    md.append("")
    md_path.write_text("\n".join(md), encoding="utf-8")

    print(f"Wrote: {dst_path}")
    print(f"Wrote: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

