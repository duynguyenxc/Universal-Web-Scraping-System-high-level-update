"""Crossref adapter: Discovers papers via REST API with offset-based pagination.

Key features:
1. REST API: https://api.crossref.org/works
2. Offset-based pagination (not cursor-based)
3. Abstract support (advantage over OpenAlex)
4. Polite rate limiting (no official limit, but be respectful)
5. Proper error handling and logging
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from typing import Iterator, Optional
from urllib.parse import urlencode

from ...store.models import Document
from ...utils.http import session_with_retries

logger = logging.getLogger(__name__)

# Crossref API
CROSSREF_BASE = "https://api.crossref.org/works"


def discover_crossref(
    keywords: list[str],
    max_records: Optional[int] = None,
    contact_email: Optional[str] = None,
    throttle_sec: float = 1.0,  # Crossref recommends polite use (1 req/sec)
    year_filter: Optional[int] = None,
) -> Iterator[dict]:
    """Discover Crossref papers using query-based search with offset pagination.
    
    Args:
        keywords: List of keywords to search for
        max_records: Maximum number of records to discover
        contact_email: Email for Crossref identification (recommended for polite use)
        throttle_sec: Delay between requests (seconds, default 1.0 for polite use)
        year_filter: Optional year filter (e.g., 2020)
        
    Yields:
        Dictionary with metadata mapped to Document schema fields
        
    Notes:
        - Crossref API is free and open, but recommends polite use
        - Include contact_email in User-Agent for better service
        - Use throttle_sec >= 1.0 to be respectful
    """
    session = session_with_retries()
    
    # Build query string from keywords
    # Crossref supports space-separated keywords (AND logic by default)
    # For OR logic, use query.title:keyword1 OR query.title:keyword2
    # For simplicity, use space-separated (AND) which works well for focused topics
    query_parts = []
    for kw in keywords[:5]:  # Limit to top 5 keywords to avoid URL length issues
        # Escape special characters and wrap in quotes for exact phrase matching
        escaped = kw.replace('"', '\\"')
        query_parts.append(f'"{escaped}"')
    
    search_query = " OR ".join(query_parts) if len(query_parts) > 1 else query_parts[0] if query_parts else ""
    
    logger.info(f"Using {len(query_parts)} keywords for Crossref search: {search_query[:100]}...")
    
    # Build base params
    params = {
        "query": search_query,
        "rows": 100,  # Max per page (Crossref allows up to 1000, but 100 is safer)
        "sort": "relevance",  # Sort by relevance
    }
    
    if contact_email:
        # Include in User-Agent header (recommended by Crossref)
        pass  # Will be set in headers
    
    if year_filter:
        # Crossref filter syntax: from-pub-date:YYYY-MM-DD
        params["filter"] = f"from-pub-date:{year_filter}-01-01"
    
    # Offset-based pagination
    offset = 0
    count = 0
    
    logger.info(f"Starting Crossref discovery with query: {search_query[:100]}...")
    
    while True:
        if max_records is not None and count >= max_records:
            break
        
        # Update offset
        current_params = dict(params)
        current_params["offset"] = str(offset)
        
        # Build headers
        headers = {
            "Accept": "application/json",
        }
        if contact_email:
            headers["User-Agent"] = f"uwss/0.1 (mailto:{contact_email})"
        else:
            headers["User-Agent"] = "uwss/0.1"
        
        try:
            # Make request
            if throttle_sec > 0:
                time.sleep(throttle_sec)
            
            url = f"{CROSSREF_BASE}?{urlencode(current_params)}"
            logger.debug(f"Crossref request: {url[:150]}...")
            
            resp = session.get(CROSSREF_BASE, params=current_params, headers=headers, timeout=30)
            
            # Handle rate limiting (429)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                continue
            
            resp.raise_for_status()
            data = resp.json()
            
            # Extract items from response
            message = data.get("message", {})
            items = message.get("items", [])
            
            if not items:
                logger.info("No more items from Crossref API")
                break
            
            # Process each item
            for item in items:
                mapped = _map_crossref_to_document_schema(item)
                if mapped:
                    yield mapped
                    count += 1
                    
                    if max_records is not None and count >= max_records:
                        break
            
            # Check if there are more pages
            total_results = message.get("total-results", 0)
            current_offset = message.get("query", {}).get("start-index", 0)
            rows_per_page = message.get("query", {}).get("rows", 100)
            
            logger.debug(f"Crossref: offset={offset}, count={count}, total={total_results}")
            
            # Check if we've reached the end
            if offset + rows_per_page >= total_results:
                logger.info(f"Reached end of Crossref results (total: {total_results})")
                break
            
            # Update offset for next page
            offset += rows_per_page
            
        except Exception as e:
            logger.error(f"Error fetching Crossref page at offset {offset}: {e}")
            # Continue to next page instead of breaking (more resilient)
            offset += params["rows"]
            if offset > 10000:  # Safety limit
                logger.warning("Reached safety limit (10000 records), stopping")
                break
    
    logger.info(f"Crossref discovery complete: {count} records")


def _map_crossref_to_document_schema(item: dict) -> Optional[dict]:
    """Map Crossref JSON response to universal Document schema.
    
    Args:
        item: Single work object from Crossref API
        
    Returns:
        Dictionary with fields matching Document model, or None if mapping fails
    """
    try:
        # Extract basic fields
        title_list = item.get("title", [])
        title = title_list[0] if title_list else ""
        title = title.strip()
        
        if not title:
            return None
        
        # Abstract (Crossref has good abstract support!)
        abstract = ""
        # Crossref abstracts can be in different formats:
        # 1. Direct string in "abstract" field
        # 2. List of strings in "abstract" field
        # 3. HTML content that needs parsing
        abstract_raw = item.get("abstract")
        if abstract_raw:
            if isinstance(abstract_raw, list):
                # List format: take first non-empty string
                for ab in abstract_raw:
                    if isinstance(ab, str) and ab.strip():
                        abstract_raw = ab
                        break
                else:
                    abstract_raw = None
            if abstract_raw and isinstance(abstract_raw, str):
                # Remove HTML tags and clean up
                abstract = re.sub(r"<[^>]+>", "", abstract_raw).strip()
                # Remove extra whitespace
                abstract = re.sub(r"\s+", " ", abstract)
        
        # Authors
        authors = []
        author_list = item.get("author", [])
        for author in author_list:
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            if given and family:
                authors.append(f"{given} {family}")
            elif family:
                authors.append(family)
            elif given:
                authors.append(given)
        
        # Affiliations (from authors)
        affiliations = []
        for author in author_list:
            affil_list = author.get("affiliation", [])
            for affil in affil_list:
                affil_name = affil.get("name", "").strip()
                if affil_name and affil_name not in affiliations:
                    affiliations.append(affil_name)
        
        # DOI
        doi = item.get("DOI", "").lower() if item.get("DOI") else None
        
        # Year (from published-print or published-online)
        year = None
        published_print = item.get("published-print", {})
        if published_print:
            date_parts = published_print.get("date-parts", [])
            if date_parts and len(date_parts[0]) > 0:
                year = date_parts[0][0]
        
        if not year:
            published_online = item.get("published-online", {})
            if published_online:
                date_parts = published_online.get("date-parts", [])
                if date_parts and len(date_parts[0]) > 0:
                    year = date_parts[0][0]
        
        # Open access status
        # Crossref provides license information
        license_list = item.get("license", [])
        is_oa = False
        oa_url = None
        
        for license_item in license_list:
            if license_item.get("content-version") == "vor":  # Version of Record
                is_oa = True
                oa_url = license_item.get("URL")
                break
        
        # Also check for open access indicators
        if not is_oa:
            # Check for free-to-read or other OA indicators
            free_to_read = item.get("free-to-read", {})
            if free_to_read:
                is_oa = True
        
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
        
        # Source URL (Crossref DOI URL)
        source_url = f"https://doi.org/{doi}" if doi else None
        
        # Landing URL (preferred URL from Crossref)
        preferred_url = item.get("URL")
        landing_url = preferred_url or source_url
        
        # Keywords (from subject)
        keywords = []
        subject_list = item.get("subject", [])
        for subject in subject_list[:10]:  # Top 10 subjects
            if isinstance(subject, str):
                keywords.append(subject)
        
        # Generate URL hash for deduplication
        url_hash = hashlib.sha1(source_url.encode()).hexdigest() if source_url else None
        
        # Convert lists to JSON strings (as stored in DB)
        authors_json = json.dumps(authors) if authors else None
        affiliations_json = json.dumps(affiliations) if affiliations else None
        keywords_json = json.dumps(keywords) if keywords else None
        
        return {
            "source": "crossref",
            "source_url": source_url or "",
            "landing_url": landing_url or "",
            "title": title,
            "abstract": abstract,
            "authors": authors_json,
            "affiliations": affiliations_json,
            "keywords": keywords_json,
            "doi": doi,
            "year": year,
            "oa_status": oa_status,
            "pdf_url": pdf_url,
            "url_hash_sha1": url_hash,
        }
        
    except Exception as e:
        logger.error(f"Error mapping Crossref item to schema: {e}")
        return None

