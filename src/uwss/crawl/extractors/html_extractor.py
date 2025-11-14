"""HTML metadata extraction with multi-strategy approach.

Extracts academic metadata from HTML pages using multiple strategies:
1. Academic meta tags (citation_*)
2. Common HTML patterns (h1, .abstract, .author)
3. Heuristic patterns (email, "Author:" labels)
"""

from __future__ import annotations

import re
from typing import Optional, Dict, List
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from scrapy.selector import Selector


def extract_metadata(html: str, url: str) -> Dict[str, any]:
    """Extract academic metadata from HTML using multiple strategies.
    
    Args:
        html: HTML content as string
        url: Source URL
        
    Returns:
        Dictionary with extracted metadata:
        - title: Document title
        - abstract: Abstract/description
        - authors: List of authors
        - affiliations: List of affiliations
        - keywords: List of keywords
        - doi: DOI if found
        - year: Publication year
        - pdf_url: PDF URL if found
        - venue: Publication venue/journal
    """
    result = {
        "title": None,
        "abstract": None,
        "authors": [],
        "affiliations": [],
        "keywords": [],
        "doi": None,
        "year": None,
        "pdf_url": None,
        "venue": None,
    }
    
    # Use both Scrapy Selector and BeautifulSoup for maximum compatibility
    selector = Selector(text=html)
    soup = BeautifulSoup(html, 'lxml')
    
    # Strategy 1: Academic meta tags (highest priority)
    result.update(_extract_from_meta_tags(selector, soup))
    
    # Strategy 2: Common HTML patterns
    if not result["title"]:
        result["title"] = _extract_title(selector, soup)
    if not result["abstract"]:
        result["abstract"] = _extract_abstract(selector, soup)
    if not result["authors"]:
        result["authors"] = _extract_authors(selector, soup)
    if not result["affiliations"]:
        result["affiliations"] = _extract_affiliations(selector, soup)
    if not result["keywords"]:
        result["keywords"] = _extract_keywords(selector, soup)
    
    # Strategy 3: Extract PDF links
    if not result["pdf_url"]:
        result["pdf_url"] = _extract_pdf_url(selector, soup, url)
    
    # Strategy 4: Extract DOI and year from text
    if not result["doi"]:
        result["doi"] = _extract_doi_from_text(html)
    if not result["year"]:
        result["year"] = _extract_year_from_text(html)
    
    return result


def _extract_from_meta_tags(selector: Selector, soup: BeautifulSoup) -> Dict:
    """Extract metadata from academic meta tags."""
    result = {}
    
    # Citation meta tags (common in academic sites)
    citation_title = selector.xpath('//meta[@name="citation_title"]/@content').get()
    if citation_title:
        result["title"] = citation_title.strip()
    
    citation_abstract = selector.xpath('//meta[@name="citation_abstract"]/@content').get()
    if citation_abstract:
        result["abstract"] = citation_abstract.strip()
    
    # Multiple citation_author tags
    citation_authors = selector.xpath('//meta[@name="citation_author"]/@content').getall()
    if citation_authors:
        result["authors"] = [a.strip() for a in citation_authors if a.strip()]
    
    citation_affiliation = selector.xpath('//meta[@name="citation_author_institution"]/@content').getall()
    if citation_affiliation:
        result["affiliations"] = [a.strip() for a in citation_affiliation if a.strip()]
    
    citation_doi = selector.xpath('//meta[@name="citation_doi"]/@content').get()
    if citation_doi:
        result["doi"] = citation_doi.strip()
    
    citation_date = selector.xpath('//meta[@name="citation_publication_date"]/@content').get()
    if citation_date:
        # Extract year from date (format: YYYY-MM-DD or YYYY)
        year_match = re.search(r'(\d{4})', citation_date)
        if year_match:
            result["year"] = int(year_match.group(1))
    
    citation_pdf = selector.xpath('//meta[@name="citation_pdf_url"]/@content').get()
    if citation_pdf:
        result["pdf_url"] = citation_pdf.strip()
    
    citation_journal = selector.xpath('//meta[@name="citation_journal_title"]/@content').get()
    if citation_journal:
        result["venue"] = citation_journal.strip()
    
    # Dublin Core meta tags
    dc_title = selector.xpath('//meta[@name="DC.Title"]/@content').get()
    if dc_title and not result.get("title"):
        result["title"] = dc_title.strip()
    
    dc_description = selector.xpath('//meta[@name="DC.Description"]/@content').get()
    if dc_description and not result.get("abstract"):
        result["abstract"] = dc_description.strip()
    
    # Open Graph meta tags
    og_title = selector.xpath('//meta[@property="og:title"]/@content').get()
    if og_title and not result.get("title"):
        result["title"] = og_title.strip()
    
    og_description = selector.xpath('//meta[@property="og:description"]/@content').get()
    if og_description and not result.get("abstract"):
        result["abstract"] = og_description.strip()
    
    return result


