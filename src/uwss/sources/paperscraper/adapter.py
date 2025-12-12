"""Paperscraper adapter: Main discovery functions for each source.

This module provides discover functions for each paperscraper-supported source:
- PubMed
- arXiv
- medRxiv
- bioRxiv
- chemRxiv

Each function:
1. Uses paperscraper's query functions
2. Maps output to UWSS Document schema
3. Handles errors gracefully
4. Supports filtering and pagination
"""

from __future__ import annotations

import logging
import time
from typing import Iterator, Optional

from .mappers import map_paperscraper_to_document
from .query_builders import build_paperscraper_query

logger = logging.getLogger(__name__)

# Try to import paperscraper, but handle gracefully if not available
try:
    # Paperscraper functions that return DataFrames
    from paperscraper.pubmed import get_pubmed_papers
    from paperscraper.arxiv import get_arxiv_papers_api

    PAPERSCRAPER_AVAILABLE = True
except ImportError:
    PAPERSCRAPER_AVAILABLE = False
    get_pubmed_papers = None
    get_arxiv_papers_api = None
    logger.warning(
        "paperscraper library not available. Install with: pip install paperscraper"
    )


def discover_paperscraper_pubmed(
    keywords: list[str],
    max_records: Optional[int] = None,
    year_filter: Optional[int] = None,
    **kwargs,
) -> Iterator[dict]:
    """Discover PubMed papers via paperscraper.

    Args:
        keywords: List of keywords to search for
        max_records: Maximum number of records to discover
        year_filter: Optional year filter (e.g., 2020)
        **kwargs: Additional arguments passed to paperscraper

    Yields:
        Dictionary with fields matching Document model

    Raises:
        ImportError: If paperscraper is not installed
    """
    if not PAPERSCRAPER_AVAILABLE:
        raise ImportError(
            "paperscraper library is required. Install with: pip install paperscraper"
        )

    logger.info(f"Starting PubMed discovery via paperscraper with {len(keywords)} keywords")

    # Build query from keywords - convert to string for PubMed
    # PubMed expects a string query, not list of lists
    query_str = " OR ".join([f"({kw})" for kw in keywords])

    try:
        # Use paperscraper's get_pubmed_papers which returns a DataFrame
        df = get_pubmed_papers(
            query=query_str,
            max_results=max_records or 1000,
            fields=['title', 'authors', 'date', 'abstract', 'journal', 'doi', 'url', 'pdf_url']
        )

        # Convert DataFrame to list of dictionaries
        papers = df.to_dict('records') if not df.empty else []

        count = 0
        for paper in papers:
            if max_records is not None and count >= max_records:
                break

            # Apply year filter if specified (paperscraper doesn't support it directly)
            if year_filter and paper.get("year"):
                try:
                    paper_year = int(paper.get("year"))
                    if paper_year < year_filter:
                        continue
                except (ValueError, TypeError):
                    pass

            # Map paperscraper output to Document schema
            mapped = map_paperscraper_to_document(paper, source="paperscraper_pubmed")
            if mapped:
                yield mapped
                count += 1

        logger.info(f"PubMed discovery complete: {count} records")

    except Exception as e:
        logger.error(f"Error during PubMed discovery: {e}")
        raise


