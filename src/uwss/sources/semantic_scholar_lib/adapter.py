"""Semantic Scholar adapter: Main discovery function using semanticscholar library."""

from __future__ import annotations

import logging
import time
from typing import Iterator, Optional

from .mapper import map_semantic_scholar_to_document

logger = logging.getLogger(__name__)

# Try to import semanticscholar, but handle gracefully if not available
try:
    from semanticscholar import SemanticScholar

    SEMANTICSCHOLAR_AVAILABLE = True
except ImportError:
    SEMANTICSCHOLAR_AVAILABLE = False
    SemanticScholar = None
    logger.warning(
        "semanticscholar library not available. Install with: pip install semanticscholar"
    )


def discover_semantic_scholar(
    keywords: list[str],
    max_records: Optional[int] = None,
    year_filter: Optional[int] = None,
    api_key: Optional[str] = None,
    throttle_sec: float = 0.1,  # Semantic Scholar allows fast requests
    **kwargs,
) -> Iterator[dict]:
    """Discover Semantic Scholar papers via semanticscholar library.

    Args:
        keywords: List of keywords to search for
        max_records: Maximum number of records to discover
        year_filter: Optional year filter (e.g., 2020)
        api_key: Optional API key for higher rate limits
        throttle_sec: Delay between requests (seconds)
        **kwargs: Additional arguments passed to semanticscholar

    Yields:
        Dictionary with fields matching Document model

    Raises:
        ImportError: If semanticscholar is not installed
    """
    if not SEMANTICSCHOLAR_AVAILABLE:
        raise ImportError(
            "semanticscholar library is required. Install with: pip install semanticscholar"
        )

    logger.info(f"Starting Semantic Scholar discovery via semanticscholar with {len(keywords)} keywords")

    # Initialize SemanticScholar client
    sch = SemanticScholar(api_key=api_key) if api_key else SemanticScholar()

    # Build search query from keywords
    # Check if this is corrosion research (based on keywords)
    is_corrosion_search = any(term.lower() in ['corrosion', 'concrete', 'steel', 'reinforced', 'chloride', 'civil engineering']
                             for term in keywords)

    if is_corrosion_search:
        # Use corrosion-specific search queries for better results
        corrosion_queries = [
            "corrosion reinforced concrete",
            "steel corrosion protection",
            "concrete corrosion chloride",
            "corrosion inhibition civil engineering",
            "corrosion stainless steel concrete",
            "corrosion cracking concrete",
            "corrosion durability concrete"
        ]
        logger.info(f"Using corrosion-specific search with {len(corrosion_queries)} queries")
    else:
        # Semantic Scholar search works best with focused queries
        # Use first 3 keywords for better results
        corrosion_queries = [" ".join(keywords[:3])]

    count = 0
    seen_titles = set()  # For deduplication across queries
    limit_per_query = min((max_records or 100) // len(corrosion_queries), 50)  # Distribute limit

    try:
        for query_idx, search_query in enumerate(corrosion_queries):
            if max_records is not None and count >= max_records:
                break

            logger.info(f"Query {query_idx + 1}/{len(corrosion_queries)}: '{search_query}'")

            # Polite rate limiting
            if throttle_sec > 0:
                time.sleep(throttle_sec)

            # Use SemanticScholar's search_paper() method
            try:
                # Build query parameters
                query_params = {
                    "query": search_query,
                    "limit": limit_per_query,
                }

                results = sch.search_paper(**query_params)

                if not results:
                    logger.info(f"No results for query: {search_query}")
                    continue

                # results is a PaginatedResults object, iterate through it
                for paper in results:
                    if max_records is not None and count >= max_records:
                        break

                # Convert paper object to dict if needed
                # Semantic Scholar returns Paper objects, not dicts
                paper_dict = {}
                if hasattr(paper, '__dict__'):
                    paper_dict = paper.__dict__
                elif hasattr(paper, 'to_dict'):
                    paper_dict = paper.to_dict()
                else:
                    # Try to access attributes directly
                    paper_dict = {
                        'title': getattr(paper, 'title', None),
                        'year': getattr(paper, 'year', None),
                        'abstract': getattr(paper, 'abstract', None),
                        'authors': getattr(paper, 'authors', []),
                        'doi': getattr(paper, 'externalIds', {}).get('DOI') if hasattr(paper, 'externalIds') else None,
                        'url': getattr(paper, 'url', None),
                        'venue': getattr(paper, 'venue', None),
                        'openAccessPdf': getattr(paper, 'openAccessPdf', None),
                    }

                # Apply year filter if specified
                if year_filter:
                    pub_year = paper_dict.get("year") or getattr(paper, 'year', None)
                    if pub_year:
                        try:
                            if int(pub_year) < year_filter:
                                continue
                        except (ValueError, TypeError):
                            pass

                # Map Semantic Scholar output to Document schema
                # Pass both dict and object to mapper
                mapped = map_semantic_scholar_to_document(paper_dict, source="semantic_scholar", paper_obj=paper)
                if mapped:
                    yield mapped
                    count += 1

        except Exception as e:
            logger.error(f"Error during Semantic Scholar API call: {e}")
            # If it's a rate limit error, wait longer
            if "429" in str(e) or "rate limit" in str(e).lower():
                wait_time = 60
                logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            raise

        logger.info(f"Semantic Scholar discovery complete: {count} records")

    except Exception as e:
        logger.error(f"Error during Semantic Scholar discovery: {e}")
        raise