def _extract_title(selector: Selector, soup: BeautifulSoup) -> Optional[str]:
    """Extract title from HTML structure."""
    # Try h1 first
    title = selector.css("h1::text").get()
    if title and title.strip():
        return title.strip()
    
    # Try title tag
    title = selector.css("title::text").get()
    if title and title.strip():
        # Clean up title (remove site name, etc.)
        title = title.strip()
        # Remove common suffixes like " | Site Name"
        title = re.sub(r'\s*\|\s*.*$', '', title)
        return title
    
    return None


def _extract_abstract(selector: Selector, soup: BeautifulSoup) -> Optional[str]:
    """Extract abstract/description from HTML."""
    # Try common abstract selectors
    abstract = selector.css(".abstract::text, #abstract::text, .description::text").get()
    if abstract and len(abstract.strip()) > 50:
        return abstract.strip()
    
    # Try meta description
    meta_desc = selector.xpath('//meta[@name="description"]/@content').get()
    if meta_desc and len(meta_desc.strip()) > 50:
        return meta_desc.strip()
    
    # Heuristic: First long paragraph in main content
    main_content = selector.css("main p::text, article p::text, .content p::text").getall()
    if main_content:
        # Find longest paragraph (likely abstract)
        longest = max(main_content, key=len)
        if len(longest.strip()) > 100:
            return longest.strip()
    
    # Fallback: First paragraph
    first_p = selector.css("p::text").get()
    if first_p and len(first_p.strip()) > 100:
        return first_p.strip()
    
    return None


def _extract_authors(selector: Selector, soup: BeautifulSoup) -> List[str]:
    """Extract authors from HTML."""
    authors = []
    
    # Common author selectors
    author_texts = selector.css(".author::text, .authors::text, .author-name::text, [class*='author']::text").getall()
    authors.extend([a.strip() for a in author_texts if a.strip() and len(a.strip()) > 2])
    
    # Try to find "Author:" or "Authors:" labels
    text_content = " ".join(selector.css("body::text").getall())
    author_patterns = [
        r'Author[s]?:\s*([^\n]+)',
        r'By\s+([^\n]+)',
        r'Written by\s+([^\n]+)',
    ]
    for pattern in author_patterns:
        matches = re.findall(pattern, text_content, re.IGNORECASE)
        for match in matches:
            # Split by comma, semicolon, or "and"
            names = re.split(r'[,;]|\s+and\s+', match)
            authors.extend([n.strip() for n in names if n.strip() and len(n.strip()) > 2])
    
    # Extract from email patterns (often in author sections)
    email_pattern = r'([A-Za-z][A-Za-z0-9._-]*\s+[A-Za-z][A-Za-z0-9._-]*)\s*<[^>]+@[^>]+>'
    emails = re.findall(email_pattern, text_content)
    authors.extend([e.strip() for e in emails if e.strip()])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_authors = []
    for author in authors:
        author_lower = author.lower()
        if author_lower not in seen:
            seen.add(author_lower)
            unique_authors.append(author)
    
    return unique_authors[:10]  # Limit to 10 authors


