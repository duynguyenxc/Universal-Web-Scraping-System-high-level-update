# arXiv Batch Processing Solution

## Problem
arXiv API was returning HTTP 500 errors when querying with 25 keywords in a single query. The query string was too long, exceeding arXiv's API limits.

## Solution: Batch Processing with Retry Logic

### Implementation
1. **Split keywords into batches**: Instead of querying all 25 keywords at once, split them into smaller batches (default: 5 keywords per batch)
2. **Retry logic**: Each batch has retry logic with exponential backoff (default: 3 retries)
3. **Deduplication**: Track seen papers across batches to avoid duplicates
4. **Graceful failure**: If one batch fails, continue with remaining batches instead of stopping entirely

### Key Features

#### Batch Processing
- **Configurable batch size**: Use `--batch-size` CLI argument (default: 5)
- **Automatic splitting**: Keywords are automatically split into batches
- **Progress tracking**: Logs show which batch is being processed (e.g., "Processing batch 1/5")

#### Retry Logic
- **Exponential backoff**: Wait time increases with each retry (2s, 4s, 8s)
- **Configurable retries**: `max_retries` parameter (default: 3)
- **Error handling**: Logs warnings but continues with next batch if all retries fail

#### Deduplication
- **Cross-batch deduplication**: Uses URL, DOI, or title as unique identifier
- **Prevents duplicates**: Same paper won't be yielded twice even if it appears in multiple batches

### Usage

```bash
# Default batch size (5 keywords per batch)
python -m src.uwss.cli paperscraper-discover --source arxiv --max 100 --batch-size 5

# Smaller batches for very long keyword lists
python -m src.uwss.cli paperscraper-discover --source arxiv --max 100 --batch-size 3

# Larger batches (if API allows)
python -m src.uwss.cli paperscraper-discover --source arxiv --max 100 --batch-size 8
```

### Code Changes

#### `src/uwss/sources/paperscraper/adapter.py`
- Updated `discover_paperscraper_arxiv()` function:
  - Added `batch_size`, `max_retries`, `retry_delay` parameters
  - Implemented batch splitting logic
  - Added retry loop with exponential backoff
  - Added cross-batch deduplication

#### `src/uwss/cli/commands/paperscraper_discover.py`
- Added `--batch-size` CLI argument
- Pass `batch_size` parameter to arXiv discover function

### Performance

**Before (single query with 25 keywords)**:
- ❌ HTTP 500 error
- ❌ No results

**After (5 batches of 5 keywords each)**:
- ✅ Successfully processes all batches
- ✅ 100 records discovered in ~12 seconds
- ✅ No API errors

### Recommendations

1. **Default batch size**: 5 keywords per batch works well for most cases
2. **Adjust for keyword length**: If keywords are very long, use smaller batches (3-4)
3. **Monitor API limits**: If you see rate limiting, increase delay between batches
4. **Error monitoring**: Check logs for failed batches and adjust batch size if needed

### Future Improvements

- [ ] Make batch processing configurable for other sources (PubMed, medRxiv, etc.)
- [ ] Add adaptive batch sizing based on query length
- [ ] Add metrics for batch success/failure rates
- [ ] Support parallel batch processing (with rate limiting)

