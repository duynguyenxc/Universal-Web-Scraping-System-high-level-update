"""TRID adapter: Maps TRID-specific data to universal Document schema.

This adapter:
1. Uses sitemap parser to discover TRID record URLs
2. Crawls HTML pages to extract metadata
3. Maps to universal Document schema
4. Respects robots.txt and rate limits
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Iterator, Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from ...discovery.sitemap import parse_sitemap
from ...store.models import Document
from ...utils.http import session_with_retries
from .html_parser import extract_trid_metadata

logger = logging.getLogger(__name__)

# TRID URLs
TRID_SITEMAP_URL = "https://trid.trb.org/sitemap.xml"
TRID_BASE_URL = "https://trid.trb.org"


def discover_trid(
    max_records: Optional[int] = None,
    throttle_sec: float = 2.0,
    respect_robots: bool = True,
) -> Iterator[dict]:
    """Discover TRID records via sitemap crawling.
    
    Args:
        max_records: Maximum number of records to discover
        throttle_sec: Delay between requests (seconds)
        respect_robots: Whether to check robots.txt before crawling
        
    Yields:
        Dictionary with metadata mapped to Document schema fields
    """
    # Check robots.txt if requested
    if respect_robots:
        if not _check_robots_txt():
            logger.warning("robots.txt check failed or disallowed, but continuing")
    
    # Parse sitemap to get URLs
    logger.info(f"Parsing TRID sitemap: {TRID_SITEMAP_URL}")
    url_count = 0
    
    for url in parse_sitemap(
        TRID_SITEMAP_URL, max_urls=max_records, throttle_sec=throttle_sec
    ):
        if max_records is not None and url_count >= max_records:
            break
        
        # Throttle before fetching HTML
        if throttle_sec > 0:
            time.sleep(throttle_sec)
        
        # Fetch and parse HTML page
        try:
            metadata = _fetch_and_parse_trid_page(url)
            if metadata:
                yield metadata
                url_count += 1
        except Exception as e:
            logger.warning(f"Failed to process {url}: {e}")
            continue


def _check_robots_txt() -> bool:
    """Check robots.txt to ensure crawling is allowed.
    
    Returns:
        True if crawling is allowed, False otherwise
    """
    try:
        rp = RobotFileParser()
        rp.set_url(f"{TRID_BASE_URL}/robots.txt")
        rp.read()
        
        # Check if we can fetch the sitemap
        can_fetch_sitemap = rp.can_fetch("*", TRID_SITEMAP_URL)
        can_fetch_records = rp.can_fetch("*", f"{TRID_BASE_URL}/view/")
        
        logger.info(f"robots.txt check - sitemap: {can_fetch_sitemap}, records: {can_fetch_records}")
        
        return can_fetch_sitemap and can_fetch_records
    except Exception as e:
        logger.warning(f"Failed to check robots.txt: {e}")
        return True  # Default to allowing if check fails


def _fetch_and_parse_trid_page(url: str) -> Optional[dict]:
    """Fetch TRID HTML page and extract metadata.
    
    Args:
        url: URL to TRID record page
        
    Returns:
        Dictionary with metadata, or None if extraction fails
    """
    session = session_with_retries()
    
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None
    
    # Extract metadata from HTML
    try:
        metadata = extract_trid_metadata(resp.text, url)
    except Exception as e:
        logger.warning(f"Failed to extract metadata from {url}: {e}")
        return None
    
    # Map to universal Document schema
    return _map_to_document_schema(metadata)


def _map_to_document_schema(metadata: dict) -> dict:
    """Map TRID metadata to universal Document schema.
    
    Args:
        metadata: Raw metadata from HTML parser
        
    Returns:
        Dictionary with fields matching Document model
    """
    # Convert authors list to JSON string (as stored in DB)
    authors_json = json.dumps(metadata.get("authors", [])) if metadata.get("authors") else None
    
    # Generate URL hash for deduplication
    url_hash = hashlib.sha1(metadata["source_url"].encode()).hexdigest()
    
    return {
        "source_url": metadata["source_url"],
        "landing_url": metadata["source_url"],  # TRID pages are landing pages
        "title": metadata.get("title"),
        "abstract": metadata.get("abstract"),
        "authors": authors_json,
        "doi": metadata.get("doi"),
        "year": metadata.get("year"),
        "source": "trid",
        "url_hash_sha1": url_hash,
        # PDF URL would be extracted if available on the page
        "pdf_url": None,  # TRID may have PDF links, but need to check HTML structure
        "oa_status": "unknown",  # Would need to check if PDF is available
    }

