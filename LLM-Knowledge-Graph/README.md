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

## Notes

- This subproject has its own `pyproject.toml` so dependencies can evolve independently from UWSS.
- We intentionally keep this folder independent; integration happens via **files/DB**, not cross-importing UWSS internals.


