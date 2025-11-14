# UWSS – Universal Web Scraping System

A universal, config-driven academic data harvesting and web scraping system designed to work with any academic database, research repository, or web source. The system uses a plugin-based adapter architecture that allows switching between sources or topics by changing configuration only, without rewriting the pipeline.

## Overview

UWSS is built to be **truly universal**:
- **Multi-source support**: Works with structured databases (arXiv, TRB/TRID, Crossref, OpenAlex) via official APIs/protocols, and unstructured web content (research group websites, personal pages, scattered PDFs) via intelligent crawling
- **Universal pipeline**: The same pipeline (discover → score → export → fetch → extract) works for any source; only the discovery adapter differs
- **Config-driven**: Switch topics or sources by editing `config/config.yaml`; no code changes required
- **Policy-compliant**: Respects `robots.txt`, Terms of Service, and uses official channels (OAI-PMH, REST APIs) when available
- **Agent-ready architecture**: Designed to support AI/agent-based autonomous discovery and refinement in future phases

## Key Features

- **Database-first architecture**: Postgres (production) or SQLite (local) as single source of truth
- **Idempotent operations**: Safe to rerun; checkpoints and upserts prevent duplicate work
- **Comprehensive metadata extraction**: Title, abstract, authors, affiliations, keywords, DOI, access flags (open access, paywall, abstract-only)
- **Quality assurance**: Keyword-based relevance scoring with negative keywords, sampling tools for manual review
- **Reproducible**: Version-pinned URLs, SHA256 checksums, sidecar metadata files
- **Observable**: Structured JSON logs, metrics, validation tools

## Architecture

### Universal Pipeline

```
DISCOVER → SCORE → EXPORT → FETCH → EXTRACT
   ↑
   └─ Source-specific adapters (OAI-PMH, REST API, sitemap crawler, web spider)
```

### Adapter Pattern

Each source has its own discovery adapter, but all sources share the same pipeline:

- **arXiv**: OAI-PMH adapter → official metadata harvesting
- **TRB/TRID**: Sitemap crawler → parse sitemap.xml, crawl HTML pages
- **Web of Science/Scopus**: REST API adapter (requires institutional subscription + API keys)
- **Web crawling**: Scrapy-based spider for research groups, personal pages, scattered PDFs

After discovery, all documents flow through the same pipeline:
- **Score**: Keyword-based relevance scoring (configurable positive/negative keywords)
- **Export**: Filter and export to JSONL/CSV with various criteria
- **Fetch**: Download PDFs with retry/backoff, rate limiting, integrity checks
- **Extract**: Full-text extraction (GROBID, local PDF parsing)

### Database Schema

All sources map to the same universal `Document` model:

## Project Structure

```
uwss/
├── config/                 # Configuration files
│   ├── config.yaml        # Main configuration
│   └── keywords*.txt      # Keyword files
├── data/                  # Production data and PDFs
│   ├── paperscraper_export.jsonl
│   ├── new_sources_final.jsonl
│   └── paperscraper_pdfs/
├── docs/                  # Documentation
│   ├── development/       # Development docs
│   ├── integration/       # Integration guides
│   ├── project/          # Project docs
│   └── reports/          # Analysis reports
├── scripts/               # Utility scripts
│   ├── analysis/         # Data analysis scripts
│   ├── testing/          # Testing scripts
│   └── utilities/        # Maintenance scripts
├── src/uwss/             # Main source code
│   ├── cli/              # Command-line interface
│   ├── sources/          # Source adapters
│   └── [modules]/        # Core modules
├── test/                 # Test artifacts and data
│   ├── outputs/          # Test results
│   ├── metrics/          # Performance metrics
│   ├── databases/        # Test databases
│   └── reports/          # Test reports
└── tests/                # Unit/integration tests
```
- Identification: `title`, `abstract`, `authors`, `affiliations`, `keywords`, `doi`, `year`
- Source tracking: `source`, `source_url`, `landing_url`
- Access flags: `oa_status`, `pdf_url`, `pdf_status`
- Scoring: `relevance_score`, `keywords_found`
- Files: `local_path`, `content_path`, `checksum_sha256`

## Quick Start

### Prerequisites

- Python 3.8+
- (Optional) Postgres for production use
- (Optional) GROBID service for advanced PDF parsing

### Installation

```bash
# Clone repository
git clone <repository-url>
cd uwss

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Basic Workflow (arXiv Example)

1. **Validate configuration**
```bash
python -m src.uwss.cli config-validate --config config/config.yaml
```

2. **Harvest metadata** (arXiv via OAI-PMH)
```bash
python -m src.uwss.cli arxiv-harvest-oai \
  --from 2024-10-01 --max 100 --resume \
  --metrics-out data/runs/arxiv_h.json
```

3. **Score by relevance**
```bash
python -m src.uwss.cli score-keywords \
  --config config/config.yaml \
  --db data/uwss.sqlite
```

4. **Export filtered results**
```bash
python -m src.uwss.cli export \
  --db data/uwss.sqlite \
  --out data/export/filtered.jsonl \
  --require-match --year-min 1995 \
  --ids-out data/export/filtered_ids.txt
```

5. **Fetch PDFs** (only for exported IDs)
```bash
python -m src.uwss.cli arxiv-fetch-pdf \
  --ids-file data/export/filtered_ids.txt \
  --limit 200 \
  --metrics-out data/runs/arxiv_p.json
