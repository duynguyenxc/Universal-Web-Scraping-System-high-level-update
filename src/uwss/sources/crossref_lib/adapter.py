"""Crossref adapter: Main discovery function using habanero library."""

from __future__ import annotations

import logging
import time
from typing import Iterator, Optional

from .mapper import map_crossref_to_document

logger = logging.getLogger(__name__)

# Try to import habanero, but handle gracefully if not available
try:
    from habanero import Crossref

    HABANERO_AVAILABLE = True
except ImportError:
    HABANERO_AVAILABLE = False
    Crossref = None
    logger.warning(
        "habanero library not available. Install with: pip install habanero"
    )


def discover_crossref(
    keywords: list[str],
    max_records: Optional[int] = None,
    year_filter: Optional[int] = None,
    contact_email: Optional[str] = None,
    throttle_sec: float = 1.0,  # Crossref recommends polite use (1 req/sec)
    **kwargs,
) -> Iterator[dict]:
    """Discover Crossref papers via habanero library.

    Args:
        keywords: List of keywords to search for
        max_records: Maximum number of records to discover
        year_filter: Optional year filter (e.g., 2020)
        contact_email: Email for Crossref identification (recommended for polite use)
        throttle_sec: Delay between requests (seconds, default 1.0 for polite use)
        **kwargs: Additional arguments passed to habanero

    Yields:
        Dictionary with fields matching Document model

    Raises:
        ImportError: If habanero is not installed
    """
    if not HABANERO_AVAILABLE:
        raise ImportError(
            "habanero library is required. Install with: pip install habanero"
        )

    logger.info(f"Starting Crossref discovery via habanero with {len(keywords)} keywords")

    # Initialize Crossref client
    cr = Crossref(mailto=contact_email) if contact_email else Crossref()

    # Build query from keywords
    # Crossref supports space-separated keywords (AND logic by default)
    # For OR logic, we can use query.title:keyword1 OR query.title:keyword2
    # For simplicity, use space-separated (AND) which works well for focused topics
    # Limit to first 5 keywords to avoid query length issues
    query_parts = []
    for kw in keywords[:5]:
        query_parts.append(kw.strip())
    
    search_query = " ".join(query_parts)

    count = 0
    offset = 0
    rows_per_page = 20  # Crossref default is 20, max is 1000

    try:
        while True:
            if max_records is not None and count >= max_records:
                break

            # Calculate how many rows to request
            remaining = max_records - count if max_records else rows_per_page
            current_rows = min(rows_per_page, remaining) if max_records else rows_per_page

            # Polite rate limiting
            if throttle_sec > 0:
                time.sleep(throttle_sec)

            try:
                # Use habanero's works() method
                # habanero accepts filter as dict, not string
                filter_dict = None
                if year_filter:
                    filter_dict = {"from-pub-date": f"{year_filter}"}
                
                result = cr.works(query=search_query, limit=current_rows, offset=offset, filter=filter_dict)
                
                # Extract items from result
                # habanero returns a dict with 'message' key containing the API response
                if isinstance(result, dict):
                    message = result.get("message", {})
                else:
                    # Sometimes habanero returns the message directly
                    message = result if isinstance(result, dict) else {}
                items = message.get("items", [])

                if not items:
                    logger.info("No more items from Crossref API")
                    break

                # Process each item
                for item in items:
                    if max_records is not None and count >= max_records:
                        break

                    # Apply year filter if specified (post-filter if API filter didn't work)
                    if year_filter:
                        issued = item.get("issued", {}).get("date-parts", [])
                        if issued and issued[0] and len(issued[0]) > 0:
                            try:
                                item_year = int(issued[0][0])
                                if item_year < year_filter:
                                    continue
                            except (ValueError, TypeError):
                                pass

                    # Map Crossref output to Document schema
                    mapped = map_crossref_to_document(item, source="crossref")
                    if mapped:
                        yield mapped
                        count += 1

                # Check if there are more pages
                total_results = message.get("total-results", 0)
                if offset + len(items) >= total_results:
                    logger.info("Reached end of Crossref results")
                    break

                offset += len(items)

            except Exception as e:
                logger.error(f"Error during Crossref API call: {e}")
                # If it's a rate limit error, wait longer
                if "429" in str(e) or "rate limit" in str(e).lower():
                    wait_time = 60
                    logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                raise

        logger.info(f"Crossref discovery complete: {count} records")

    except Exception as e:
        logger.error(f"Error during Crossref discovery: {e}")
        raise

