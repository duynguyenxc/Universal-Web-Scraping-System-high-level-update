# Pipeline Architecture: arXiv vs TRB

## 🎯 Câu trả lời ngắn gọn

**Pipeline VẪN GIỐNG NHAU** - chỉ khác ở bước **DISCOVER** (adapter).

- **arXiv**: OAI-PMH adapter → gọi API, parse XML
- **TRB**: Sitemap crawler/spider → parse sitemap, crawl HTML pages
- **Sau discover**: Tất cả đều đi qua cùng pipeline (score → export → fetch → extract)

## 📊 Sơ đồ Pipeline Universal

```
┌─────────────────────────────────────────────────────────────────┐
│                    UNIVERSAL PIPELINE                            │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐
│   DISCOVER   │  ← CHỈ BƯỚC NÀY KHÁC NHAU
└──────────────┘
      │
      ├─ arXiv: OAI-PMH adapter
      │   └─> Gọi https://export.arxiv.org/oai2?verb=ListRecords
      │   └─> Parse XML metadata
      │   └─> Insert Document vào DB
      │
      ├─ TRB: Sitemap crawler
      │   └─> Parse sitemap.xml
      │   └─> Crawl HTML pages (Scrapy spider)
      │   └─> Extract metadata từ HTML
      │   └─> Insert Document vào DB
      │
      └─ Web of Science: API adapter (nếu có subscription)
          └─> Gọi REST API với API key
          └─> Parse JSON response
          └─> Insert Document vào DB

      ▼
┌──────────────┐
│    SCORE     │  ← GIỐNG NHAU (keyword scoring)
└──────────────┘
      │
      ▼
┌──────────────┐
│    EXPORT    │  ← GIỐNG NHAU (filter, export JSONL)
└──────────────┘
      │
      ▼
┌──────────────┐
│    FETCH     │  ← GIỐNG NHAU (download PDFs)
└──────────────┘
      │
      ▼
┌──────────────┐
│   EXTRACT    │  ← GIỐNG NHAU (GROBID, full-text)
└──────────────┘
```

## 🔍 Chi tiết từng bước

### 1. DISCOVER (Adapter Pattern)

**arXiv - OAI-PMH Adapter:**
```python
# src/uwss/arxiv/harvest_oai.py
def harvest_arxiv_oai(...):
    # Gọi OAI-PMH API
    url = "https://export.arxiv.org/oai2?verb=ListRecords&metadataPrefix=oai_dc"
    response = requests.get(url)
    xml = parse_xml(response.text)
    
    # Parse metadata
    for record in xml.find_all('record'):
        doc = Document(
            title=record.find('title').text,
            abstract=record.find('description').text,
            # ...
        )
        # Insert vào DB
        session.merge(doc)
```

**TRB - Sitemap Crawler:**
```python
# src/uwss/discovery/sitemap.py (hoặc Scrapy spider)
def discover_trb_sitemap(...):
    # Parse sitemap.xml
    sitemap_url = "https://trid.trb.org/sitemap.xml"
    sitemap = parse_sitemap(sitemap_url)
    
    # Crawl từng URL
    for url in sitemap.urls:
        html = requests.get(url).text
        doc = extract_metadata_from_html(html)  # Parse HTML
        # Insert vào DB
        session.merge(doc)
```

**Kết quả:** Cả hai đều insert `Document` objects vào **cùng một DB schema**.

### 2. SCORE (Giống nhau)

```python
# src/uwss/score/__init__.py
def score_documents(session, config):
    # Query TẤT CẢ documents (không phân biệt source)
    docs = session.query(Document).all()
    
    for doc in docs:
        # Score bằng keywords (giống nhau cho mọi source)
        score = calculate_relevance_score(
            doc.title, 
            doc.abstract, 
            positive_keywords,
            negative_keywords
        )
        doc.relevance_score = score
```

### 3. EXPORT (Giống nhau)

```python
# src/uwss/cli.py - export command
def cmd_export(args):
    # Query TẤT CẢ documents (không phân biệt source)
    query = session.query(Document)
    if args.require_match:
        query = query.filter(Document.relevance_score > 0)
    
    # Export JSONL (giống nhau cho mọi source)
    for doc in query:
        write_jsonl(doc)
```

### 4. FETCH (Giống nhau)

```python
# src/uwss/fetch/arxiv_pdf.py (hoặc generic fetcher)
def fetch_pdfs(session, ids):
    for doc_id in ids:
        doc = session.query(Document).get(doc_id)
        
        # Download PDF (logic giống nhau)
        pdf_url = doc.pdf_url or doc.landing_url
        download_pdf(pdf_url, output_path)
        
        # Update DB (giống nhau)
        doc.local_path = output_path
        doc.pdf_status = 'downloaded'
```

## 🏗️ Kiến trúc Universal

### Adapter Pattern

```python
# src/uwss/sources/
├── arxiv/
│   ├── harvest_oai.py      # OAI-PMH adapter
│   └── fetch_pdf.py         # arXiv-specific PDF fetcher
│
├── trb/
│   ├── discover_sitemap.py  # Sitemap crawler adapter
│   └── parse_html.py        # HTML parser
│
└── generic/
    ├── oai_adapter.py       # Generic OAI-PMH (cho bất kỳ source nào)
    ├── rss_adapter.py       # Generic RSS/Atom
    └── sitemap_adapter.py   # Generic sitemap crawler
```

### Database Schema (Chung cho tất cả)

```python
# src/uwss/store/models.py
class Document(Base):
    # Identification
    id = Column(Integer, primary_key=True)
    title = Column(String(500))
    abstract = Column(Text)
    authors = Column(Text)
    doi = Column(String(255))
    
    # Source tracking
    source = Column(String(50))  # 'arxiv', 'trb', 'wos', ...
    source_url = Column(String(1000))
    
    # Scoring
    relevance_score = Column(Float)
    
    # Files
    pdf_url = Column(String(1000))
    local_path = Column(String(1000))
    pdf_status = Column(String(50))
    
    # ... (tất cả sources dùng cùng schema)
```

## ✅ Kết luận

1. **Pipeline VẪN GIỐNG NHAU**: discover → score → export → fetch → extract
2. **Chỉ khác ở DISCOVER**: mỗi source có adapter riêng
   - arXiv: OAI-PMH adapter
   - TRB: Sitemap crawler/spider
   - Web of Science: REST API adapter (nếu có subscription)
3. **Sau discover**: Tất cả documents vào cùng DB schema → cùng pipeline
4. **Kiến trúc universal**: Thêm source mới = thêm adapter mới, không cần sửa pipeline

## 🎯 Ví dụ thực tế

**arXiv:**
```bash
# Discover (OAI-PMH)
python -m src.uwss.cli arxiv-harvest-oai --max 100

# Score (chung)
python -m src.uwss.cli score-keywords --config config.yaml

# Export (chung)
python -m src.uwss.cli export --require-match

# Fetch (chung)
python -m src.uwss.cli arxiv-fetch-pdf --ids-file ids.txt
```

**TRB:**
```bash
# Discover (Sitemap crawler)
python -m src.uwss.cli trb-discover-sitemap --max 100

# Score (chung) - GIỐNG NHAU
python -m src.uwss.cli score-keywords --config config.yaml

# Export (chung) - GIỐNG NHAU
python -m src.uwss.cli export --require-match

# Fetch (chung) - GIỐNG NHAU
python -m src.uwss.cli fetch-pdfs --ids-file ids.txt
```

**→ Sau bước discover, pipeline hoàn toàn giống nhau!**

