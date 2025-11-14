# Paperscraper Integration - Quick Reference

## Overview

UWSS đã tích hợp `paperscraper` library như một source adapter, cho phép sử dụng paperscraper's excellent query và filtering capabilities cho:
- **PubMed**
- **arXiv** 
- **medRxiv**
- **bioRxiv**
- **chemRxiv**

## Installation

```bash
pip install paperscraper>=0.3.0
```

## Usage

### Basic Discovery

```bash
# Discover from PubMed
python -m src.uwss.cli paperscraper-discover \
  --source pubmed \
  --config config/config.yaml \
  --max 100

# Discover from arXiv
python -m src.uwss.cli paperscraper-discover \
  --source arxiv \
  --config config/config.yaml \
  --max 100 \
  --year 2020
```

### Full Pipeline

Sau discovery, sử dụng pipeline universal như bình thường:

```bash
# 1. Discover
python -m src.uwss.cli paperscraper-discover \
  --source pubmed \
  --config config/config.yaml \
  --max 200

# 2. Score (same as always)
python -m src.uwss.cli score-keywords \
  --config config/config.yaml \
  --db data/uwss.sqlite

# 3. Export (same as always)
python -m src.uwss.cli export \
  --db data/uwss.sqlite \
  --out data/export.jsonl \
  --require-match \
  --min-score 0.2

# 4. Fetch PDFs (same as always)
python -m src.uwss.cli fetch \
  --db data/uwss.sqlite \
  --outdir data/files \
  --limit 50
```

## Advantages của Paperscraper

1. **Better Relevance**: Paperscraper có filtering tốt hơn, dữ liệu thu về rất liên quan đến keywords
2. **Tested & Proven**: Library đã được sử dụng rộng rãi và test kỹ
3. **Multiple Sources**: Hỗ trợ 5 sources chính trong một library

## Universal Architecture

Paperscraper adapter hoàn toàn tương thích với UWSS universal architecture:
- ✅ Output map vào cùng Document schema
- ✅ Đi qua cùng pipeline (score → export → fetch → extract)
- ✅ Có thể dùng song song với native adapters
- ✅ Dễ dàng mở rộng thêm sources khác

## Comparison với Native Adapters

| Feature | Native Adapters | Paperscraper Adapter |
|---------|----------------|---------------------|
| Relevance Filtering | Basic keyword matching | Advanced filtering (paperscraper's strength) |
| Sources | Individual adapters | 5 sources in one |
| Maintenance | Custom code | Leverages existing library |
| Quality | Good | Excellent (proven) |

## Notes

- Paperscraper adapter là **optional**: Nếu không cài paperscraper, command sẽ báo lỗi nhưng không ảnh hưởng đến các adapters khác
- Có thể dùng **cả hai**: Native adapter và paperscraper adapter cho cùng một source (ví dụ: `arxiv-harvest-oai` và `paperscraper-discover --source arxiv`)
- **Deduplication**: Tự động dedupe theo DOI, source_url, title

## Troubleshooting

### Import Error
```
paperscraper library not available
```
**Solution**: `pip install paperscraper>=0.3.0`

### Empty Results
- Kiểm tra keywords trong config.yaml
- Kiểm tra source có available không
- Test với query nhỏ trước (--max 10)

### Mapping Errors
- Có thể cần adjust mappers nếu paperscraper output format khác
- Check logs để xem field names thực tế


