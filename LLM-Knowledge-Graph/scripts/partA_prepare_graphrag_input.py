from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    llmkg_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(llmkg_root / "src"))

    from llm_kg.parta.graphrag_input import (
        build_graphrag_docs_from_metadata,
        load_metadata_jsonl,
        write_graphrag_input_dir,
    )

    ap = argparse.ArgumentParser(description="Part A: build GraphRAG input .txt files from PDFs + URL abstracts.")
    ap.add_argument("--metadata-jsonl", type=Path, default=Path("LLM-Knowledge-Graph/artifacts/partA/studies_metadata.jsonl"))
    ap.add_argument("--pdf-dir", type=Path, default=Path("LLM-Knowledge-Graph/data-28-studies"))
    ap.add_argument("--out-input-dir", type=Path, default=Path("LLM-Knowledge-Graph/graphrag-project/input_partA"))
    ap.add_argument("--limit", type=int, default=0, help="If >0, only write the first N records (for fast iteration).")
    ap.add_argument(
        "--only-pdf",
        action="store_true",
        help="If set, only include records with source=pdf (recommended for early iteration).",
    )
    args = ap.parse_args()

    rows = load_metadata_jsonl(args.metadata_jsonl)
    if args.only_pdf:
        rows = [r for r in rows if (r.get("source") or "").strip().lower() == "pdf"]
    if args.limit and args.limit > 0:
        rows = rows[: int(args.limit)]
    docs = build_graphrag_docs_from_metadata(metadata_rows=rows, pdf_dir=args.pdf_dir)
    write_graphrag_input_dir(args.out_input_dir, docs)
    print(f"Docs written: {len(docs)} -> {args.out_input_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