def discover_paperscraper_arxiv(
    keywords: list[str],
    max_records: Optional[int] = None,
    year_filter: Optional[int] = None,
    batch_size: int = 5,
    max_retries: int = 3,
    retry_delay: float = 2.0,
    **kwargs,
) -> Iterator[dict]:
    """Discover arXiv papers via paperscraper.

    Args:
        keywords: List of keywords to search for
        max_records: Maximum number of records to discover
        year_filter: Optional year filter (e.g., 2020)
        batch_size: Number of keywords per query batch (default: 5)
        max_retries: Maximum retry attempts per batch (default: 3)
        retry_delay: Delay between retries in seconds (default: 2.0)
        **kwargs: Additional arguments passed to paperscraper

    Yields:
        Dictionary with fields matching Document model

    Raises:
        ImportError: If paperscraper is not installed

    Notes:
        - arXiv API has query length limits, so keywords are split into batches
        - Each batch is queried separately and results are merged
        - Retry logic handles temporary API failures
    """
    if not PAPERSCRAPER_AVAILABLE:
        raise ImportError(
            "paperscraper library is required. Install with: pip install paperscraper"
        )

    logger.info(
        f"Starting arXiv discovery via paperscraper with {len(keywords)} keywords "
        f"(batch_size={batch_size})"
    )

    # Split keywords into batches to avoid query length limits
    batches = []
    for i in range(0, len(keywords), batch_size):
        batch = keywords[i : i + batch_size]
        batches.append(batch)
    
    logger.info(f"Split {len(keywords)} keywords into {len(batches)} batches")

    total_count = 0
    seen_ids = set()  # Track seen papers to avoid duplicates across batches

    for batch_idx, batch_keywords in enumerate(batches, 1):
        logger.info(
            f"Processing batch {batch_idx}/{len(batches)} with {len(batch_keywords)} keywords"
        )

        # Build query string for this batch
        query_str = " OR ".join([f"({kw})" for kw in batch_keywords])

        # Retry logic for this batch
        batch_papers = []
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                # Use paperscraper's get_arxiv_papers_api which returns a DataFrame
                df = get_arxiv_papers_api(
                    query=query_str,
                    max_results=max_records or 1000,
                    fields=['title', 'authors', 'date', 'abstract', 'journal', 'doi', 'url', 'pdf_url']
                )

                # Convert DataFrame to list of dictionaries
                batch_papers = df.to_dict('records') if not df.empty else []
                last_error = None
                break  # Success, exit retry loop

            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    logger.warning(
                        f"Batch {batch_idx} attempt {attempt} failed: {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Batch {batch_idx} failed after {max_retries} attempts: {e}"
                    )
                    # Continue with next batch instead of raising
                    logger.info(f"Skipping batch {batch_idx} and continuing with next batch")

        # Process papers from this batch
        for paper in batch_papers:
            if max_records is not None and total_count >= max_records:
                logger.info(f"Reached max_records limit ({max_records})")
                return

            # Deduplication: Use URL or DOI as unique identifier
            paper_id = paper.get("url") or paper.get("doi") or paper.get("title", "")
            if paper_id in seen_ids:
                continue
            seen_ids.add(paper_id)

            # Apply year filter if specified
            if year_filter and paper.get("year"):
                try:
                    paper_year = int(paper.get("year"))
                    if paper_year < year_filter:
                        continue
                except (ValueError, TypeError):
                    pass

            # Map paperscraper output to Document schema
            mapped = map_paperscraper_to_document(paper, source="paperscraper_arxiv")
            if mapped:
                yield mapped
                total_count += 1

        # Small delay between batches to be polite to arXiv API
        if batch_idx < len(batches):
            time.sleep(1.0)

    logger.info(f"arXiv discovery complete: {total_count} records from {len(batches)} batches")


def discover_paperscraper_medrxiv(
    keywords: list[str],
    max_records: Optional[int] = None,
    year_filter: Optional[int] = None,
    **kwargs,
) -> Iterator[dict]:
    """Discover medRxiv papers via paperscraper.

    Args:
        keywords: List of keywords to search for
        max_records: Maximum number of records to discover
        year_filter: Optional year filter (e.g., 2020)
        **kwargs: Additional arguments passed to paperscraper

    Yields:
        Dictionary with fields matching Document model

    Raises:
        ImportError: If paperscraper is not installed
    """
    if not PAPERSCRAPER_AVAILABLE:
        raise ImportError(
            "paperscraper library is required. Install with: pip install paperscraper"
        )

    logger.info(f"Starting medRxiv discovery via paperscraper with {len(keywords)} keywords")

    # Build query from keywords
    query = build_paperscraper_query(keywords, year_filter)

    try:
        # Use paperscraper's QUERY_FN_DICT for querying
        query_fn = QUERY_FN_DICT.get("medrxiv")
        if not query_fn:
            raise ValueError("paperscraper does not support 'medrxiv' source")

        papers = query_fn(query, limit=max_records or 1000)

        count = 0
        for paper in papers:
            if max_records is not None and count >= max_records:
                break

            # Apply year filter if specified
            if year_filter and paper.get("year"):
                try:
                    paper_year = int(paper.get("year"))
                    if paper_year < year_filter:
                        continue
                except (ValueError, TypeError):
                    pass

            # Map paperscraper output to Document schema
            mapped = map_paperscraper_to_document(paper, source="paperscraper_medrxiv")
            if mapped:
                yield mapped
                count += 1

        logger.info(f"medRxiv discovery complete: {count} records")

    except Exception as e:
        logger.error(f"Error during medRxiv discovery: {e}")
        raise


