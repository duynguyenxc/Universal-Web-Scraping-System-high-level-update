from __future__ import annotations

import argparse
import sys
from pathlib import Path
def main() -> int:
    # Allow running without installing the package (Windows-friendly).
    llmkg_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(llmkg_root / "src"))
    from llm_kg.parta.metadata import run_metadata_extraction

    ap = argparse.ArgumentParser(description="Part A: extract metadata from PDFs + optional URLs for Richmond-28 corpus.")
    ap.add_argument("--pdf-dir", type=Path, default=Path("LLM-Knowledge-Graph/data-28-studies"))
    ap.add_argument("--links-file", type=Path, default=None, help="Optional text file with one URL per line.")
    ap.add_argument(
        "--links-pdf",
        type=Path,
        default=Path("LLM-Knowledge-Graph/documents/in4-about-28-studies-paper.pdf"),
        help="Optional PDF containing embedded links (e.g., PubMed URLs).",
    )
    ap.add_argument("--max-pages", type=int, default=3, help="Max pages to extract text from each PDF.")
    ap.add_argument("--out-dir", type=Path, default=Path("LLM-Knowledge-Graph/artifacts/partA"))
    ap.add_argument("--timeout-s", type=float, default=20.0)
    ap.add_argument("--crossref-sleep-s", type=float, default=0.25)
    ap.add_argument("--user-agent", type=str, default="llm-kg/0.1 (mailto:example@example.com)")
    args = ap.parse_args()

    records = run_metadata_extraction(
        pdf_dir=args.pdf_dir,
        links_file=args.links_file,
        links_pdf=args.links_pdf if args.links_pdf and args.links_pdf.exists() else None,
        max_pages=args.max_pages,
        out_dir=args.out_dir,
        timeout_s=args.timeout_s,
        crossref_sleep_s=args.crossref_sleep_s,
        user_agent=args.user_agent,
    )

    # small console summary
    pdf_n = sum(1 for r in records if r.source == "pdf")
    url_n = sum(1 for r in records if r.source == "url")
    doi_n = sum(1 for r in records if r.doi)
    title_n = sum(1 for r in records if r.title)
    print(f"Records: {len(records)} (pdf={pdf_n}, url={url_n})")
    print(f"With DOI: {doi_n} | With title: {title_n}")
    print(f"Wrote: {args.out_dir / 'studies_metadata.csv'}")
    print(f"Wrote: {args.out_dir / 'studies_metadata.jsonl'}")
    if args.links_file is None and (args.links_pdf is None or not args.links_pdf.exists()):
        print("Note: no --links-file/--links-pdf provided (URL-only studies skipped).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

