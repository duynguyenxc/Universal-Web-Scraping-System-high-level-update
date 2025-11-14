# Development Plan - Universal Web Scraping System

## Executive Summary

This document outlines a phased development plan for building a truly universal web scraping system that meets the professor's requirements. The plan is based on:
- Current codebase status (arXiv integration complete, architecture ready)
- Best practices from similar projects (Scrapy, AutoScraper, academic crawlers)
- Realistic timelines and risk assessments
- Dependencies and priorities

**Total Estimated Timeline**: 9 weeks (~2 months)

---

## Phase 0: Foundation & Preparation ✅ (COMPLETED)

### Status: ✅ Complete

**Deliverables:**
- ✅ Universal pipeline architecture (discover → score → export → fetch → extract)
- ✅ arXiv integration via OAI-PMH
- ✅ Generic OAI-PMH and RSS/Atom adapters
- ✅ Database schema with comprehensive metadata fields
- ✅ Modular CLI architecture
- ✅ Code quality tools (black, ruff, mypy, .editorconfig)

**Key Achievements:**
- Architecture supports adapter pattern for any source
- Database schema universal (works for all sources)
- Config-driven system (switch topics/sources via config)

**Duration**: Already completed

---

## Phase 1: Multi-Source Database Integration (Weeks 1-2)

### Goal
Extend system to support multiple academic databases beyond arXiv, starting with open/public sources.

### Sub-Phase 1.1: TRB/TRID Sitemap Crawling (Week 1, Days 1-3)

**Priority**: HIGH (critical for concrete deterioration topic)

#### Technologies & Libraries
- **Sitemap parsing**: `xml.etree.ElementTree` (built-in) hoặc `lxml.etree`
- **HTML parsing**: `BeautifulSoup4` (bs4) hoặc `lxml.html`
- **HTTP client**: `requests` (via `src/uwss/utils/http.py`)
- **Robots.txt**: `urllib.robotparser` (built-in)
- **Rate limiting**: Custom throttle với `time.sleep()` + jitter

#### Algorithms & Approach

**1. Sitemap Parsing Algorithm:**
```python
# Algorithm: Parse sitemap.xml recursively
def parse_sitemap(sitemap_url: str) -> List[str]:
    """
    Algorithm:
    1. Fetch sitemap.xml
    2. Parse XML (namespace: http://www.sitemaps.org/schemas/sitemap/0.9)
    3. Extract <loc> tags (URLs)
    4. If sitemap index (<sitemapindex>), recursively parse child sitemaps
    5. Return list of URLs
    """
    # Implementation using xml.etree.ElementTree
    # Handle both sitemap and sitemapindex
    # Support recursive parsing for nested sitemaps
```

**2. Robots.txt Checking Algorithm:**
```python
# Algorithm: Check robots.txt before crawling
def can_fetch(url: str, user_agent: str) -> bool:
    """
    Algorithm:
    1. Extract domain from URL
    2. Fetch robots.txt from domain/robots.txt
    3. Parse robots.txt using urllib.robotparser
    4. Check if user_agent can fetch URL path
    5. Return True/False
    """
    # Use RobotFileParser from urllib.robotparser
    # Cache robots.txt per domain
    # Respect crawl-delay if specified
```

**3. HTML Metadata Extraction Algorithm:**
```python
# Algorithm: Extract metadata from HTML
def extract_metadata(html: str, url: str) -> Dict:
    """
    Algorithm:
    1. Parse HTML with BeautifulSoup
    2. Try multiple selectors (fallback strategy):
       - Title: <h1>, <title>, meta[property="og:title"]
       - Abstract: .abstract, #abstract, meta[name="description"]
       - Authors: .authors, .author, meta[name="author"]
       - DOI: meta[name="citation_doi"], .doi
       - Year: meta[name="citation_publication_date"], .year
    3. Clean and normalize extracted text
    4. Return structured dict
    """
    # Use BeautifulSoup
    # Try multiple selectors with priority
    # Fallback to regex patterns if selectors fail
    # Normalize whitespace, encoding
```

**4. Rate Limiting Algorithm:**
```python
# Algorithm: Polite rate limiting
def throttle_with_jitter(base_delay: float, jitter: float):
    """
    Algorithm:
    1. Calculate delay = base_delay + random(0, jitter)
    2. Sleep for delay seconds
    3. Track requests per domain
    4. Respect robots.txt crawl-delay
    """
    # Use time.sleep() + random.uniform()
    # Track last_request_time per domain
    # Enforce minimum delay between requests
```

#### Implementation Details

**File Structure:**
```
src/uwss/
├── discovery/
│   └── sitemap.py          # Generic sitemap parser
├── sources/
│   └── trid/
│       ├── __init__.py
│       ├── sitemap_parser.py   # TRID-specific sitemap logic
│       ├── html_parser.py      # HTML metadata extraction
│       └── adapter.py          # Map to Document schema
└── cli/
    └── commands/
        └── trid_discover.py    # CLI command
```

**Code Example (sitemap.py):**
```python
# src/uwss/discovery/sitemap.py
import xml.etree.ElementTree as ET
from typing import Iterator, List
import requests
from urllib.parse import urljoin, urlparse

def parse_sitemap(sitemap_url: str) -> Iterator[str]:
    """Parse sitemap.xml and yield URLs."""
    resp = requests.get(sitemap_url, timeout=30)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    
    # Handle sitemapindex (nested sitemaps)
    ns = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    
    if root.tag.endswith('sitemapindex'):
        # Recursive: parse child sitemaps
        for sitemap in root.findall('.//sitemap:sitemap', ns):
            child_url = sitemap.find('sitemap:loc', ns).text
            yield from parse_sitemap(child_url)
    else:
        # Extract URLs
        for url_elem in root.findall('.//sitemap:url', ns):
            loc = url_elem.find('sitemap:loc', ns)
            if loc is not None:
                yield loc.text
```

