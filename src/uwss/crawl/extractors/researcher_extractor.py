"""Researcher information extraction from web pages.

Extracts:
- Name, affiliation, email
- Research interests
- Homepage URL
- ORCID (if available)
"""

from __future__ import annotations

import re
from typing import Optional, Dict, List
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from scrapy.selector import Selector


def extract_researcher_info(html: str, url: str) -> Dict[str, any]:
    """Extract researcher information from HTML page.
    
    Args:
        html: HTML content
        url: Page URL
        
    Returns:
        Dictionary with researcher info:
        - name: Researcher name
        - email: Email address
        - affiliation: Institution/affiliation
        - homepage: Homepage URL
        - research_interests: List of research interests
        - orcid: ORCID ID if found
    """
    result = {
        "name": None,
        "email": None,
        "affiliation": None,
        "homepage": None,
        "research_interests": [],
        "orcid": None,
    }
    
    selector = Selector(text=html)
    soup = BeautifulSoup(html, 'lxml')
    
    # Extract name (usually in h1 or title)
    name = selector.css("h1::text").get() or selector.css("title::text").get()
    if name:
        # Clean up title (remove "Dr.", "Prof.", etc.)
        name = re.sub(r'^(Dr\.|Prof\.|Professor|Dr)\s+', '', name.strip(), flags=re.IGNORECASE)
        name = re.sub(r'\s*\|\s*.*$', '', name)  # Remove site name
        result["name"] = name.strip()
    
    # Extract email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, html)
    if emails:
        # Prefer academic emails (.edu, .ac.*)
        academic_emails = [e for e in emails if re.search(r'\.(edu|ac\.[a-z]{2,}|gov)$', e, re.IGNORECASE)]
        result["email"] = academic_emails[0] if academic_emails else emails[0]
    
    # Extract affiliation
    affiliation_patterns = [
        r'Affiliation[s]?:\s*([^\n]+)',
        r'Institution[s]?:\s*([^\n]+)',
        r'University:\s*([^\n]+)',
        r'Department:\s*([^\n]+)',
    ]
    text_content = " ".join(selector.css("body::text").getall())
    for pattern in affiliation_patterns:
        match = re.search(pattern, text_content, re.IGNORECASE)
        if match:
            result["affiliation"] = match.group(1).strip()
            break
    
    # If no explicit affiliation, try to infer from email domain
    if not result["affiliation"] and result["email"]:
        email_domain = result["email"].split('@')[1] if '@' in result["email"] else None
        if email_domain:
            # Remove common email providers
            if email_domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
                result["affiliation"] = email_domain
    
    # Extract homepage (usually in links)
    homepage_links = selector.css('a[href*="homepage"], a[href*="website"], a[href*="personal"]::attr(href)').getall()
    if homepage_links:
        result["homepage"] = homepage_links[0]
    
    # Extract research interests
    interest_sections = selector.css('.research-interests, .interests, #interests, [class*="interest"]::text').getall()
    if interest_sections:
        interests_text = " ".join(interest_sections)
        # Split by comma, semicolon, or newline
        interests = re.split(r'[,;]\s*|\n', interests_text)
        result["research_interests"] = [i.strip() for i in interests if i.strip() and len(i.strip()) > 3]
    
    # Extract ORCID
    orcid_pattern = r'\b\d{4}-\d{4}-\d{4}-\d{3}[X\d]\b'
    orcid_match = re.search(orcid_pattern, html)
    if orcid_match:
        result["orcid"] = orcid_match.group(0)
    
    # Also check for ORCID links
    orcid_links = selector.css('a[href*="orcid.org"]::attr(href)').getall()
    if orcid_links:
        for link in orcid_links:
            orcid_match = re.search(r'(\d{4}-\d{4}-\d{4}-\d{3}[X\d])', link)
            if orcid_match:
                result["orcid"] = orcid_match.group(1)
                break
    
    return result


