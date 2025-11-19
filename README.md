## Overview

**Universal Web Scraping System (UWSS)** is a configurable pipeline for collecting, storing, and analyzing academic documents about **corrosion and long‑term durability of reinforced concrete**.  
It combines **official academic databases** (Crossref, OpenAlex, Semantic Scholar, PubMed, arXiv via libraries) with a **Scrapy web crawler** for research‑group websites, and stores everything in a unified database and JSONL exports.

At a high level, the system:
- **Discovers** candidate papers and pages from multiple sources.
- **Scores** them for relevance using your corrosion/durability keywords.
- **Exports** high‑quality metadata to JSONL for inspection or downstream use.
- **Fetches PDFs** and records provenance (status, checksum, size, paths).
- **Extracts content** for deeper text analysis (optional, via GROBID).

The design goal: **one config‑driven toolchain** that can be reused for different research topics by changing keywords and seeds, without rewriting the pipeline.


## High‑Level Architecture

### Core components

- **Configuration (`config/config.yaml`, `config/web_crawler_scrapy.yaml`)**
  - `domain_keywords`, `negative_keywords` for corrosion/durability.
  - Rate limits, user‑agent, and optional Scrapy whitelist/blacklist.
  - Separate YAML for the Scrapy crawler (seed URLs, crawl depth, etc.).

- **CLI orchestrator (`src/uwss/cli.py`)**
  - Single entry point: `python -m src.uwss.cli <command> [options]`.
  - Registers all discovery, scoring, export, fetch, and validation commands.

- **Database + models (`src/uwss/store`)**
  - Unified `Document` model (SQLAlchemy) with fields like:
    - `source_url`, `landing_url`, `pdf_url`, `doi`, `title`, `abstract`, `authors`.
    - `year`, `venue`, `open_access`, `license`.
    - `relevance_score`, `keywords_found`.
    - `local_path`, `content_path`, `file_size`, `checksum_sha256`, `pdf_status`.
  - Works with **SQLite** for local experiments and **Postgres** in production.

- **Source adapters (`src/uwss/sources`)**
  - **Library‑based academic databases (improved path, recommended):**
    - `crossref_lib` (habanero) – `crossref-lib-discover`.
    - `openalex_lib` (pyalex) – `openalex-lib-discover`.
    - `semantic_scholar_lib` (semanticscholar) – `semantic-scholar-lib-discover`.
    - `paperscraper` (PubMed + arXiv) – `paperscraper-discover --source pubmed|arxiv`.
  - **Web crawler**:
    - `web_crawler_scrapy` (Scrapy spider + pipelines + adapter).

- **Scoring + quality (`src/uwss/score`, `src/uwss/quality`, `src/uwss/clean`)**
  - Keyword relevance scoring (unigram + bigram + title boost + negative keywords).
  - Data cleaning, deduplication, validation (duplicates, invalid years, missing files).

- **Fetch & extract (`src/uwss/crawl`, `src/uwss/fetch`, `src/uwss/parse`)**
  - Enrich Open Access info via **Unpaywall**.
  - Download PDFs and record status, HTTP codes, checksums, and local paths.
  - Optional full‑text extraction via **GROBID** into `data/content/`.


## End‑to‑End Pipeline

The pipeline has **five main stages**:

1. **Discover** – Collect candidate documents and pages.
2. **Score** – Compute relevance scores wrt. corrosion/durability keywords.
3. **Export** – Materialize high‑quality subsets to JSONL.
4. **Fetch** – Download PDFs and update document records.
5. **(Optional) Extract** – Parse PDFs into structured text for analysis.

Each stage is implemented as one or more CLI commands so you can run them independently, re‑run with different configs, or script them.


## Setup & Installation

### 1. Clone and install

```bash
git clone https://github.com/duynguyenxc/Universal-Web-Scraping-System-high-level-update.git
cd Universal-Web-Scraping-System-high-level-update

python -m venv uwss-env
uwss-env\Scripts\activate    # Windows
# source uwss-env/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

### 2. Configure domain keywords

Edit `config/config.yaml` to describe your corrosion/durability topic:

```yaml
domain_keywords:
  - "reinforced concrete corrosion experiment"
  - "chloride diffusion test concrete"
  - "service life prediction reinforced concrete"

negative_keywords:
  - "deep learning"
  - "computer vision"
  - "transformer"

contact_email: "your.email@university.edu"
user_agent: "uwss-bot/0.1 (+your.email@university.edu)"
```

### 3. Initialize a local database

```bash
python -m src.uwss.cli db-init --db data/uwss.sqlite
```

This creates a `documents` table and related metadata for your experiments.


## Stage 1 – Discover (library‑based academic databases)

Use the **improved, library‑based commands** (recommended). These commands all:
- Read `domain_keywords` from `config/config.yaml`.
- Insert `Document` rows into your DB.
- Are safe to re‑run (dedupe by DOI / title / URL).

### Crossref (via habanero)

```bash
python -m src.uwss.cli crossref-lib-discover \
  --config config/config.yaml \
  --db data/uwss.sqlite \
  --max 100
```

### OpenAlex (via pyalex)

```bash
python -m src.uwss.cli openalex-lib-discover \
  --config config/config.yaml \
  --db data/uwss.sqlite \
  --max 100
```

### Semantic Scholar (via semanticscholar)

```bash
python -m src.uwss.cli semantic-scholar-lib-discover \
  --config config/config.yaml \
  --db data/uwss.sqlite \
  --max 100
```

### PubMed & arXiv (via paperscraper)

```bash
# PubMed
python -m src.uwss.cli paperscraper-discover \
  --config config/config.yaml \
  --db data/uwss.sqlite \
  --source pubmed \
  --max 100