**Code Example (html_parser.py):**
```python
# src/uwss/sources/trid/html_parser.py
from bs4 import BeautifulSoup
from typing import Dict, Optional
import re

def extract_trid_metadata(html: str, url: str) -> Dict:
    """Extract metadata from TRID HTML page."""
    soup = BeautifulSoup(html, 'lxml')
    
    # Title: try multiple selectors
    title = (
        soup.select_one('h1.title') or
        soup.select_one('meta[property="og:title"]') or
        soup.find('title')
    )
    title = title.get_text(strip=True) if title else None
    
    # Abstract: try multiple selectors
    abstract = (
        soup.select_one('.abstract') or
        soup.select_one('#abstract') or
        soup.select_one('meta[name="description"]')
    )
    abstract = abstract.get_text(strip=True) if abstract else None
    
    # Authors: extract from multiple patterns
    authors = []
    author_elements = soup.select('.author, .authors, meta[name="citation_author"]')
    for elem in author_elements:
        if elem.name == 'meta':
            authors.append(elem.get('content', ''))
        else:
            authors.append(elem.get_text(strip=True))
    
    # DOI: try meta tags and text patterns
    doi = None
    doi_meta = soup.find('meta', {'name': 'citation_doi'})
    if doi_meta:
        doi = doi_meta.get('content')
    else:
        # Regex fallback: 10.xxxx/xxxx
        doi_match = re.search(r'10\.\d+/[^\s]+', html)
        if doi_match:
            doi = doi_match.group(0)
    
    return {
        'title': title,
        'abstract': abstract,
        'authors': authors,
        'doi': doi,
        'source_url': url,
        'source': 'trid'
    }
```

**Tasks:**
1. **Research & Analysis** (Day 1)
   - Verify TRID sitemap structure: `https://trid.trb.org/sitemap.xml`
   - Check robots.txt compliance
   - Analyze HTML structure of TRID pages (inspect 5-10 sample pages)
   - Identify metadata extraction points (CSS selectors, XPath, meta tags)
   - Document findings in `docs/sources/trid/analysis.md`

2. **Implementation** (Day 2)
   - Create `src/uwss/discovery/sitemap.py` (generic sitemap parser)
   - Create `src/uwss/sources/trid/` module:
     - `sitemap_parser.py`: Parse sitemap.xml
     - `html_parser.py`: Extract metadata from HTML pages (BeautifulSoup)
     - `adapter.py`: Map to universal Document schema
   - Create CLI command: `trid-discover-sitemap`
   - Add rate limiting and robots.txt checking (urllib.robotparser)
   - Integrate with existing HTTP client (`src/uwss/utils/http.py`)

3. **Testing & Validation** (Day 3)
   - Test with small batch (10-20 records)
   - Manual review of extracted metadata
   - Verify compliance (robots.txt, rate limits)
   - Fix bugs and edge cases
   - Scale to 50-100 records

**Deliverables:**
- ✅ TRB/TRID sitemap crawler adapter
- ✅ CLI command `trid-discover-sitemap`
- ✅ Test results and validation report
- ✅ Documentation: `docs/sources/trid/`

**Success Criteria:**
- Successfully harvest 50-100 TRID records
- Metadata extraction accuracy >90%
- Compliance with robots.txt
- No errors in pipeline (score → export → fetch)
- **Demo**: Show list of harvested papers with metadata

**Risks & Mitigations:**
- **Risk**: HTML structure changes → **Mitigation**: Multiple selectors, fallback strategies
- **Risk**: Rate limiting issues → **Mitigation**: Configurable throttle, respect robots.txt
- **Risk**: Timeout errors → **Mitigation**: Retry logic, timeout handling

**Estimated Time**: 2-3 days

---

### Sub-Phase 1.2: Open Academic Databases (Week 1, Days 4-5)

**Priority**: MEDIUM (validates universal architecture)

#### Technologies & Libraries
- **REST API clients**: `requests` (via `src/uwss/utils/http.py`)
- **JSON parsing**: `json` (built-in)
- **OAI-PMH**: Reuse existing `src/uwss/discovery/oai.py`
- **Rate limiting**: Track requests per API, respect limits

#### Algorithms & Approach

**1. Crossref REST API Algorithm:**
```python
# Algorithm: Query Crossref API
def query_crossref(keywords: List[str], limit: int = 100) -> Iterator[Dict]:
    """
    Algorithm:
    1. Build query string from keywords (OR logic)
    2. Call GET https://api.crossref.org/works?query={query}&rows={limit}
    3. Parse JSON response
    4. Extract items from response['message']['items']
    5. Map each item to Document schema:
       - title: item['title'][0]
       - abstract: item.get('abstract')
       - authors: [a['given'] + ' ' + a['family'] for a in item.get('author', [])]
       - doi: item.get('DOI')
       - year: item.get('published-print', {}).get('date-parts', [[None]])[0][0]
    6. Yield mapped documents
    """
    # Use requests.get() with query parameters
    # Handle pagination (cursor-based)
    # Rate limit: 1 request/second (polite)
```

**2. OpenAlex REST API Algorithm:**
```python
# Algorithm: Query OpenAlex API
def query_openalex(keywords: List[str], limit: int = 100) -> Iterator[Dict]:
    """
    Algorithm:
    1. Build search query: "|".join(keywords)
    2. Call GET https://api.openalex.org/works?search={query}&per_page={limit}
    3. Parse JSON response
    4. Extract items from response['results']
    5. Map each item to Document schema:
       - title: item['title']
       - abstract: item.get('abstract')
       - authors: [a['author']['display_name'] for a in item.get('authorships', [])]
       - doi: item.get('doi')
       - year: item.get('publication_year')
    6. Yield mapped documents
    """
    # Use requests.get() with query parameters
    # Handle pagination (page-based)
    # Rate limit: Track daily quota (100k/day)
```

