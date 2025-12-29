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