```

6. **Extract full text**
```bash
python -m src.uwss.cli extract-full-text \
  --db data/uwss.sqlite \
  --content-dir data/content \
  --limit 200
```

### Switching Sources

To use a different source, simply change the discovery command:

```bash
# TRB/TRID (sitemap crawling - coming soon)
python -m src.uwss.cli trid-discover-sitemap --max 100

# After discovery, same pipeline:
python -m src.uwss.cli score-keywords --config config/config.yaml
python -m src.uwss.cli export --require-match
python -m src.uwss.cli fetch-pdfs --ids-file ids.txt
```

## Configuration

Edit `config/config.yaml` to customize:

- **Domain keywords**: Positive keywords for relevance scoring
- **Negative keywords**: Terms to penalize/exclude (e.g., physics terms for civil engineering focus)
- **Rate limits**: Throttling and jitter for polite crawling
- **Contact info**: Email and User-Agent for compliance

Example:
```yaml
domain_keywords:
  - "concrete deterioration"
  - "chloride diffusion"
  - "corrosion"

negative_keywords:
  - "quantum"
  - "neural network"
  - "machine learning"

rate_limits:
  throttle_sec: 1.0
  jitter_sec: 0.5
```

## Data Storage

- **Database**: `data/uwss.sqlite` (or Postgres via `--db-url`)
  - Tables: `documents`, `visited_urls`, `ingestion_state`
- **PDFs**: `data/files/{source}_{id}.pdf` with sidecar `{source}_{id}.meta.json`
- **Content**: `data/content/doc_{id}.txt` (extracted full text)
- **Metrics**: `data/runs/*.json` (harvest/fetch/extract metrics)
- **Policy snapshots**: `docs/policies/{source}/` (compliance artifacts)

## Monitoring & Quality Assurance

### Recent Downloads
```bash
python -m src.uwss.cli recent-downloads \
  --hours 1 --limit 10 \
  --source arxiv \
  --json-out data/runs/recent.json
```

### Sampling for Manual Review
```bash
python -m src.uwss.cli sample-records \
  --db data/uwss.sqlite \
  --out data/samples/manual_review.jsonl \
  --n 50 --pdf-only --require-match
```

### Validation & Statistics
```bash
python -m src.uwss.cli validate \
  --db data/uwss.sqlite \
  --json-out data/export/validation.json

python -m src.uwss.cli stats \
  --db data/uwss.sqlite \
  --json-out data/export/stats.json
```

## Current Status

### ✅ Implemented

- **arXiv integration**: Full OAI-PMH harvesting, canonical PDF fetching
- **Generic adapters**: OAI-PMH and RSS/Atom parsers (reusable for any source)
- **Scoring system**: Keyword-based relevance with negative keywords
- **Export system**: Flexible filtering and export to JSONL/CSV
- **PDF fetching**: Atomic writes, SHA256 checksums, retry/backoff
- **Full-text extraction**: Local PDF parsing, GROBID integration (optional)
- **Code quality**: Modular architecture, standardized HTTP client, constants

### 🚧 In Progress

- **TRB/TRID integration**: Sitemap crawling adapter (identified correct approach)
- **Web crawling expansion**: Research groups, personal pages, scattered PDFs
- **Researcher finder**: Extract researcher info, ORCID integration

### 📋 Planned

- **Subscription databases**: Web of Science, Scopus, ScienceDirect (requires institutional access + API keys)
- **Agent framework**: LLM-based autonomous discovery and refinement
- **Cloud deployment**: AWS-hosted platform with usage instructions

## Compliance & Policy

UWSS is designed to be policy-compliant:

- **Official channels only**: Uses OAI-PMH, REST APIs, sitemap crawling (not unauthorized scraping)
- **Respects robots.txt**: Checks and honors robots.txt before crawling
- **Rate limiting**: Configurable throttling and jitter to avoid overwhelming servers
- **Policy snapshots**: Stores compliance artifacts (Identify responses, robots.txt, links)
- **Terms of Service**: Subscription databases only integrated with proper institutional access and API credentials

## Roadmap

### Phase 1: Core Infrastructure ✅
- Universal pipeline architecture
- arXiv integration (OAI-PMH)
- Generic adapters (OAI-PMH, RSS)

### Phase 2: Multi-Source Support 🚧
- TRB/TRID (sitemap crawling)
- Crossref, OpenAlex, CORE
- Subscription databases (with proper access)

### Phase 3: Web Crawling Expansion
- Research group website discovery
- Personal faculty page crawling
- Scattered PDF discovery
- Search API integration

### Phase 4: Researcher & Group Finder
- Extract researcher information
- ORCID integration
- Contact info extraction
- Institution tracking

### Phase 5: Agent Framework
- LLM orchestration
- Autonomous discovery
- Iterative refinement
- Tool integration

## Contributing

This project follows a modular, adapter-based architecture. To add a new source:

1. Create a discovery adapter in `src/uwss/sources/{source_name}/`
2. Map source-specific metadata to the universal `Document` schema
3. Add CLI command in `src/uwss/cli/commands/`
4. Test with a small batch
5. Document access policy and compliance requirements

## License

[Specify license]

## Contact

[Specify contact information]