# arXiv (via paperscraper)
python -m src.uwss.cli paperscraper-discover \
  --config config/config.yaml \
  --db data/uwss.sqlite \
  --source arxiv \
  --max 100
```

> **Note**: Older commands like `discover-crossref`, `discover-arxiv`, `discover-pmc`, `discover-doaj`, `discover-semanticscholar` are kept only for backward compatibility and **should not be used** in this improved pipeline.


## Stage 1b – Discover (Scrapy web crawler for research groups)

For research‑group websites and structural‑durability centers, use the Scrapy adapter:

```bash
python -m src.uwss.cli web-crawler-scrapy-discover \
  --config config/web_crawler_scrapy.yaml \
  --seed-url "https://example-research-group.edu" \
  --max-depth 2 \
  --max-pages 50 \
  --output data/web_crawler_scrapy_results.jsonl
```

The crawler:
- Starts from a seed (research group homepage).
- Stays inside allowed domains.
- Filters pages by corrosion/durability keywords (phrase + token matching).
- Extracts `title`, `abstract`/summary, `year`, `authors`, `group`, `emails`, `depth`.
- Converts each relevant page into a UWSS document structure (via pipelines).

Details of the crawler design and experiments are documented in `web_crawler_scrapy_report.md`.


## Stage 2 – Score (keyword‑based relevance)

Once you have documents in the DB from various sources:

```bash
python -m src.uwss.cli score-keywords \
  --config config/config.yaml \
  --db data/uwss.sqlite \
  --min 0.0
```

The scoring algorithm (`src/uwss/score`):
- Tokenizes title, abstract, and (optionally) full‑text.
- Builds unigram and bigram lexicons from `domain_keywords`.
- Gives extra weight to matches in **title** and **abstract**.
- Adds a **quality bonus** when a document has DOI, long abstract, authors, affiliations, and/or full‑text.
- Records matched keywords in `keywords_found` for explainability.

The result: each document has a `relevance_score ∈ [0, 1]` and a list of matched keywords.


## Stage 3 – Export (JSONL)

Export a filtered set of high‑quality documents to JSONL:

```bash
python -m src.uwss.cli export \
  --db data/uwss.sqlite \
  --out data/corrosion_papers.jsonl \
  --require-match \
  --min-score 0.5 \
  --require-abstract \
  --min-abstract-length 80
```

Typical use:
- `--require-match`: ensure at least one keyword was matched.
- `--min-score`: keep only more relevant items.
- `--require-abstract` / `--min-abstract-length`: enforce minimum text quality.

You can then post‑process `data/corrosion_papers.jsonl` in notebooks or scripts.


## Stage 4 – Fetch PDFs

To download a small batch of open‑access PDFs:

```bash
python -m src.uwss.cli fetch \
  --db data/uwss.sqlite \
  --outdir data/files \
  --limit 20 \
  --config config/config.yaml
```

Under the hood (`src/uwss/crawl/__init__.py`):
- Calls **Unpaywall** to enrich open‑access information for documents with DOIs.
- Resolves publisher links where needed.
- Downloads PDFs (preferring `pdf_url`, then `source_url`).
- Writes files into `data/files` with stable names.
- Updates `local_path`, `pdf_status`, `http_status`, `mime_type`, `file_size`, `checksum_sha256` in the DB.


## Stage 5 – (Optional) Full‑Text Extraction

If you want full text for NLP or deeper analysis:

```bash
python -m src.uwss.cli extract-full-text \
  --db data/uwss.sqlite \
  --content-dir data/content \
  --limit 50
```

This step:
- Reads PDFs from `local_path`.
- Calls a parser (e.g., GROBID client) to extract structured text.
- Writes content to `data/content/…` and updates `content_path` and `content_chars`.


## Project Structure

```text
.
├── config/                    # Global + crawler configuration
│   ├── config.yaml            # Domain keywords, rate limits, negative keywords, etc.
│   └── web_crawler_scrapy.yaml  # Scrapy research-group crawler configuration
├── data/                      # Collected data (JSONL, SQLite DB, downloaded files)
├── src/
│   ├── uwss/                  # Main system code
│   │   ├── cli.py             # CLI entrypoint and command registration
│   │   ├── sources/           # Source adapters (Crossref, OpenAlex, S2, paperscraper, crawler)
│   │   ├── store/             # DB engines, models, migrations
│   │   ├── score/             # Keyword scoring
│   │   ├── crawl/             # Fetching, Unpaywall, scraping utilities
│   │   ├── parse/             # GROBID client and text extraction
│   │   └── ...                # Helpers, quality checks, utilities
│   └── data/                  # Sample/test outputs used during development
├── scripts/
│   ├── analysis/              # Data analysis / reporting tools
│   ├── testing/               # Legacy/manual testing scripts
│   └── utilities/             # Miscellaneous helpers (e.g., split_by_source.py)
├── tests/                     # Unit, integration, and end-to-end tests
├── docs/                      # Documentation, reports, and project notes
│   └── project/REPORT.md      # Project-level status / design report (optional)
└── web_crawler_scrapy_report.md  # Detailed report about the Scrapy web crawler adapter
```


## Summary for New Collaborators

- Edit `config/config.yaml` to define your **corrosion/durability** keyword space.
- Run the **library-based discover commands** to populate the DB from Crossref, OpenAlex, Semantic Scholar, PubMed, and arXiv.
- Use `score-keywords` and `export` to get clean **JSONL outputs**.
- Use `fetch` (and optionally `extract-full-text`) to obtain and analyze PDFs.
- Use the **Scrapy crawler** when you need **page‑level data from specific research groups or centers**, not covered well by standard APIs.

All experiments and test runs can be reproducibly described as sequences of CLI commands, making it easy for your teammates (or your professor) to understand **what you did, how to re‑run it, and how the data flows through the system**.
