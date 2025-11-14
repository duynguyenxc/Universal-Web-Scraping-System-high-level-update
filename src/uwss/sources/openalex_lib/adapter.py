"""OpenAlex adapter: Main discovery function using pyalex library."""

from __future__ import annotations

import logging
import time
from typing import Iterator, Optional

from .mapper import map_openalex_to_document

logger = logging.getLogger(__name__)

# Try to import pyalex, but handle gracefully if not available
try:
    from pyalex import Works, config

    PYALEX_AVAILABLE = True
except ImportError:
    PYALEX_AVAILABLE = False
    Works = None
    config = None
    logger.warning(
        "pyalex library not available. Install with: pip install pyalex"
    )


def discover_openalex(
    keywords: list[str],
    max_records: Optional[int] = None,
    year_filter: Optional[int] = None,
    contact_email: Optional[str] = None,
    throttle_sec: float = 0.1,  # OpenAlex allows fast requests, but be respectful
    **kwargs,
) -> Iterator[dict]:
    """Discover OpenAlex papers via pyalex library.

    Args:
        keywords: List of keywords to search for
        max_records: Maximum number of records to discover
        year_filter: Optional year filter (e.g., 2020)
        contact_email: Email for OpenAlex identification (REQUIRED by ToS)
        throttle_sec: Delay between requests (seconds)
        **kwargs: Additional arguments passed to pyalex

    Yields:
        Dictionary with fields matching Document model

    Raises:
        ImportError: If pyalex is not installed
        ValueError: If contact_email is not provided (required by OpenAlex ToS)
    """
    if not PYALEX_AVAILABLE:
        raise ImportError(
            "pyalex library is required. Install with: pip install pyalex"
        )

    if not contact_email:
        raise ValueError(
            "contact_email is REQUIRED for OpenAlex API (per ToS). "
            "Provide via --config or --contact-email argument."
        )

    logger.info(f"Starting OpenAlex discovery via pyalex with {len(keywords)} keywords")

    # Configure pyalex with contact email
    config.email = contact_email

    # Build search query from keywords
    # OpenAlex search works best with focused queries
    # Try using first 3 keywords for better results
    limited_keywords = keywords[:3]
    search_query = " ".join(limited_keywords)

    count = 0

    try:
        # Initialize Works client
        works = Works()

        # Build search - use simple search first
        search = works.search(search_query)

        # Add year filter if specified
        if year_filter:
            search = search.filter(from_publication_date=f"{year_filter}-01-01")

        # Polite rate limiting
        if throttle_sec > 0:
            time.sleep(throttle_sec)

        # Get results - pyalex returns an iterator that handles pagination automatically
        try:
            results = search.get()

            # Process each work
            for work in results:
                if max_records is not None and count >= max_records:
                    break

                # Apply year filter if specified (post-filter if API filter didn't work)
                if year_filter:
                    pub_date = work.get("publication_date")
                    if pub_date:
                        try:
                            work_year = int(pub_date.split("-")[0])
                            if work_year < year_filter:
                                continue
                        except (ValueError, TypeError):
                            pass

                # Map OpenAlex output to Document schema
                mapped = map_openalex_to_document(work, source="openalex")
                if mapped:
                    yield mapped
                    count += 1

                # Small delay between items to be polite
                if throttle_sec > 0 and count % 10 == 0:
                    time.sleep(throttle_sec)

        except Exception as e:
            logger.error(f"Error during OpenAlex API call: {e}")
            # If it's a rate limit error, wait longer
            if "429" in str(e) or "rate limit" in str(e).lower():
                wait_time = 60
                logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            raise

        logger.info(f"OpenAlex discovery complete: {count} records")

    except Exception as e:
        logger.error(f"Error during OpenAlex discovery: {e}")
        raise

