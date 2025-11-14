"""HTML metadata extractor for TRID pages.

Extracts academic metadata from TRID HTML pages using multiple strategies:
1. Academic meta tags (citation_*)
2. CSS selectors (common HTML patterns)
3. Heuristic patterns (fallback)
"""

from __future__ import annotations

import logging
import re
from typing import Dict, Optional

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise ImportError(
        "BeautifulSoup4 is required for HTML parsing. Install with: pip install beautifulsoup4 lxml"
    )

logger = logging.getLogger(__name__)


def extract_trid_metadata(html: str, url: str) -> Dict[str, Optional[str | list[str]]]:
    """Extract metadata from TRID HTML page.
    
    Uses multiple extraction strategies with fallback:
    1. Academic meta tags (citation_title, citation_author, etc.)
    2. CSS selectors (common HTML patterns)
    3. Heuristic patterns (regex, text analysis)
    
    Args:
        html: HTML content of the TRID page
        url: Source URL of the page
        
    Returns:
        Dictionary with extracted metadata:
        - title: str | None
        - abstract: str | None
        - authors: list[str]
        - doi: str | None
        - year: int | None
        - source_url: str
        - source: str (always 'trid')
    """
    soup = BeautifulSoup(html, "lxml")
    
    # Strategy 1: Academic meta tags (highest priority)
    title = _extract_title_meta(soup) or _extract_title_html(soup)
    abstract = _extract_abstract_meta(soup) or _extract_abstract_html(soup)
    authors = _extract_authors_meta(soup) or _extract_authors_html(soup)
    doi = _extract_doi_meta(soup) or _extract_doi_text(html)
    year = _extract_year_meta(soup) or _extract_year_text(html)
    
    return {
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "doi": doi.lower() if doi else None,
        "year": year,
        "source_url": url,
        "source": "trid",
    }


def _extract_title_meta(soup: BeautifulSoup) -> Optional[str]:
    """Extract title from academic meta tags."""
    # Try citation_title first
    meta = soup.find("meta", {"name": "citation_title"})
    if meta and meta.get("content"):
        return meta["content"].strip()
    
    # Try og:title
    meta = soup.find("meta", {"property": "og:title"})
    if meta and meta.get("content"):
        return meta["content"].strip()
    
    return None


def _extract_title_html(soup: BeautifulSoup) -> Optional[str]:
    """Extract title from HTML elements."""
    # Try h1 first
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)
    
    # Try title tag
    title_tag = soup.find("title")
    if title_tag and title_tag.get_text(strip=True):
        title_text = title_tag.get_text(strip=True)
        # Remove common suffixes like " - TRID"
        title_text = re.sub(r"\s*-\s*TRID.*$", "", title_text, flags=re.IGNORECASE)
        return title_text.strip()
    
    return None


def _extract_abstract_meta(soup: BeautifulSoup) -> Optional[str]:
    """Extract abstract from academic meta tags."""
    # Try citation_abstract
    meta = soup.find("meta", {"name": "citation_abstract"})
    if meta and meta.get("content"):
        return meta["content"].strip()
    
    # Try description
    meta = soup.find("meta", {"name": "description"})
    if meta and meta.get("content"):
        return meta["content"].strip()
    
    return None


def _extract_abstract_html(soup: BeautifulSoup) -> Optional[str]:
    """Extract abstract from HTML elements."""
    # Try common abstract selectors
    selectors = [
        ".abstract",
        "#abstract",
        "[class*='abstract']",
        "[id*='abstract']",
        ".summary",
        "#summary",
    ]
    
    for selector in selectors:
        elem = soup.select_one(selector)
        if elem and elem.get_text(strip=True):
            text = elem.get_text(strip=True)
            # Filter out very short text (likely not abstract)
            if len(text) > 50:
                return text
    
    return None


def _extract_authors_meta(soup: BeautifulSoup) -> list[str]:
    """Extract authors from academic meta tags."""
    authors = []
    
    # citation_author can appear multiple times
    for meta in soup.find_all("meta", {"name": "citation_author"}):
        if meta.get("content"):
            authors.append(meta["content"].strip())
    
    if authors:
        return authors
    
    # Try dc.creator
    for meta in soup.find_all("meta", {"name": "dc.creator"}):
        if meta.get("content"):
            authors.append(meta["content"].strip())
    
    return authors


def _extract_authors_html(soup: BeautifulSoup) -> list[str]:
    """Extract authors from HTML elements."""
    authors = []
    
    # Try common author selectors
    selectors = [
        ".author",
        ".authors",
        "[class*='author']",
        "[class*='creator']",
    ]
    
    for selector in selectors:
        for elem in soup.select(selector):
            text = elem.get_text(strip=True)
            if text and text not in authors:
                # Split by comma or semicolon if multiple authors
                for author in re.split(r"[;,]|\sand\s", text):
                    author = author.strip()
                    if author and len(author) > 2:
                        authors.append(author)
        if authors:
            break
    
    return authors


def _extract_doi_meta(soup: BeautifulSoup) -> Optional[str]:
    """Extract DOI from meta tags."""
    meta = soup.find("meta", {"name": "citation_doi"})
    if meta and meta.get("content"):
        return meta["content"].strip()
    
    return None


def _extract_doi_text(html: str) -> Optional[str]:
    """Extract DOI using regex pattern."""
    # DOI pattern: 10.xxxx/xxxx
    doi_pattern = r"10\.\d+/[^\s<>\"']+"
    match = re.search(doi_pattern, html)
    if match:
        return match.group(0)
    return None


def _extract_year_meta(soup: BeautifulSoup) -> Optional[int]:
    """Extract year from meta tags."""
    # Try citation_publication_date
    meta = soup.find("meta", {"name": "citation_publication_date"})
    if meta and meta.get("content"):
        date_str = meta["content"].strip()
        # Extract year from date string (YYYY-MM-DD or YYYY)
        year_match = re.search(r"\b(19|20)\d{2}\b", date_str)
        if year_match:
            return int(year_match.group(0))
    
    # Try dc.date
    meta = soup.find("meta", {"name": "dc.date"})
    if meta and meta.get("content"):
        date_str = meta["content"].strip()
        year_match = re.search(r"\b(19|20)\d{2}\b", date_str)
        if year_match:
            return int(year_match.group(0))
    
    return None


def _extract_year_text(html: str) -> Optional[int]:
    """Extract year using regex pattern."""
    # Look for 4-digit years in reasonable range
    year_pattern = r"\b(19|20)\d{2}\b"
    matches = re.findall(year_pattern, html)
    if matches:
        # Return the most recent year found
        years = [int(m[0] + m[1]) for m in matches]
        # Filter reasonable years (1900-2100)
        years = [y for y in years if 1900 <= y <= 2100]
        if years:
            return max(years)
    return None

