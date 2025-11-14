# Paperscraper Integration Design

## Mục tiêu

Tích hợp `paperscraper` library vào UWSS như một source adapter, giữ nguyên tính universal của hệ thống để có thể mở rộng thêm các database khác trong tương lai.

## Phân tích Paperscraper

### Các nguồn Paperscraper hỗ trợ:
- **PubMed**: `paperscraper.pubmed`
- **arXiv**: `paperscraper.arxiv`
- **medRxiv**: `paperscraper.medrxiv`
- **bioRxiv**: `paperscraper.biorxiv`
- **chemRxiv**: `paperscraper.chemrxiv`

### Điểm mạnh của Paperscraper:
1. **Query filtering tốt**: Dữ liệu thu về rất liên quan đến keywords
2. **Đã được test kỹ**: Library đã được sử dụng rộng rãi
3. **Hỗ trợ nhiều sources**: 5 sources chính
4. **PDF download**: Có sẵn PDF fetching capabilities

### Kiến trúc Paperscraper:
- Module-based: Mỗi source có module riêng
- Query functions: `get_papers()`, `get_papers_from_query()`
- Output format: JSON/JSONL với metadata đầy đủ

## Thiết kế Tích hợp

### 1. Adapter Pattern

Tạo adapter wrapper cho paperscraper theo pattern hiện tại của UWSS:

```
src/uwss/sources/paperscraper/
├── __init__.py          # Public API
├── adapter.py           # Main adapter với discover functions
├── mappers.py           # Map paperscraper output → Document schema
└── query_builders.py    # Build queries từ keywords/config
```

### 2. Interface Design

Mỗi source trong paperscraper sẽ có một discover function riêng:

```python
def discover_paperscraper_pubmed(
    keywords: list[str],
    max_records: Optional[int] = None,
    year_filter: Optional[int] = None,
    **kwargs
) -> Iterator[dict]:
    """Discover PubMed papers via paperscraper."""
    pass

def discover_paperscraper_arxiv(
    keywords: list[str],
    max_records: Optional[int] = None,
    year_filter: Optional[int] = None,
    **kwargs
) -> Iterator[dict]:
    """Discover arXiv papers via paperscraper."""
    pass

# ... tương tự cho medrxiv, biorxiv, chemrxiv
```

### 3. Mapping Strategy

Paperscraper output format → UWSS Document schema:

- `title` → `title`
- `abstract` → `abstract`
- `authors` → `authors` (JSON string)
- `doi` → `doi`
- `year` → `year`
- `url` → `source_url` / `landing_url`
- `pdf_url` → `pdf_url`
- `journal` → `venue`
- Source identifier → `source` (e.g., "paperscraper_pubmed")

### 4. CLI Commands

Tạo commands cho từng source:

- `paperscraper-pubmed-discover`
- `paperscraper-arxiv-discover`
- `paperscraper-medrxiv-discover`
- `paperscraper-biorxiv-discover`
- `paperscraper-chemrxiv-discover`

Hoặc một command chung với `--source` parameter:

- `paperscraper-discover --source pubmed|arxiv|medrxiv|biorxiv|chemrxiv`

### 5. Dependencies

Thêm vào `requirements.txt`:
```
paperscraper>=0.3.0
```

### 6. Error Handling

- Handle paperscraper import errors gracefully
- Fallback nếu paperscraper không available
- Log warnings nếu có issues

### 7. Testing Strategy

- Unit tests cho mappers
- Integration tests với paperscraper mocks
- End-to-end tests với real queries (small batches)

## Implementation Plan

### Phase 1: Core Adapter (Priority: HIGH)
1. ✅ Research paperscraper API
2. ⏳ Create adapter structure
3. ⏳ Implement mappers
4. ⏳ Implement query builders
5. ⏳ Add to requirements.txt

### Phase 2: CLI Integration (Priority: HIGH)
1. ⏳ Create CLI commands
2. ⏳ Test với real queries
3. ⏳ Validate output quality

### Phase 3: Documentation (Priority: MEDIUM)
1. ⏳ Update README
2. ⏳ Add usage examples
3. ⏳ Document configuration

### Phase 4: Testing & Refinement (Priority: MEDIUM)
1. ⏳ Unit tests
2. ⏳ Integration tests
3. ⏳ Performance testing

## Notes

- Giữ nguyên tính universal: Paperscraper chỉ là một adapter, không thay đổi pipeline chính
- Có thể dùng paperscraper song song với adapters hiện tại (ví dụ: có thể dùng cả `arxiv-harvest-oai` và `paperscraper-arxiv-discover`)
- Paperscraper sẽ được map vào cùng Document schema, đi qua cùng pipeline (score → export → fetch → extract)