def discover_paperscraper_biorxiv(
    keywords: list[str],
    max_records: Optional[int] = None,
    year_filter: Optional[int] = None,
    **kwargs,
) -> Iterator[dict]:
    """Discover bioRxiv papers via paperscraper.

    Args:
        keywords: List of keywords to search for
        max_records: Maximum number of records to discover
        year_filter: Optional year filter (e.g., 2020)
        **kwargs: Additional arguments passed to paperscraper

    Yields:
        Dictionary with fields matching Document model

    Raises:
        ImportError: If paperscraper is not installed
    """
    if not PAPERSCRAPER_AVAILABLE:
        raise ImportError(
            "paperscraper library is required. Install with: pip install paperscraper"
        )

    logger.info(f"Starting bioRxiv discovery via paperscraper with {len(keywords)} keywords")

    # Build query from keywords
    query = build_paperscraper_query(keywords, year_filter)

    try:
        # Use paperscraper's QUERY_FN_DICT for querying
        query_fn = QUERY_FN_DICT.get("biorxiv")
        if not query_fn:
            raise ValueError("paperscraper does not support 'biorxiv' source")

        papers = query_fn(query, limit=max_records or 1000)

        count = 0
        for paper in papers:
            if max_records is not None and count >= max_records:
                break

            # Apply year filter if specified
            if year_filter and paper.get("year"):
                try:
                    paper_year = int(paper.get("year"))
                    if paper_year < year_filter:
                        continue
                except (ValueError, TypeError):
                    pass

            # Map paperscraper output to Document schema
            mapped = map_paperscraper_to_document(paper, source="paperscraper_biorxiv")
            if mapped:
                yield mapped
                count += 1

        logger.info(f"bioRxiv discovery complete: {count} records")

    except Exception as e:
        logger.error(f"Error during bioRxiv discovery: {e}")
        raise


def discover_paperscraper_chemrxiv(
    keywords: list[str],
    max_records: Optional[int] = None,
    year_filter: Optional[int] = None,
    **kwargs,
) -> Iterator[dict]:
    """Discover chemRxiv papers via paperscraper.

    Args:
        keywords: List of keywords to search for
        max_records: Maximum number of records to discover
        year_filter: Optional year filter (e.g., 2020)
        **kwargs: Additional arguments passed to paperscraper

    Yields:
        Dictionary with fields matching Document model

    Raises:
        ImportError: If paperscraper is not installed
    """
    if not PAPERSCRAPER_AVAILABLE:
        raise ImportError(
            "paperscraper library is required. Install with: pip install paperscraper"
        )

    logger.info(f"Starting chemRxiv discovery via paperscraper with {len(keywords)} keywords")

    # Build query from keywords
    query = build_paperscraper_query(keywords, year_filter)

    try:
        # Use paperscraper's QUERY_FN_DICT for querying
        query_fn = QUERY_FN_DICT.get("chemrxiv")
        if not query_fn:
            raise ValueError("paperscraper does not support 'chemrxiv' source")

        papers = query_fn(query, limit=max_records or 1000)

        count = 0
        for paper in papers:
            if max_records is not None and count >= max_records:
                break

            # Apply year filter if specified
            if year_filter and paper.get("year"):
                try:
                    paper_year = int(paper.get("year"))
                    if paper_year < year_filter:
                        continue
                except (ValueError, TypeError):
                    pass

            # Map paperscraper output to Document schema
            mapped = map_paperscraper_to_document(paper, source="paperscraper_chemrxiv")
            if mapped:
                yield mapped
                count += 1

        logger.info(f"chemRxiv discovery complete: {count} records")

    except Exception as e:
        logger.error(f"Error during chemRxiv discovery: {e}")
        raise

