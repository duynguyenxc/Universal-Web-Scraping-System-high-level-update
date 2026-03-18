from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def _write_text(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def _df_head_md(df: pd.DataFrame, cols: list[str], n: int) -> str:
    cols = [c for c in cols if c in df.columns]
    if not cols:
        return df.head(n).to_markdown(index=False)
    return df[cols].head(n).to_markdown(index=False)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Export GraphRAG parquet outputs into human-readable Markdown files for meetings."
    )
    ap.add_argument(
        "--out-dir",
        default="graphrag-project/output_meeting_std",
        help="GraphRAG output directory (contains parquet files).",
    )
    ap.add_argument(
        "--export-dir",
        default="graphrag-project/output_meeting_std/human_readable",
        help="Directory to write readable exports (Markdown).",
    )
    ap.add_argument("--n", type=int, default=10, help="Number of sample rows to export for tables.")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    export_dir = Path(args.export_dir)

    # Basic sanity checks
    stats = out_dir / "stats.json"
    if stats.exists():
        _write_text(export_dir / "stats.json", stats.read_text(encoding="utf-8"))

    # Documents
    docs_p = out_dir / "documents.parquet"
    if docs_p.exists():
        df = pd.read_parquet(docs_p)
        md = "# GraphRAG Documents (sample)\n\n"
        md += f"- rows: {len(df)}\n- cols: {df.columns.tolist()}\n\n"
        md += _df_head_md(df, ["human_readable_id", "title", "id"], args.n)
        md += "\n"
        _write_text(export_dir / "documents.md", md)

    # Entities
    ent_p = out_dir / "entities.parquet"
    if ent_p.exists():
        df = pd.read_parquet(ent_p)
        md = "# GraphRAG Entities (sample)\n\n"
        md += f"- rows: {len(df)}\n- cols: {df.columns.tolist()}\n\n"
        md += _df_head_md(df, ["title", "type", "frequency", "degree"], args.n)
        md += "\n\n## Entities with description (first 10)\n\n"
        cols = [c for c in ["title", "type", "description"] if c in df.columns]
        if cols:
            md += df[cols].head(10).to_markdown(index=False)
            md += "\n"
        _write_text(export_dir / "entities.md", md)

    # Relationships
    rel_p = out_dir / "relationships.parquet"
    if rel_p.exists():
        df = pd.read_parquet(rel_p)
        md = "# GraphRAG Relationships (sample)\n\n"
        md += f"- rows: {len(df)}\n- cols: {df.columns.tolist()}\n\n"
        md += _df_head_md(df, ["source", "target", "description", "weight"], args.n)
        md += "\n"
        _write_text(export_dir / "relationships.md", md)

    # Communities
    com_p = out_dir / "communities.parquet"
    if com_p.exists():
        df = pd.read_parquet(com_p)
        md = "# GraphRAG Communities (clusters)\n\n"
        md += f"- rows: {len(df)}\n- cols: {df.columns.tolist()}\n\n"
        md += _df_head_md(df, ["community", "level", "parent", "size", "title"], args.n)
        md += "\n"
        _write_text(export_dir / "communities.md", md)

    # Community reports (the key demo artifact)
    rep_p = out_dir / "community_reports.parquet"
    if rep_p.exists():
        df = pd.read_parquet(rep_p)
        md = "# GraphRAG Community Reports (THIS is what to show in the meeting)\n\n"
        md += f"- rows: {len(df)}\n- cols: {df.columns.tolist()}\n\n"

        # prefer full_content, fallback to summary
        text_col = "full_content" if "full_content" in df.columns else ("summary" if "summary" in df.columns else None)
        header_cols = [c for c in ["community", "level", "title", "rank", "size"] if c in df.columns]

        for i, row in df.iterrows():
            md += f"## Community {row.get('community', i)} — {row.get('title', '')}\n\n"
            if header_cols:
                md += "- meta:\n"
                for c in header_cols:
                    md += f"  - {c}: {row.get(c)}\n"
                md += "\n"
            if text_col:
                md += str(row.get(text_col, "")).strip() + "\n\n"
            else:
                md += "_No text column found (expected full_content/summary)._ \n\n"

        _write_text(export_dir / "community_reports.md", md)

    # Claims / covariates (GraphRAG versions differ: some output "claims.parquet", others "covariates.parquet".
    # Our Part A pipeline may also produce a repaired/derived `claims_fixed.parquet`.)
    fixed_p = out_dir / "claims_fixed.parquet"
    claims_p = out_dir / "claims.parquet"
    cov_p = out_dir / "covariates.parquet"
    src_p = fixed_p if fixed_p.exists() else (claims_p if claims_p.exists() else (cov_p if cov_p.exists() else None))
    if src_p is not None:
        df = pd.read_parquet(src_p)
        md = "# GraphRAG Claims (sample)\n\n"
        md += f"- source: {src_p.name}\n"
        md += f"- rows: {len(df)}\n- cols: {df.columns.tolist()}\n\n"
        # Column names vary by version; pick the best available set.
        preferred_cols = [
            # Prefer GraphRAG's covariates schema (subject_id/object_id); fallback to claims schema (subject/object)
            "subject_id",
            "object_id",
            "subject",
            "object",
            "type",
            "status",
            "description",
            "source_text",
            "text_unit_id",
            "text",
            "covariate_type",
            "covariate_status",
        ]
        md += _df_head_md(df, preferred_cols, args.n)
        md += "\n"
        _write_text(export_dir / "claims.md", md)

    print(f"Exported readable files to: {export_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