**3. CORE/DOAJ OAI-PMH Algorithm:**
```python
# Algorithm: Reuse OAI-PMH adapter
def harvest_core_oai(from_date: str = None) -> Iterator[Dict]:
    """
    Algorithm:
    1. Use existing iter_oai_dc() from src/uwss/discovery/oai.py
    2. Pass base_url='https://core.ac.uk/oai'
    3. Pass metadataPrefix='oai_dc'
    4. Map OAI-DC fields to Document schema (same as arXiv)
    """
    # Reuse existing OAI-PMH adapter
    # Just change base_url
    # Same mapping logic as arXiv
```

#### Implementation Details

**Crossref Adapter Code:**
```python
# src/uwss/sources/crossref/adapter.py
import requests
from typing import Iterator, Dict, List
from ..utils.http import session_with_retries

def discover_crossref(keywords: List[str], limit: int = 100) -> Iterator[Dict]:
    """Discover papers from Crossref."""
    session = session_with_retries()
    query = ' OR '.join(keywords)
    
    params = {
        'query': query,
        'rows': min(limit, 1000),  # Crossref max 1000 per request
        'sort': 'relevance',
        'order': 'desc'
    }
    
    url = 'https://api.crossref.org/works'
    
    while True:
        resp = session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        items = data.get('message', {}).get('items', [])
        for item in items:
            yield {
                'title': ' '.join(item.get('title', [''])),
                'abstract': item.get('abstract', ''),
                'authors': [
                    f"{a.get('given', '')} {a.get('family', '')}".strip()
                    for a in item.get('author', [])
                ],
                'doi': item.get('DOI', '').lower(),
                'year': _extract_year(item),
                'source': 'crossref',
                'source_url': f"https://doi.org/{item.get('DOI', '')}",
                'pdf_url': _find_pdf_url(item),
            }
        
        # Pagination
        if len(items) < params['rows']:
            break
        # Crossref uses cursor-based pagination
        next_cursor = data.get('message', {}).get('next-cursor')
        if not next_cursor:
            break
        params['cursor'] = next_cursor
```

**OpenAlex Adapter Code:**
```python
# src/uwss/sources/openalex/adapter.py
import requests
from typing import Iterator, Dict, List
from ..utils.http import session_with_retries

def discover_openalex(keywords: List[str], limit: int = 100) -> Iterator[Dict]:
    """Discover papers from OpenAlex."""
    session = session_with_retries()
    search_query = '|'.join(keywords)
    
    url = 'https://api.openalex.org/works'
    params = {
        'search': search_query,
        'per_page': min(limit, 200),  # OpenAlex max 200 per page
        'sort': 'relevance_score:desc'
    }
    
    page = 1
    while True:
        params['page'] = page
        resp = session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        results = data.get('results', [])
        for item in results:
            yield {
                'title': item.get('title', ''),
                'abstract': item.get('abstract', ''),
                'authors': [
                    a.get('author', {}).get('display_name', '')
                    for a in item.get('authorships', [])
                ],
                'doi': item.get('doi', '').replace('https://doi.org/', '').lower(),
                'year': item.get('publication_year'),
                'source': 'openalex',
                'source_url': item.get('id', ''),
                'pdf_url': item.get('open_access', {}).get('oa_url', ''),
                'oa_status': 'open' if item.get('open_access', {}).get('is_oa') else 'closed'
            }
        
        # Pagination
        if not data.get('meta', {}).get('next'):
            break
        page += 1
        if page * params['per_page'] > limit:
            break
```

**Sources to integrate:**
1. **Crossref** (REST API)
   - API: `https://api.crossref.org/works`
   - Documentation: https://api.crossref.org/
   - Rate limit: Polite use (no official limit, but be respectful)
   - **Technology**: REST API, JSON response, cursor-based pagination

2. **OpenAlex** (REST API)
   - API: `https://api.openalex.org/works`
   - Documentation: https://docs.openalex.org/
   - Rate limit: 100,000 requests/day (free tier)
   - **Technology**: REST API, JSON response, page-based pagination

3. **CORE** (OAI-PMH)
   - Endpoint: `https://core.ac.uk/oai`
   - Can reuse existing OAI-PMH adapter
   - **Technology**: OAI-PMH protocol, XML response

4. **DOAJ** (OAI-PMH)
   - Endpoint: `https://doaj.org/oai`
   - Can reuse existing OAI-PMH adapter
   - **Technology**: OAI-PMH protocol, XML response

**Tasks:**
1. **Crossref Adapter** (Day 4, Morning)
   - Create `src/uwss/sources/crossref/adapter.py`
   - Implement REST API client (requests)
   - Map Crossref JSON to Document schema
   - Handle pagination (cursor-based)
   - Add CLI command: `crossref-discover`

2. **OpenAlex Adapter** (Day 4, Afternoon)
   - Create `src/uwss/sources/openalex/adapter.py`
   - Implement REST API client (requests)
   - Map OpenAlex JSON to Document schema
   - Handle pagination (page-based)
   - Track daily quota
   - Add CLI command: `openalex-discover`

3. **CORE & DOAJ** (Day 5, Morning)
   - Reuse OAI-PMH adapter (`src/uwss/discovery/oai.py`)
   - Create source-specific wrappers
   - Add CLI commands: `core-discover`, `doaj-discover`

4. **Testing** (Day 5, Afternoon)
   - Test each source with small batch (10-20 records)
   - Verify metadata mapping
   - Test end-to-end pipeline

**Deliverables:**
- ✅ Crossref adapter
- ✅ OpenAlex adapter
- ✅ CORE adapter (OAI-PMH wrapper)
- ✅ DOAJ adapter (OAI-PMH wrapper)
- ✅ CLI commands for each source
- ✅ Documentation: `docs/sources/{source}/`

**Success Criteria:**
- Each source successfully harvests 20+ records
- Metadata correctly mapped to universal schema
- Pipeline works end-to-end (discover → score → export)
- **Deduplication**: DOI-based dedup across sources implemented early
- **Demo**: Show cross-source deduplication working (same paper from multiple sources)

