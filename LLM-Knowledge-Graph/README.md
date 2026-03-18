# LLM Knowledge Graph (subproject)

This folder is a **separate project** inside the UWSS repository. The goal is to build a **domain-specific knowledge graph** and **literature review / QA** tooling **on top of** the papers already collected by UWSS.

## Design goals

- Keep UWSS (the data collection pipeline) untouched and stable.
- Treat UWSS outputs as inputs:
  - JSONL exports (recommended)
  - SQLite/Postgres `documents` table (optional)
  - downloaded PDFs / extracted text (optional)
- Provide an LLM-assisted pipeline:
  1) **Ontology** (entity/relation schema)
  2) **Extraction** (entities/relations + provenance)
  3) **Graph store** (queryable KG)
  4) **QA & literature review** (answers with citations)

## What this project consumes from UWSS

Typical inputs (you can point to local paths or S3-synced folders):

- `data/runs/<YY-MM-DD>/corrosion_papers_<YY-MM-DD>.jsonl`
- `data/runs/<YY-MM-DD>/files/` (downloaded PDFs; optional)
- `data/uwss.sqlite` (optional alternative input)

## Repo layout (inside this folder)

```
LLM-Knowledge-Graph/
  README.md
  pyproject.toml
  src/
    llm_kg/
      __init__.py
      cli.py
      pipeline/
        __init__.py
  configs/
    example.yaml
  data/               # local-only (ignored) for KG experiments
  outputs/            # local-only (ignored) KG artifacts
```

## Quick start (local)

Create a venv for *this subproject* and install:

```bash
cd LLM-Knowledge-Graph
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
pip install -e .
python -m llm_kg --help
```

## Microsoft GraphRAG (this week's goal: make it runnable locally)

This repo already contains a ready-to-run GraphRAG project at `LLM-Knowledge-Graph/graphrag-project/`.

## Part A (Education verification) – this week’s deliverable

Goal: run a **benchmarkable** pipeline over the Richmond et al. (2020) “included studies” corpus (28 studies), producing:
- a **clean metadata manifest** (DOI/title/year/journal/abstract when available) with traceability,
- GraphRAG indexing artifacts (graph, communities, community reports),
- and a query demo grounded in the corpus.

### 0) Put your benchmark files in the expected locations

- **PDFs you downloaded**: `LLM-Knowledge-Graph/data-28-studies/` *(gitignored)*
- **PDF containing the missing-study links** (PubMed links are OK): `LLM-Knowledge-Graph/documents/in4-about-28-studies-paper.pdf`

### 1) Build metadata (PDF + missing-study links)

```bash
python LLM-Knowledge-Graph/scripts/partA_extract_study_metadata.py ^
  --pdf-dir "LLM-Knowledge-Graph/data-28-studies" ^
  --links-pdf "LLM-Knowledge-Graph/documents/in4-about-28-studies-paper.pdf" ^
  --out-dir "LLM-Knowledge-Graph/artifacts/partA" ^
  --max-pages 3 ^
  --user-agent "llm-kg/0.1 (mailto:YOUR_EMAIL_HERE)"
```

Outputs:
- `LLM-Knowledge-Graph/artifacts/partA/studies_metadata.csv`
- `LLM-Knowledge-Graph/artifacts/partA/studies_metadata.jsonl`

### 2) Build GraphRAG input texts (28 docs)

```bash
python LLM-Knowledge-Graph/scripts/partA_prepare_graphrag_input.py ^
  --metadata-jsonl "LLM-Knowledge-Graph/artifacts/partA/studies_metadata.jsonl" ^
  --pdf-dir "LLM-Knowledge-Graph/data-28-studies" ^
  --out-input-dir "LLM-Knowledge-Graph/graphrag-project/input_partA"
```

### 3) Run GraphRAG (index + query)

Set your key (Windows PowerShell):

```powershell
$env:OPENAI_API_KEY="YOUR_KEY"
```

Then run the end-to-end script:

```powershell
powershell -ExecutionPolicy Bypass -File LLM-Knowledge-Graph/scripts/partA_run_graphrag_v4.ps1 -OutDir "graphrag-project/output_partA_richmond28_v4_run2" -InputDir "graphrag-project/input_partA_v4" -CacheDir "C:\\grc4"
```

Or skip indexing/query (if you already indexed once, and only want exports/gates):

```powershell
powershell -ExecutionPolicy Bypass -File LLM-Knowledge-Graph/scripts/partA_run_graphrag_v4.ps1 -OutDir "graphrag-project/output_partA_richmond28_v4_run2" -InputDir "graphrag-project/input_partA_v4" -SkipIndex -SkipQuery
```

Notes:
- This Part A runner uses `graphrag-project/settings.partA.v4.yaml` (CMOC-shaped entities/relationships + evidence-local claims + community detection).
- Outputs are written to the `-OutDir` folder and also exported to `-OutDir/human_readable/` for easy review.
- `-CacheDir` should be a short path on Windows (prevents MAX_PATH / long filename issues).

### 1) Install GraphRAG (separate from `llm-kg`)

From `LLM-Knowledge-Graph/`:

```bash
python -m pip install --upgrade pip
pip install graphrag
graphrag --help
```

### 2) Set your API key

Copy `graphrag-project/env.example` to `graphrag-project/.env` and set:
- `OPENAI_API_KEY`

### 3) Build GraphRAG input from your UWSS JSONL (S3-synced)

Example: take up to 50 papers from a specific day:

```bash
python scripts/graphrag_prepare_input.py --day 25-12-06 --max-docs 50
```

This writes `.txt` files into `graphrag-project/input/` (GraphRAG input format).

### 4) Run indexing (low-rate config to avoid 429 rate limits)

```bash
graphrag index --root graphrag-project --config graphrag-project/settings.lowrate.yaml
```

### 5) Query (global search = “big picture”)

```bash
graphrag query --root graphrag-project --method global --query "What are the main corrosion mitigation intervention clusters and their reported outcomes?"
```

### (Optional) Prompt tuning (for iterative refinement next week)

```bash
graphrag prompt-tune --root graphrag-project --config graphrag-project/settings.lowrate.yaml --domain "reinforced concrete corrosion"
```

### Windows one-command smoke test

```powershell
.\scripts\graphrag_smoketest.ps1 -Day 25-12-06 -MaxDocs 30 -OutDir "graphrag-project/output_meeting_std" -Query "Summarize main corrosion mechanisms and mitigation strategies."
```

Dry-run (validate config without any LLM calls):

```powershell
.\scripts\graphrag_smoketest.ps1 -Day 25-12-06 -MaxDocs 5 -DryRun
```

## Notes

- This subproject has its own `pyproject.toml` so dependencies can evolve independently from UWSS.
- We intentionally keep this folder independent; integration happens via **files/DB**, not cross-importing UWSS internals.


