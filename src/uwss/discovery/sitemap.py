"""Generic sitemap.xml parser for discovering URLs from sitemaps.

This module provides a reusable sitemap parser that can handle:
- Standard sitemaps (list of URLs)
- Sitemap indexes (nested sitemaps)
- Recursive parsing of nested structures
"""

from __future__ import annotations

import logging
import time
from typing import Iterator, Optional
import xml.etree.ElementTree as ET

from ..utils.http import session_with_retries

logger = logging.getLogger(__name__)

# Sitemap namespace
SITEMAP_NS = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def parse_sitemap(
    sitemap_url: str,
    max_urls: Optional[int] = None,
    throttle_sec: float = 1.0,
    timeout: int = 30,
) -> Iterator[str]:
    """Parse sitemap.xml and yield URLs.
    
    Handles both standard sitemaps and sitemap indexes (nested sitemaps).
    Recursively parses nested sitemaps.
    
    Args:
        sitemap_url: URL to sitemap.xml
        max_urls: Maximum number of URLs to yield (None for unlimited)
        throttle_sec: Delay between requests (seconds)
        timeout: Request timeout (seconds)
        
    Yields:
        URLs from the sitemap(s)
        
    Raises:
        requests.RequestException: If HTTP request fails
        xml.etree.ElementTree.ParseError: If XML parsing fails
    """
    session = session_with_retries()
    yield from _parse_sitemap_recursive(
        session, sitemap_url, max_urls=max_urls, throttle_sec=throttle_sec, timeout=timeout
    )


def _parse_sitemap_recursive(
    session,
    sitemap_url: str,
    max_urls: Optional[int] = None,
    throttle_sec: float = 1.0,
    timeout: int = 30,
    _urls_yielded: list[int] = None,
) -> Iterator[str]:
    """Recursively parse sitemap, handling nested sitemap indexes.
    
    Internal function that handles recursion for nested sitemaps.
    Uses a list to track yielded count across recursive calls.
    """
    if _urls_yielded is None:
        _urls_yielded = [0]
    
    logger.info(f"Parsing sitemap: {sitemap_url}")
    
    try:
        resp = session.get(sitemap_url, timeout=timeout)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch sitemap {sitemap_url}: {e}")
        raise
    
    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        logger.error(f"Failed to parse XML from {sitemap_url}: {e}")
        raise
    
    # Check if this is a sitemap index (contains nested sitemaps)
    if root.tag.endswith("sitemapindex") or any(
        child.tag.endswith("sitemap") for child in root
    ):
        logger.debug(f"Found sitemap index: {sitemap_url}")
        # This is a sitemap index - recursively parse child sitemaps
        for sitemap_elem in root.findall(".//sitemap:sitemap", SITEMAP_NS):
            if max_urls is not None and _urls_yielded[0] >= max_urls:
                return
            loc_elem = sitemap_elem.find("sitemap:loc", SITEMAP_NS)
            if loc_elem is not None and loc_elem.text:
                child_url = loc_elem.text.strip()
                # Throttle before fetching child sitemap
                if throttle_sec > 0:
                    time.sleep(throttle_sec)
                yield from _parse_sitemap_recursive(
                    session,
                    child_url,
                    max_urls=max_urls,
                    throttle_sec=throttle_sec,
                    timeout=timeout,
                    _urls_yielded=_urls_yielded,
                )
    else:
        # This is a standard sitemap - extract URLs
        logger.debug(f"Found standard sitemap: {sitemap_url}")
        for url_elem in root.findall(".//sitemap:url", SITEMAP_NS):
            if max_urls is not None and _urls_yielded[0] >= max_urls:
                return
            loc_elem = url_elem.find("sitemap:loc", SITEMAP_NS)
            if loc_elem is not None and loc_elem.text:
                url = loc_elem.text.strip()
                yield url
                _urls_yielded[0] += 1


def parse_sitemap_simple(sitemap_url: str, timeout: int = 30) -> list[str]:
    """Simple non-recursive sitemap parser (for testing).
    
    Only parses the immediate sitemap, does not handle nested sitemaps.
    
    Args:
        sitemap_url: URL to sitemap.xml
        timeout: Request timeout (seconds)
        
    Returns:
        List of URLs from the sitemap
    """
    session = session_with_retries()
    resp = session.get(sitemap_url, timeout=timeout)
    resp.raise_for_status()
    
    root = ET.fromstring(resp.text)
    urls = []
    
    for url_elem in root.findall(".//sitemap:url", SITEMAP_NS):
        loc_elem = url_elem.find("sitemap:loc", SITEMAP_NS)
        if loc_elem is not None and loc_elem.text:
            urls.append(loc_elem.text.strip())
    
    return urls