**Estimated Time**: 1.5-2 days

---

### Sub-Phase 1.3: Integration Testing & Documentation (Week 2, Days 1-2)

**Tasks:**
1. **End-to-End Testing**
   - Test all sources together
   - **Deduplication**: Implement DOI-based dedup across sources early
   - Verify deduplication (DOI, title, url_hash)
   - Test cross-source scoring and export

2. **Performance Testing**
   - Measure harvest speed for each source
   - Identify bottlenecks
   - Optimize if needed

3. **Documentation**
   - Update README with new sources
   - Create source-specific documentation
   - Document API requirements and rate limits

4. **Demo Preparation**
   - Prepare sample output showing papers from multiple sources
   - Show deduplication working (same paper from arXiv + Crossref)
   - Document findings and quality metrics

**Deliverables:**
- ✅ Integration test results
- ✅ Performance benchmarks
- ✅ Updated documentation
- ✅ Demo: Cross-source deduplication example

**Estimated Time**: 1-2 days

---

## Phase 2: Web Crawling Expansion (Weeks 3-4)

### Goal
Extend system beyond structured databases to crawl unstructured web content (research groups, personal pages, scattered PDFs).

### Sub-Phase 2.1: Enhanced Scrapy Infrastructure (Week 3, Days 1-2)

**Priority**: HIGH (core requirement for "web crawling thực thụ")

