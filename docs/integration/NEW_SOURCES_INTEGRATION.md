# New Sources Integration - Crossref, OpenAlex, Semantic Scholar

## Overview

Three new academic sources have been integrated into UWSS using well-tested Python libraries:
- **Crossref**: Using `habanero` library
- **OpenAlex**: Using `pyalex` library  
- **Semantic Scholar**: Using `semanticscholar` library

All integrations follow the same pattern as `paperscraper` integration, ensuring consistency and maintainability.

## Libraries Used

### 1. Crossref - `habanero`
- **Library**: `habanero>=1.2.0`
- **GitHub**: https://github.com/sckott/habanero
- **Documentation**: https://pypi.org/project/habanero/
- **Features**: Official Crossref API client, well-maintained

### 2. OpenAlex - `pyalex`
- **Library**: `pyalex>=1.0.0`
- **GitHub**: https://github.com/J535D165/pyalex
- **Documentation**: https://pyalex.readthedocs.io/
- **Features**: Lightweight Python interface for OpenAlex API

### 3. Semantic Scholar - `semanticscholar`
- **Library**: `semanticscholar>=2.0.0`
- **GitHub**: https://github.com/danielnsilva/semanticscholar
- **Documentation**: https://pypi.org/project/semanticscholar/
- **Features**: Unofficial but well-tested Semantic Scholar API client

## Installation

Install the required libraries:

```bash
pip install habanero pyalex semanticscholar
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

## Architecture

Each source follows the same structure as `paperscraper`:

```
src/uwss/sources/
├── crossref_lib/
│   ├── __init__.py
│   ├── adapter.py      # discover_crossref() function
│   └── mapper.py       # map_crossref_to_document() function
├── openalex_lib/
│   ├── __init__.py
│   ├── adapter.py      # discover_openalex() function
│   └── mapper.py       # map_openalex_to_document() function
└── semantic_scholar_lib/
    ├── __init__.py
    ├── adapter.py      # discover_semantic_scholar() function
    └── mapper.py        # map_semantic_scholar_to_document() function
```

## CLI Commands

### Crossref Discovery

```bash
python -m src.uwss.cli crossref-lib-discover \
    --config config/config.yaml \
    --db data/uwss.sqlite \
    --max 100 \
    --year 2020
```

### OpenAlex Discovery

**Note**: `contact_email` is REQUIRED for OpenAlex (per ToS). Set it in `config.yaml`:

```yaml
contact_email: your-email@example.com
```

```bash
python -m src.uwss.cli openalex-lib-discover \
    --config config/config.yaml \
    --db data/uwss.sqlite \
    --max 100 \
    --year 2020
```

### Semantic Scholar Discovery

```bash
python -m src.uwss.cli semantic-scholar-lib-discover \
    --config config/config.yaml \
    --db data/uwss.sqlite \
    --max 100 \
    --year 2020 \
    --api-key YOUR_API_KEY  # Optional, for higher rate limits
```

## Configuration

Add to `config/config.yaml`:

```yaml
domain_keywords:
  - keyword1
  - keyword2
  # ...

contact_email: your-email@example.com  # Required for OpenAlex, recommended for Crossref
semantic_scholar_api_key: YOUR_API_KEY  # Optional, for higher rate limits
```

## Features

### All Sources Support:
- ✅ Keyword-based discovery
- ✅ Year filtering
- ✅ Max records limit
- ✅ Automatic deduplication (by DOI, URL, or title)
- ✅ Error handling and retry logic
- ✅ Rate limiting
- ✅ Mapping to universal Document schema

### Source-Specific Features:

#### Crossref
- Polite rate limiting (1 req/sec recommended)
- Abstract support
- PDF URL detection
- DOI-based deduplication

#### OpenAlex
- **REQUIRES** contact_email (per ToS)
- Fast requests (0.1 sec throttle)
- Open access status detection
- Cursor-based pagination

#### Semantic Scholar
- Optional API key for higher rate limits
- Abstract support
- Open access PDF detection
- Citation information available

## Data Mapping

All sources map to the universal `Document` schema:

- `source`: Source identifier (e.g., "crossref", "openalex", "semantic_scholar")
- `title`: Paper title
- `abstract`: Abstract text (if available)
- `authors`: JSON array of author names
- `doi`: DOI identifier
- `year`: Publication year
- `venue`: Journal/conference name
- `pdf_url`: PDF download URL (if available)
- `open_access`: Boolean open access flag
- `url_hash_sha1`: Hash for deduplication

## Testing

Test each source with a small batch:

```bash
# Test Crossref
python -m src.uwss.cli crossref-lib-discover --max 10 --config config/config.yaml --db data/test.sqlite

# Test OpenAlex
python -m src.uwss.cli openalex-lib-discover --max 10 --config config/config.yaml --db data/test.sqlite

# Test Semantic Scholar
python -m src.uwss.cli semantic-scholar-lib-discover --max 10 --config config/config.yaml --db data/test.sqlite
```

## Known Limitations

1. **Crossref**: Abstracts may not be available for all papers
2. **OpenAlex**: Abstracts require fetching full work details (not included in basic search)
3. **Semantic Scholar**: API key recommended for production use (higher rate limits)

## Next Steps

1. Test all three sources with real API calls
2. Verify data quality and completeness
3. Adjust mappers if needed based on real data
4. Add to main discovery pipeline if desired

## Troubleshooting

### Import Errors
If you see import errors, make sure libraries are installed:
```bash
pip install habanero pyalex semanticscholar
```

### OpenAlex Errors
If OpenAlex fails, check that `contact_email` is set in config.yaml

### Rate Limiting
If you hit rate limits:
- Crossref: Increase throttle_sec (default: 1.0)
- OpenAlex: Increase throttle_sec (default: 0.1)
- Semantic Scholar: Use API key for higher limits

## References

- Crossref API: https://www.crossref.org/categories/apis/
- OpenAlex API: https://docs.openalex.org/
- Semantic Scholar API: https://www.semanticscholar.org/product/api

