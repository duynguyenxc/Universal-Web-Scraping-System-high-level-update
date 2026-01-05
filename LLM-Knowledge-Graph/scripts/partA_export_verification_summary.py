from __future__ import annotations

import argparse
import json
from pathlib import Path


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Part A: export a concise verification/coverage summary for this week's deliverable.")
    ap.add_argument("--metadata-jsonl", type=Path, default=Path("LLM-Knowledge-Graph/artifacts/partA/studies_metadata.jsonl"))
    ap.add_argument("--pdf-dir", type=Path, default=Path("LLM-Knowledge-Graph/data-28-studies"))
    ap.add_argument("--graphrag-out-dir", type=Path, default=Path("LLM-Knowledge-Graph/graphrag-project/output_partA"))
    ap.add_argument("--out-md", type=Path, default=Path("LLM-Knowledge-Graph/artifacts/partA/verification_summary.md"))
    args = ap.parse_args()

    rows = _read_jsonl(args.metadata_jsonl)
    pdf_files = {p.name for p in args.pdf_dir.glob("*.pdf")} if args.pdf_dir.exists() else set()

    total = len(rows)
    pdf_n = sum(1 for r in rows if r.get("source") == "pdf")
    url_n = sum(1 for r in rows if r.get("source") == "url")
    with_doi = sum(1 for r in rows if (r.get("doi") or "").strip())
    with_abs = sum(1 for r in rows if (r.get("abstract") or "").strip())

    pdf_missing_text = []
    for r in rows:
        if r.get("source") == "pdf":
            sid = (r.get("source_id") or "").strip()
            if sid and sid not in pdf_files:
                pdf_missing_text.append(sid)

    stats_path = args.graphrag_out_dir / "stats.json"
    stats = None
    if stats_path.exists():
        try:
            stats = json.loads(stats_path.read_text(encoding="utf-8"))
        except Exception:
            stats = None

    md = "## Part A (Education) - Verification Snapshot (this week)\n\n"
    md += "### Corpus coverage\n\n"
    md += f"- **records (Richmond-28 target)**: {total}\n"
    md += f"- **PDF-backed**: {pdf_n}\n"
    md += f"- **URL-only**: {url_n}\n"
    md += f"- **with DOI**: {with_doi}\n"
    md += f"- **with abstract** (used for URL-only ingestion): {with_abs}\n"
    if pdf_missing_text:
        md += "\n**PDFs referenced but missing on disk:**\n"
        for x in pdf_missing_text:
            md += f"- {x}\n"
    md += "\n"

    md += "### GraphRAG indexing artifacts\n\n"
    md += f"- output dir: `{args.graphrag_out_dir.as_posix()}`\n"
    for f in [
        "documents.parquet",
        "text_units.parquet",
        "entities.parquet",
        "relationships.parquet",
        "communities.parquet",
        "community_reports.parquet",
        # GraphRAG versions differ: claims may be written as "covariates.parquet"
        "claims.parquet",
        "covariates.parquet",
    ]:
        p = args.graphrag_out_dir / f
        md += f"- {f}: {'YES' if p.exists() else 'NO'}\n"
    md += "\n"

    if stats:
        md += "### stats.json (raw)\n\n"
        md += "```json\n"
        md += json.dumps(stats, indent=2, ensure_ascii=False)
        md += "\n```\n"

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(md, encoding="utf-8")
    print(f"Wrote: {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