#### Technologies & Libraries
- **Scrapy**: Framework chính cho web crawling
- **BeautifulSoup4**: HTML parsing (backup cho Scrapy's built-in selectors)
- **lxml**: Fast XML/HTML parser (Scrapy default)
- **urllib.robotparser**: Robots.txt checking
- **PyPDF2** hoặc **pdfplumber**: PDF metadata extraction
- **regex**: Pattern matching cho academic content

#### Algorithms & Approach

**1. Scrapy Spider Architecture:**
```python
# Algorithm: Generic web spider
class GenericSpider(scrapy.Spider):
    """
    Algorithm:
    1. Start from seed URLs (from config)
    2. Parse robots.txt before crawling
    3. Extract metadata from HTML:
       - Title, abstract, authors
       - PDF links
       - Publication links
    4. Follow links with depth control (max_depth)
    5. Rate limit per domain (respect crawl-delay)
    6. Yield items to pipeline
    """
    # Use Scrapy's built-in features:
    # - LinkExtractor for following links
    # - ItemLoader for structured extraction
    # - Middleware for rate limiting
```

**2. Robots.txt Middleware Algorithm:**
```python
# Algorithm: Robots.txt compliance middleware
class RobotsTxtMiddleware:
    """
    Algorithm:
    1. Before each request, check robots.txt
    2. Use urllib.robotparser.RobotFileParser
    3. Cache robots.txt per domain (TTL: 1 hour)
    4. Check can_fetch(url, user_agent)
    5. If not allowed, drop request
    6. Respect crawl-delay if specified
    """
    # Implement as Scrapy Downloader Middleware
    # Cache robots.txt in memory
    # Track last_request_time per domain
```

**3. Rate Limiting Algorithm:**
```python
# Algorithm: Domain-based rate limiting
def throttle_per_domain(domain: str, crawl_delay: float):
    """
    Algorithm:
    1. Track last_request_time per domain
    2. Calculate time_since_last = now - last_request_time[domain]
    3. If time_since_last < crawl_delay:
       - sleep(crawl_delay - time_since_last)
    4. Update last_request_time[domain] = now
    5. Add jitter: sleep(random(0, jitter))
    """
    # Use asyncio.sleep() or time.sleep()
    # Store state in middleware
    # Configurable per domain
```

**4. HTML Metadata Extraction Algorithm:**
```python
# Algorithm: Multi-strategy metadata extraction
def extract_metadata(html: str, url: str) -> Dict:
    """
    Algorithm:
    1. Parse HTML with Scrapy Selector or BeautifulSoup
    2. Try multiple extraction strategies (priority order):
       Strategy 1: Academic meta tags
         - citation_title, citation_author, citation_abstract
         - citation_doi, citation_publication_date
       Strategy 2: Common HTML patterns
         - <h1> for title
         - .abstract, #abstract for abstract
         - .author, .authors for authors
       Strategy 3: Heuristic patterns
         - Title: First <h1> or <title>
         - Abstract: Longest paragraph or <meta description>
         - Authors: Email patterns, "Author:" labels
    3. Score confidence for each extracted field
    4. Return best match with confidence scores
    """
    # Use multiple selectors with fallback
    # Pattern matching for emails, DOIs
    # Confidence scoring
```

#### Implementation Details

**Scrapy Middleware Code:**
```python
# src/uwss/crawl/scrapy_project/middlewares.py
from scrapy.downloadermiddlewares.robotstxt import RobotsTxtMiddleware
from urllib.robotparser import RobotFileParser
import time
from collections import defaultdict

class PoliteRobotsTxtMiddleware(RobotsTxtMiddleware):
    """Enhanced robots.txt middleware with caching."""
    
    def __init__(self):
        self.parsers = {}  # Cache RobotFileParser per domain
        self.last_request = defaultdict(float)  # Track last request time
    
    def process_request(self, request, spider):
        domain = request.url.split('/')[2]
        
        # Check robots.txt
        if domain not in self.parsers:
            rp = RobotFileParser()
            rp.set_url(f"https://{domain}/robots.txt")
            rp.read()
            self.parsers[domain] = rp
        
        parser = self.parsers[domain]
        if not parser.can_fetch(spider.settings.get('USER_AGENT'), request.url):
            spider.logger.info(f"Blocked by robots.txt: {request.url}")
            return None  # Drop request
        
        # Respect crawl-delay
        crawl_delay = parser.crawl_delay(spider.settings.get('USER_AGENT'))
        if crawl_delay:
            elapsed = time.time() - self.last_request[domain]
            if elapsed < crawl_delay:
                time.sleep(crawl_delay - elapsed)
            self.last_request[domain] = time.time()
        
        return None  # Continue processing
```

**Generic Spider Code:**
```python
# src/uwss/crawl/scrapy_project/spiders/generic_spider.py
import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.loader import ItemLoader
from ..items import AcademicDocumentItem

class GenericSpider(scrapy.Spider):
    name = 'generic'
    
    def __init__(self, seed_urls=None, max_depth=3, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = seed_urls.split(',') if seed_urls else []
        self.max_depth = int(max_depth)
        self.link_extractor = LinkExtractor(
            allow_domains=None,  # Allow all domains from seed
            deny_extensions=['jpg', 'png', 'gif', 'css', 'js'],
            unique=True
        )
    
    def parse(self, response):
        # Extract metadata
        loader = ItemLoader(item=AcademicDocumentItem(), response=response)
        loader.add_value('source_url', response.url)
        loader.add_css('title', 'h1::text, title::text')
        loader.add_css('abstract', '.abstract::text, #abstract::text')
        loader.add_css('authors', '.author::text, .authors::text')
        
        # Try academic meta tags
        loader.add_xpath('title', '//meta[@name="citation_title"]/@content')
        loader.add_xpath('abstract', '//meta[@name="citation_abstract"]/@content')
        loader.add_xpath('authors', '//meta[@name="citation_author"]/@content')
        loader.add_xpath('doi', '//meta[@name="citation_doi"]/@content')
        
        item = loader.load_item()
        yield item
        
        # Follow links (depth control)
        if response.meta.get('depth', 0) < self.max_depth:
            for link in self.link_extractor.extract_links(response):
                yield response.follow(link, callback=self.parse)
```

**Tasks:**
1. **Scrapy Project Setup**
   - Enhance existing `src/uwss/crawl/scrapy_project/`
   - Add middleware for:
     - Robots.txt compliance (urllib.robotparser)
     - Rate limiting per domain (time.sleep + crawl-delay)
     - User-Agent rotation (random selection from pool)
     - Retry logic (Scrapy built-in + custom)
   - Add item pipeline for:
     - Metadata extraction (ItemLoader)
     - Database insertion (SQLAlchemy)
     - Deduplication (url_hash check)

2. **Generic Web Spider**
   - Create `src/uwss/crawl/scrapy_project/spiders/generic_spider.py`
   - Support seed URLs from config
   - Follow links with depth control (LinkExtractor)
   - Extract PDFs and HTML content
   - Respect robots.txt (middleware)

3. **Metadata Extraction**
   - Create `src/uwss/crawl/extractors/`:
     - `html_extractor.py`: Extract metadata from HTML (BeautifulSoup + Scrapy Selector)
     - `pdf_extractor.py`: Extract metadata from PDFs (PyPDF2/pdfplumber)
     - `pattern_matcher.py`: Pattern matching for academic content (regex)

**Deliverables:**
- ✅ Enhanced Scrapy infrastructure
- ✅ Generic web spider
- ✅ Metadata extractors
- ✅ CLI command: `crawl-web`

**Success Criteria:**
- Successfully crawl 10+ research group websites
- Extract metadata with >80% accuracy
- Respect robots.txt
- No blocking or rate limit issues

**Risks & Mitigations:**
- **Risk**: HTML structure varies widely → **Mitigation**: Multiple extraction strategies, ML-based extraction (future)
- **Risk**: Getting blocked → **Mitigation**: Rate limiting, User-Agent rotation, proxy support (optional)
- **Risk**: Low-quality content → **Mitigation**: Content scoring, filtering

**Estimated Time**: 2-3 days

---

### Sub-Phase 2.2: Research Group & Faculty Page Discovery (Week 3, Days 3-5)

**Tasks:**
1. **Seed Discovery**
   - Create `src/uwss/discovery/seed_finder.py`:
     - Extract homepage URLs from papers (OpenAlex, Crossref metadata)
     - University directory parsing (manual seed list for initial phase)
     - Conference proceedings discovery (from paper metadata)
     - **Domain scoring**: Prioritize .edu, .ac.*, .gov, .org domains
   - Generate seed URLs for research groups
   - **Note**: Do NOT crawl Google Scholar (violates ToS)

2. **Faculty Page Crawler**
   - Create specialized spider for faculty pages
   - Extract: name, affiliation, email, research interests, publications
   - Follow links to publications and PDFs

3. **Research Group Crawler**
   - Create specialized spider for lab/group pages
   - Extract: group members, projects, publications
   - Discover publication links

**Deliverables:**
- ✅ Seed discovery module
- ✅ Faculty page crawler
- ✅ Research group crawler
- ✅ CLI commands: `discover-seeds`, `crawl-faculty`, `crawl-groups`

**Success Criteria:**
- Discover 50+ seed URLs for research groups
- Successfully crawl 20+ faculty pages
- Extract researcher information with >70% accuracy
- **Domain filtering**: Prioritize academic/government domains (.edu, .ac.*, .gov, .org)
- **Demo**: Show list of discovered research groups with contact info

**Estimated Time**: 2-3 days

---

### Sub-Phase 2.3: Scattered PDF Discovery (Week 4, Days 1-2)

**Tasks:**
1. **PDF Discovery**
   - Enhance spider to detect PDF links
   - Follow PDF links from HTML pages
   - Extract metadata from PDFs (using existing PDF parser)

2. **Content Filtering**
   - Score PDFs by relevance (using existing scoring system)
   - Filter out non-academic content
   - Deduplicate PDFs (by content hash)

**Deliverables:**
- ✅ PDF discovery module
- ✅ Content filtering
- ✅ Integration with existing pipeline

**Success Criteria:**
- Discover 100+ PDFs from web crawling
- Filter to 50+ relevant PDFs (using keyword scoring + domain filtering)
- Metadata extraction accuracy >75%
- **Content scoring**: Filter out spam/blog content, prioritize academic content
- **Demo**: Show list of discovered PDFs with relevance scores

**Estimated Time**: 1-2 days

---

### Sub-Phase 2.4: Testing & Refinement (Week 4, Days 3-5)

**Tasks:**
1. **Comprehensive Testing**
   - Test with multiple domains
   - Verify compliance (robots.txt, rate limits)
   - Test error handling and recovery

2. **Performance Optimization**
   - Optimize crawling speed
   - Reduce false positives
   - Improve metadata extraction accuracy

3. **Documentation**
   - Document crawling strategies
   - Document compliance measures
   - Create runbook for web crawling

**Deliverables:**
- ✅ Test results
- ✅ Performance benchmarks
- ✅ Documentation

**Estimated Time**: 2-3 days

---

## Phase 3: Researcher & Group Finder (Weeks 5-6)

### Goal
Extract researcher information, build researcher profiles, and enable collaborator discovery.

### Sub-Phase 3.1: Researcher Information Extraction (Week 5, Days 1-3)

#### Technologies & Libraries
- **ORCID API**: `requests` (REST API client)
- **Name parsing**: `nameparser` library (parse "First Last" vs "Last, First")
- **Email extraction**: `regex` patterns + validation
- **Affiliation parsing**: Heuristic rules + regex
- **Graph database**: `networkx` (for collaboration networks)
- **Fuzzy matching**: `fuzzywuzzy` hoặc `rapidfuzz` (for name disambiguation)

#### Algorithms & Approach

**1. Author Extraction Algorithm:**
```python
# Algorithm: Extract and normalize author information
def extract_authors(text: str, metadata: Dict) -> List[Dict]:
    """
    Algorithm:
    1. Extract from multiple sources:
       - Paper metadata (authors field)
       - HTML meta tags (citation_author)
       - PDF metadata
       - Text patterns ("Author:", "By:", etc.)
    2. Parse name formats:
       - "First Last" → {given: "First", family: "Last"}
       - "Last, First" → {given: "First", family: "Last"}
       - "First Middle Last" → {given: "First Middle", family: "Last"}
    3. Extract affiliations:
       - From affiliation field
       - From email domain (infer institution)
       - From text patterns
    4. Extract emails:
       - Regex: [a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}
       - Validate format
    5. Extract ORCID:
       - Regex: 0000-000[1-9]\d{3}-\d{3}[X\d]
       - Validate checksum
    """
    # Use nameparser for name parsing
    # Use regex for email/ORCID extraction
    # Use heuristics for affiliation inference
```

**2. Researcher Deduplication Algorithm:**
```python
# Algorithm: Deduplicate researchers across sources
def deduplicate_researchers(researchers: List[Dict]) -> List[Dict]:
    """
    Algorithm:
    1. Group by exact matches:
       - Same ORCID → same person
       - Same email → same person
    2. Fuzzy matching for names:
       - Calculate similarity (Levenshtein distance)
       - If similarity > 0.9 and same affiliation → likely same person
    3. Build clusters of likely duplicates
    4. Merge profiles in each cluster
    5. Return deduplicated list
    """
    # Use fuzzywuzzy/rapidfuzz for name similarity
    # Use networkx for clustering
    # Merge profiles with priority (ORCID > email > name)
```

**3. ORCID API Integration Algorithm:**
```python
# Algorithm: Fetch researcher data from ORCID
def fetch_orcid_profile(orcid_id: str) -> Dict:
    """
    Algorithm:
    1. Call ORCID API: GET https://pub.orcid.org/v3.0/{orcid_id}
    2. Parse XML response (ORCID uses XML)
    3. Extract:
       - Name (given-names, family-name)
       - Email (emails.email[0].email)
       - Affiliations (affiliations.affiliation-group)
       - Works (activities-summary.works.group)
    4. Map to researcher profile schema
    """
    # Use requests for API calls
    # Use xml.etree.ElementTree for XML parsing
    # Handle rate limits (ORCID: 10 requests/second)
```

#### Implementation Details

**ORCID Client Code:**
```python
# src/uwss/researchers/orcid.py
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Optional

def fetch_orcid_profile(orcid_id: str) -> Optional[Dict]:
    """Fetch researcher profile from ORCID API."""
    url = f"https://pub.orcid.org/v3.0/{orcid_id}"
    headers = {
        'Accept': 'application/xml',
        'User-Agent': 'UWSS/1.0 (https://github.com/uwss)'
    }
    
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        return None
    
    root = ET.fromstring(resp.text)
    ns = {'person': 'http://www.orcid.org/ns/person',
          'common': 'http://www.orcid.org/ns/common'}
    
    # Extract name
    given_name = root.find('.//person:given-names', ns)
    family_name = root.find('.//person:family-name', ns)
    
    # Extract email
    email_elem = root.find('.//common:email[1]', ns)
    email = email_elem.get('value') if email_elem is not None else None
    
    # Extract affiliations
    affiliations = []
    for aff in root.findall('.//common:affiliation-group', ns):
        org = aff.find('.//common:organization', ns)
        if org is not None:
            affiliations.append(org.find('common:name', ns).text)
    
    return {
        'orcid_id': orcid_id,
        'given_name': given_name.text if given_name is not None else None,
        'family_name': family_name.text if family_name is not None else None,
        'email': email,
        'affiliations': affiliations
    }
```

**Tasks:**
1. **Author Extraction Enhancement**
   - Enhance existing author extraction
   - Parse author affiliations (regex + heuristics)
   - Extract author emails (regex patterns: `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`)
   - Extract ORCID IDs (regex: `0000-000[1-9]\d{3}-\d{3}[X\d]`)
   - Use `nameparser` library for name parsing

2. **Researcher Profile Builder**
   - Create `src/uwss/researchers/` module:
     - `profile_builder.py`: Build researcher profiles from multiple sources
     - `deduplication.py`: Deduplicate researchers (fuzzy matching with `fuzzywuzzy`)
     - `enrichment.py`: Enrich profiles with additional data

3. **ORCID Integration**
   - Create `src/uwss/researchers/orcid.py`:
     - ORCID API client (REST API, XML response)
     - Fetch researcher data from ORCID
     - Link papers to ORCID profiles

**Deliverables:**
- ✅ Enhanced author extraction
- ✅ Researcher profile builder
- ✅ ORCID integration
- ✅ CLI command: `build-researcher-profiles`

**Success Criteria:**
- Extract researcher info from 100+ papers
- Build 50+ researcher profiles
- ORCID integration works for 20+ researchers
- **Simplified V1**: List researchers + affiliations + homepage/email (if available)
- **Group by topic**: "Top researchers/groups" by keyword
- **Demo**: Show list of researchers with contact info and affiliations

**Risks & Mitigations:**
- **Risk**: Contact info not always available → **Mitigation**: Multiple sources, heuristics
- **Risk**: Name disambiguation → **Mitigation**: Use ORCID, email, affiliation matching

**Estimated Time**: 2-3 days

---

### Sub-Phase 3.2: Group & Institution Tracking (Week 5, Days 4-5)

**Tasks:**
1. **Institution Extraction**
   - Extract institutions from affiliations
   - Normalize institution names
   - Build institution database

2. **Research Group Discovery**
   - Identify research groups from crawled pages
   - Extract group members
   - Link researchers to groups
   - **Simplified V1**: Basic grouping by affiliation + topic keywords
   - **Future work**: Co-author network analysis (networkx) - nice-to-have

**Deliverables:**
- ✅ Institution database
- ✅ Research group tracker
- ✅ CLI commands: `track-institutions`, `track-groups`

**Estimated Time**: 1-2 days

---

### Sub-Phase 3.3: Collaborator Discovery & Trends (Week 6, Days 1-3)

**Tasks:**
1. **Researcher Listing & Grouping**
   - List researchers by topic/keyword
   - Group by affiliation/institution
   - Extract contact info (email, homepage) if publicly available
   - **Simplified V1**: Basic listing and grouping (no complex network analysis)

2. **Future Work (Nice-to-have)**
   - Co-author network analysis (networkx)
   - Research trends tracking
   - Collaboration pattern identification
   - **Note**: These are future enhancements, not required for initial demo

**Deliverables:**
- ✅ Researcher listing by topic
- ✅ Group by affiliation/institution
- ✅ Contact info extraction
- ✅ CLI commands: `list-researchers`, `list-groups`
- ⏸️ Future: Collaboration network, trend tracker (nice-to-have)

**Estimated Time**: 2-3 days

---

### Sub-Phase 3.4: Testing & Documentation (Week 6, Days 4-5)

**Tasks:**
1. **Testing**
   - Test researcher extraction accuracy
   - Test collaborator discovery
   - Test trend tracking

2. **Documentation**
   - Document researcher finder features
   - Create usage examples
   - Document API

**Estimated Time**: 1-2 days

---

## Phase 4: Subscription Databases (Weeks 7-8)

### Goal
Integrate subscription databases (Web of Science, Scopus, ScienceDirect) when institutional access is available.

### Prerequisites
- Institutional subscription verified
- API keys obtained
- Terms of Service reviewed

### Sub-Phase 4.1: API Research & Documentation (Week 7, Days 1-2)

**Tasks:**
1. **API Research**
   - Research Web of Science API
   - Research Scopus API
   - Research ScienceDirect API
   - Document requirements and limitations

2. **Access Verification**
   - Verify institutional access
   - Obtain API keys
   - Test API access

**Deliverables:**
- ✅ API documentation
- ✅ Access verification report
- ✅ API keys (secured)

**Estimated Time**: 1-2 days (depends on access)

---

### Sub-Phase 4.2: Adapter Implementation (Week 7, Days 3-5)

**Tasks:**
1. **Web of Science Adapter**
   - Create `src/uwss/sources/wos/adapter.py`
   - Implement REST API client
   - Map to Document schema
   - Add CLI command: `wos-discover`

2. **Scopus Adapter**
   - Create `src/uwss/sources/scopus/adapter.py`
   - Implement REST API client
   - Map to Document schema
   - Add CLI command: `scopus-discover`

3. **ScienceDirect Adapter**
   - Create `src/uwss/sources/sciencedirect/adapter.py`
   - Implement REST API client
   - Map to Document schema
   - Add CLI command: `sciencedirect-discover`

**Deliverables:**
- ✅ Web of Science adapter
- ✅ Scopus adapter
- ✅ ScienceDirect adapter
- ✅ CLI commands

**Estimated Time**: 2-3 days

---

### Sub-Phase 4.3: Testing & Compliance (Week 8, Days 1-3)

**Tasks:**
1. **Compliance Verification**
   - Verify ToS compliance
   - Test rate limits
   - Verify usage quotas

2. **Testing**
   - Test with small batches
   - Verify metadata extraction
   - Test end-to-end pipeline

**Deliverables:**
- ✅ Compliance report
- ✅ Test results
- ✅ Documentation

**Estimated Time**: 2-3 days

---

## Phase 5: Cloud Deployment & Documentation (Week 9)

### Goal
Prepare system for cloud deployment and create comprehensive documentation.

### Sub-Phase 5.1: Cloud Infrastructure (Week 9, Days 1-2)

**Note**: This phase focuses on "deployment-ready design" rather than full production deployment. For research/RA context, focus on results and pipeline rather than over-engineering infrastructure.

**Tasks:**
1. **Basic Deployment Setup**
   - Create deployment scripts (optional, for future use)
   - Document deployment requirements
   - Set up basic cloud storage (S3) for PDFs if needed
   - **Simplified**: Focus on local/development setup first

2. **Configuration Management**
   - Environment variables
   - Secrets management (for API keys)
   - Configuration files

**Deliverables:**
- ✅ Deployment-ready design documentation
- ✅ Basic deployment scripts (optional)
- ✅ Configuration management setup
- ✅ Deployment guide (for future use)

**Estimated Time**: 1-2 days

---

### Sub-Phase 5.2: Documentation & User Guide (Week 9, Days 3-5)

**Tasks:**
1. **User Documentation**
   - Complete README
   - User guide
   - API documentation
   - Configuration guide

2. **Developer Documentation**
   - Architecture documentation
   - Contributing guide
   - Code examples
   - Testing guide

**Deliverables:**
- ✅ Complete documentation
- ✅ User guide
- ✅ Developer guide

**Estimated Time**: 2-3 days

---

## Technology Stack Summary

### Core Technologies
- **Language**: Python 3.8+
- **Database**: SQLite (local) / PostgreSQL (production)
- **ORM**: SQLAlchemy
- **HTTP Client**: `requests` (with retry/backoff)
- **CLI Framework**: `argparse` (built-in)

### Phase 1: Multi-Source Database Integration
- **Sitemap parsing**: `xml.etree.ElementTree` (built-in)
- **HTML parsing**: `BeautifulSoup4` (bs4)
- **Robots.txt**: `urllib.robotparser` (built-in)
- **REST APIs**: `requests` (JSON parsing)
- **OAI-PMH**: Custom parser (XML, `xml.etree.ElementTree`)

### Phase 2: Web Crawling
- **Crawling framework**: `Scrapy`
- **HTML parsing**: `BeautifulSoup4` + Scrapy Selectors
- **PDF parsing**: `PyPDF2` hoặc `pdfplumber`
- **Pattern matching**: `regex` (built-in)

### Phase 3: Researcher Finder
- **ORCID API**: `requests` (REST API, XML)
- **Name parsing**: `nameparser`
- **Fuzzy matching**: `fuzzywuzzy` hoặc `rapidfuzz`
- **Graph networks**: `networkx`

### Phase 4: Subscription Databases
- **REST APIs**: `requests` (same as Phase 1)
- **Authentication**: OAuth2, API keys

### Phase 5: Cloud Deployment
- **Cloud**: AWS (EC2, RDS, S3)
- **Containerization**: Docker
- **Infrastructure as Code**: Terraform (optional)

---

## Algorithm Summary

### 1. Sitemap Parsing
- **Input**: Sitemap URL
- **Process**: Parse XML → Extract URLs → Handle nested sitemaps recursively
- **Output**: Iterator of URLs
- **Complexity**: O(n) where n = number of URLs

### 2. HTML Metadata Extraction
- **Input**: HTML content
- **Process**: Multi-strategy extraction (meta tags → CSS selectors → heuristics)
- **Output**: Structured metadata dict
- **Complexity**: O(n) where n = HTML size

### 3. Rate Limiting
- **Input**: Domain, crawl-delay
- **Process**: Track last request time → Calculate delay → Sleep if needed
- **Output**: None (side effect: throttling)
- **Complexity**: O(1) per request

### 4. Researcher Deduplication
- **Input**: List of researcher profiles
- **Process**: Exact matching (ORCID/email) → Fuzzy matching (names) → Clustering → Merging
- **Output**: Deduplicated list
- **Complexity**: O(n²) for fuzzy matching (can optimize with indexing)

---

## Summary Timeline

| Phase | Duration | Priority | Status |
|-------|----------|----------|--------|
| **Phase 0: Foundation** | - | HIGH | ✅ Complete |
| **Phase 1: Multi-Source DB** | 2 weeks | HIGH | 🚧 Next |
| **Phase 2: Web Crawling** | 2 weeks | HIGH | 📋 Planned |
| **Phase 3: Researcher Finder** | 2 weeks | MEDIUM | 📋 Planned |
| **Phase 4: Subscription DB** | 2 weeks | LOW* | 📋 Planned* |
| **Phase 5: Cloud & Docs** | 1 week | MEDIUM | 📋 Planned |

*Requires institutional access

**Total**: 9 weeks (~2 months)

---

## Risk Management

### High-Risk Items
1. **Web Crawling Complexity** (Phase 2)
   - Mitigation: Start with simple cases, iterate
   - Fallback: Manual seed URLs if auto-discovery fails

2. **Subscription Database Access** (Phase 4)
   - Mitigation: Research APIs early, request access early
   - Fallback: Skip if access not available

### Medium-Risk Items
1. **HTML Structure Changes**
   - Mitigation: Multiple selectors, robust parsing
   - Fallback: Manual extraction rules

2. **Rate Limiting Issues**
   - Mitigation: Configurable throttling, respect robots.txt
   - Fallback: Reduce crawl speed

---

## Success Metrics

### Phase 1 Success
- ✅ 5+ sources integrated (arXiv, TRB/TRID, Crossref, OpenAlex, CORE/DOAJ)
- ✅ 1000+ records harvested across all sources
- ✅ Metadata extraction accuracy >90%

### Phase 2 Success
- ✅ 50+ research group websites crawled
- ✅ 100+ faculty pages crawled
- ✅ 200+ scattered PDFs discovered
- ✅ Compliance with robots.txt 100%
- ✅ Domain filtering working (.edu, .ac.*, .gov, .org prioritized)

### Phase 3 Success
- ✅ 200+ researcher profiles built
- ✅ ORCID integration working
- ✅ Collaborator discovery functional
- ✅ Researcher listing and grouping functional
- ✅ Contact info extraction working (where publicly available)
- ⏸️ Future: Co-author network, trend analysis (nice-to-have)

---

## Next Steps

**Immediate (This Week):**
1. Start Phase 1.1: TRB/TRID sitemap crawling
2. Test with small batch first, then scale up
3. Iterate based on results
4. **Demo after each phase**: Show tangible results (list of papers, researchers, etc.)

**This approach ensures:**
- ✅ Incremental progress
- ✅ Early validation
- ✅ Risk mitigation
- ✅ Realistic timelines
- ✅ **Tangible demos** for professor review
- ✅ Quality over quantity
- ✅ Compliance with ToS (no Google Scholar, etc.)

