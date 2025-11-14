"""OpenAlex adapter: Discovers papers via REST API with cursor-based pagination.

Key requirements from OpenAlex:
1. MUST include mailto= parameter (or in User-Agent header)
2. Use filter= instead of search= for stable results
3. Use cursor-based pagination (not page=)
4. Handle rate limits (100k requests/day free tier)
5. Proper error handling and logging
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Iterator, Optional
from urllib.parse import urlencode

from ...store.models import Document
from ...utils.http import session_with_retries

logger = logging.getLogger(__name__)

# OpenAlex API
OPENALEX_BASE = "https://api.openalex.org/works"


def discover_openalex(
    keywords: list[str],
    max_records: Optional[int] = None,
    contact_email: Optional[str] = None,
    throttle_sec: float = 0.1,  # OpenAlex allows fast requests, but be respectful
    year_filter: Optional[int] = None,
) -> Iterator[dict]:
    """Discover OpenAlex papers using filter-based queries with cursor pagination.
    
    Args:
        keywords: List of keywords to search for
        max_records: Maximum number of records to discover
        contact_email: Email for OpenAlex identification (REQUIRED by ToS)
        throttle_sec: Delay between requests (seconds)
        year_filter: Optional year filter (e.g., 2020)
        
    Yields:
        Dictionary with metadata mapped to Document schema fields
        
    Raises:
        ValueError: If contact_email is not provided (required by OpenAlex ToS)
    """
    if not contact_email:
        raise ValueError(
            "contact_email is REQUIRED for OpenAlex API (per ToS). "
            "Provide via --config or --contact-email argument."
        )
    
    session = session_with_retries()
    
    # Build query params
    # Use search= for keywords (more flexible, handles multiple keywords well)
    # Use filter= for structured filters (year, concepts, etc.)
    # Strategy: Use top 3 most relevant keywords to avoid URL length issues
    # OpenAlex search works best with focused queries (3-5 keywords max)
    # If too many keywords, only use first 3 for better results
    limited_keywords = keywords[:3]  # Use first 3 keywords for better precision and URL length
    search_query = " ".join(limited_keywords)
    
    logger.info(f"Using {len(limited_keywords)} keywords for search: {search_query[:100]}...")
    
    # Build base params
    params = {
        "search": search_query,  # Use search= for keyword matching
        "per_page": 200,  # Max per page
        "sort": "relevance_score:desc",
        "mailto": contact_email,  # REQUIRED by OpenAlex ToS
    }
    
    if year_filter:
        params["from_publication_date"] = f"{year_filter}-01-01"
    
    # Cursor-based pagination
    cursor = "*"  # Start cursor
    count = 0
    
    logger.info(f"Starting OpenAlex discovery with search: {search_query[:100]}...")
    
    while True:
        if max_records is not None and count >= max_records:
            break
        
        # Add cursor to params
        current_params = dict(params)
        if cursor and cursor != "*":
            current_params["cursor"] = cursor
        
        try:
            # Make request
            if throttle_sec > 0:
                time.sleep(throttle_sec)
            
            resp = session.get(
                OPENALEX_BASE,
                params=current_params,
                headers={
                    "User-Agent": f"uwss/0.1 (+mailto:{contact_email})",
                    "Accept": "application/json",
                },
                timeout=30,
            )
            
            # Check for rate limiting
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                continue
            
            resp.raise_for_status()
            data = resp.json()
            
            # Log response info for debugging
            meta = data.get("meta", {})
            result_count = data.get("results_count", 0)
            logger.debug(f"OpenAlex response: {result_count} total results, {len(data.get('results', []))} in this page")
            
        except Exception as e:
            logger.error(f"Failed to fetch OpenAlex page: {e}")
            # Log URL for debugging
            if 'resp' in locals():
                logger.debug(f"Request URL: {resp.url}")
                logger.debug(f"Response status: {resp.status_code}")
                logger.debug(f"Response text: {resp.text[:500]}")
            break
        
        # Extract results
        results = data.get("results", [])
        if not results:
            logger.info("No more results from OpenAlex")
            break
        
        # Process each result
        for item in results:
            if max_records is not None and count >= max_records:
                break
            
            try:
                metadata = _map_openalex_to_document_schema(item)
                if metadata:
                    yield metadata
                    count += 1
            except Exception as e:
                logger.warning(f"Failed to process OpenAlex record: {e}")
                continue
        
        # Get next cursor
        meta = data.get("meta", {})
        next_cursor = meta.get("next_cursor")
        
        if not next_cursor:
            logger.info("No more pages (next_cursor is None)")
            break
        
        cursor = next_cursor
        
        logger.debug(f"Processed {count} records, next cursor: {cursor[:20]}...")
    
    logger.info(f"OpenAlex discovery complete: {count} records")


def _map_openalex_to_document_schema(item: dict) -> Optional[dict]:
    """Map OpenAlex JSON response to universal Document schema.
    
    Args:
        item: Single work object from OpenAlex API
        
    Returns:
        Dictionary with fields matching Document model, or None if mapping fails
    """
    try:
        # Extract basic fields
        title = item.get("title", "").strip()
        if not title:
            return None
        
        # Abstract
        abstract = item.get("abstract", "")
        if abstract:
            # OpenAlex abstracts may have HTML/markdown, strip basic tags
            import re
            abstract = re.sub(r"<[^>]+>", "", abstract).strip()
        
        # Authors
        authors = []
        authorships = item.get("authorships", [])
        for authorship in authorships:
            author = authorship.get("author", {})
            if author:
                display_name = author.get("display_name", "")
                if display_name:
                    authors.append(display_name)
        
        # Affiliations (from authorships)
        affiliations = []
        for authorship in authorships:
            institutions = authorship.get("institutions", [])
            for inst in institutions:
                display_name = inst.get("display_name", "")
                if display_name and display_name not in affiliations:
                    affiliations.append(display_name)
        
        # DOI
        doi = None
        doi_url = item.get("doi")
        if doi_url:
            # Extract DOI from URL (e.g., "https://doi.org/10.1234/abc" -> "10.1234/abc")
            doi = doi_url.replace("https://doi.org/", "").replace("http://doi.org/", "").lower()
        
        # Year
        year = item.get("publication_year")
        
        # Open access status
        oa_info = item.get("open_access", {})
        is_oa = oa_info.get("is_oa", False)
        oa_url = oa_info.get("oa_url", "")
        
        # Determine OA status
        if is_oa and oa_url:
            oa_status = "fulltext_pdf"
            pdf_url = oa_url
        elif is_oa:
            oa_status = "open"
            pdf_url = None
        else:
            oa_status = "closed"
            pdf_url = None
        
        # Source URL (OpenAlex ID)
        source_url = item.get("id", "")
        
        # Landing URL (primary location)
        landing_url = source_url
        primary_location = item.get("primary_location", {})
        landing_page_url = primary_location.get("landing_page_url")
        if landing_page_url:
            landing_url = landing_page_url
        
        # Keywords (from concepts)
        keywords = []
        concepts = item.get("concepts", [])
        for concept in concepts[:10]:  # Top 10 concepts
            display_name = concept.get("display_name", "")
            if display_name:
                keywords.append(display_name)
        
        # Generate URL hash for deduplication
        url_hash = hashlib.sha1(source_url.encode()).hexdigest() if source_url else None
        
        # Convert lists to JSON strings (as stored in DB)
        authors_json = json.dumps(authors) if authors else None
        affiliations_json = json.dumps(affiliations) if affiliations else None
        keywords_json = json.dumps(keywords) if keywords else None
        
        return {
            "source_url": source_url,
            "landing_url": landing_url,
            "title": title,
            "abstract": abstract,
            "authors": authors_json,
            "affiliations": affiliations_json,
            "keywords": keywords_json,
            "doi": doi,
            "year": year,
            "source": "openalex",
            "url_hash_sha1": url_hash,
            "pdf_url": pdf_url,
            "oa_status": oa_status,
            "open_access": is_oa,
        }
        
    except Exception as e:
        logger.error(f"Error mapping OpenAlex record: {e}")
        return None