def _extract_affiliations(selector: Selector, soup: BeautifulSoup) -> List[str]:
    """Extract affiliations from HTML."""
    affiliations = []
    
    # Common affiliation selectors
    aff_texts = selector.css(".affiliation::text, .institution::text, [class*='affiliation']::text").getall()
    affiliations.extend([a.strip() for a in aff_texts if a.strip() and len(a.strip()) > 5])
    
    # Try to find "Affiliation:" labels
    text_content = " ".join(selector.css("body::text").getall())
    aff_patterns = [
        r'Affiliation[s]?:\s*([^\n]+)',
        r'Institution[s]?:\s*([^\n]+)',
        r'University:\s*([^\n]+)',
    ]
    for pattern in aff_patterns:
        matches = re.findall(pattern, text_content, re.IGNORECASE)
        affiliations.extend([m.strip() for m in matches if m.strip() and len(m.strip()) > 5])
    
    # Remove duplicates
    seen = set()
    unique_affs = []
    for aff in affiliations:
        aff_lower = aff.lower()
        if aff_lower not in seen:
            seen.add(aff_lower)
            unique_affs.append(aff)
    
    return unique_affs[:5]  # Limit to 5 affiliations


def _extract_keywords(selector: Selector, soup: BeautifulSoup) -> List[str]:
    """Extract keywords from HTML."""
    keywords = []
    
    # Meta keywords
    meta_keywords = selector.xpath('//meta[@name="keywords"]/@content').get()
    if meta_keywords:
        keywords.extend([k.strip() for k in meta_keywords.split(',') if k.strip()])
    
    # DC.Keywords
    dc_keywords = selector.xpath('//meta[@name="DC.Subject"]/@content').getall()
    keywords.extend([k.strip() for k in dc_keywords if k.strip()])
    
    return keywords[:20]  # Limit to 20 keywords


def _extract_pdf_url(selector: Selector, soup: BeautifulSoup, base_url: str) -> Optional[str]:
    """Extract PDF URL from page."""
    from urllib.parse import urljoin
    
    # Look for PDF links
    pdf_links = selector.css('a[href$=".pdf"]::attr(href)').getall()
    if pdf_links:
        # Prefer "download" or "pdf" in link text
        for link in pdf_links:
            full_url = urljoin(base_url, link)
            return full_url
        # Return first PDF link
        return urljoin(base_url, pdf_links[0])
    
    # Look for PDF in meta tags
    pdf_meta = selector.xpath('//meta[@name="citation_pdf_url"]/@content').get()
    if pdf_meta:
        return urljoin(base_url, pdf_meta)
    
    return None


def _extract_doi_from_text(text: str) -> Optional[str]:
    """Extract DOI from text using regex."""
    # DOI pattern: 10.xxxx/xxxx
    doi_pattern = r'\b10\.\d{4,}/[^\s]+'
    match = re.search(doi_pattern, text)
    if match:
        return match.group(0)
    return None


def _extract_year_from_text(text: str) -> Optional[int]:
    """Extract publication year from text."""
    # Look for years in common patterns: (2024), [2024], 2024, etc.
    year_patterns = [
        r'\((\d{4})\)',
        r'\[(\d{4})\]',
        r'\b(19|20)\d{2}\b',
    ]
    for pattern in year_patterns:
        matches = re.findall(pattern, text)
        if matches:
            # Get the last match (likely publication year)
            year_str = matches[-1] if isinstance(matches[-1], str) else str(matches[-1])
            try:
                year = int(year_str)
                if 1900 <= year <= 2100:  # Reasonable range
                    return year
            except ValueError:
                continue
    return None


