## Part A (Education Verification) – Study Metadata Artifacts

This folder contains **lightweight, shareable artifacts** (CSV/JSONL) produced from the local benchmark corpus (Richmond et al., 2020 → included studies).

### What you run

- **PDFs present**: put PDFs under `LLM-Knowledge-Graph/data-28-studies/` (this folder is gitignored).
- **PDFs missing**: put the paper landing-page URLs (one per line) into a text file (see `missing_links.example.txt`).
- **Alternative (recommended for your current setup)**: if you already have a PDF that contains embedded links for the missing studies (e.g. `documents/in4-about-28-studies-paper.pdf`), the script can extract those links automatically via `--links-pdf` (PubMed links work well).

Run:

```bash
python LLM-Knowledge-Graph/scripts/partA_extract_study_metadata.py ^
  --pdf-dir "LLM-Knowledge-Graph/data-28-studies" ^
  --links-file "LLM-Knowledge-Graph/artifacts/partA/missing_links.txt" ^
  --links-pdf "LLM-Knowledge-Graph/documents/in4-about-28-studies-paper.pdf" ^
  --out-dir "LLM-Knowledge-Graph/artifacts/partA" ^
  --max-pages 3 ^
  --user-agent "llm-kg/0.1 (mailto:YOUR_EMAIL_HERE)"
```

If you don’t have missing links yet, you can omit `--links-file`.

### What you get

- `studies_metadata.csv`: human-readable table for checking/cleanup.
- `studies_metadata.jsonl`: machine-friendly records (one JSON per line).

Key columns:
- **source / source_id**: `pdf` + filename OR `url` + the URL.
- **doi / title / authors / year / journal**: normalized metadata (Crossref-enriched when possible).
- **abstract**: abstract when available (from Crossref or page meta tags).
- **doi_source / title_source**: where the DOI/title came from (PDF regex, Crossref, etc.).
- **confidence / notes**: quick quality signal + any replacement/heuristic notes.

### Next step (needed for full Part A verification)

We still need a **canonical list of the Richmond “28 included studies”** (ideally DOI/title/year) so we can:
- compute exact coverage (how many of the 28 we have locally),
- list what’s missing (PDF missing / URL-only),
- and later evaluate GraphRAG outputs against the human review.

