"""Query builders: Build paperscraper queries from keywords and filters.

This module handles the conversion of UWSS keywords and filters
into paperscraper-compatible query formats.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def build_paperscraper_query(
    keywords: list[str], year_filter: Optional[int] = None
) -> list[list[str]]:
    """Build paperscraper query format from keywords.

    Paperscraper expects queries in the format:
    [[keyword1, keyword2], [keyword3, keyword4]]
    where inner lists are ANDed and outer lists are ORed.

    Args:
        keywords: List of keywords to search for
        year_filter: Optional year filter (not directly supported by paperscraper,
                    but can be filtered post-query)

    Returns:
        Query in paperscraper format: list of lists of keywords

    Notes:
        - Paperscraper uses AND within each sublist, OR between sublists
        - For focused queries, we can group related keywords together
        - For broad queries, we can put each keyword in its own sublist
    """
    if not keywords:
        logger.warning("No keywords provided, returning empty query")
        return [[]]

    # Strategy: Group keywords into related clusters
    # For now, simple approach: each keyword as a separate OR term
    # This gives broad coverage (any keyword match)
    query = [[kw] for kw in keywords if kw.strip()]

    # Alternative strategy (commented out): Group related keywords
    # This would give more focused results (all keywords in group must match)
    # query = [keywords]  # All keywords must match

    logger.debug(f"Built paperscraper query with {len(query)} keyword groups")

    # Note: year_filter is not directly supported by paperscraper query format
    # We'll need to filter results post-query if year_filter is provided
    if year_filter:
        logger.info(f"Year filter {year_filter} will be applied post-query")

    return query


