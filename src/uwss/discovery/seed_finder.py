"""Seed URL discovery for research groups and faculty pages.

Discovers seed URLs from:
1. Papers already in database (extract affiliations/homepages)
2. University directories
3. Conference proceedings
4. Known research group websites
"""

from __future__ import annotations

import re
from typing import List, Set
from urllib.parse import urlparse
from sqlalchemy import select

from ..store.models import Document
from ..store.db import create_sqlite_engine


def find_seeds_from_database(
    db_path: str,
    keywords: List[str] | None = None,
    limit: int = 50
) -> List[str]:
    """Find seed URLs from existing database records.
    
    Extracts:
    - Homepage URLs from affiliations
    - Author homepages
    - PDF source domains
    
    Args:
        db_path: Path to SQLite database
        keywords: Optional keywords to filter records
        limit: Maximum number of seeds to return
        
    Returns:
        List of seed URLs
    """
    engine, SessionLocal = create_sqlite_engine(db_path)
    session = SessionLocal()
    
    try:
        seeds: Set[str] = set()
        
        # Query documents
        query = session.query(Document)
        if keywords:
            # Filter by keywords in title/abstract
            keyword_filters = []
            for kw in keywords:
                keyword_filters.append(
                    (Document.title.contains(kw)) |
                    (Document.abstract.contains(kw))
                )
            if keyword_filters:
                from sqlalchemy import or_
                query = query.filter(or_(*keyword_filters))
        
        documents = query.limit(limit * 10).all()  # Get more to extract URLs
        
        for doc in documents:
            # Extract URLs from affiliations
            if doc.affiliations:
                import json
                try:
                    affs = json.loads(doc.affiliations) if isinstance(doc.affiliations, str) else doc.affiliations
                    for aff in affs if isinstance(affs, list) else [affs]:
                        urls = _extract_urls_from_text(str(aff))
                        seeds.update(urls)
                except:
                    pass
            
            # Extract from source_url domain (add homepage)
            if doc.source_url:
                parsed = urlparse(doc.source_url)
                if parsed.netloc:
                    homepage = f"{parsed.scheme}://{parsed.netloc}"
                    seeds.add(homepage)
        
        # Convert to list and limit
        seed_list = list(seeds)[:limit]
        return seed_list
        
    finally:
        session.close()


def _extract_urls_from_text(text: str) -> List[str]:
    """Extract URLs from text."""
    # URL pattern
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, text)
    
    # Clean and validate
    valid_urls = []
    for url in urls:
        try:
            parsed = urlparse(url)
            if parsed.netloc and parsed.scheme in ('http', 'https'):
                # Remove trailing punctuation
                url = url.rstrip('.,;:!?)')
                valid_urls.append(url)
        except:
            continue
    
    return valid_urls


def find_seeds_from_keywords(keywords: List[str], limit: int = 20) -> List[str]:
    """Generate seed URLs from keywords (future: use search engines).
    
    For now, returns empty list. Future implementation could:
    - Use Google Scholar search
    - Use university directory APIs
    - Use conference websites
    
    Args:
        keywords: Research topic keywords
        limit: Maximum number of seeds
        
    Returns:
        List of seed URLs
    """
    # TODO: Implement search-based seed discovery
    # For now, return empty list
    return []


def find_seeds_from_papers(db_path: str, limit: int = 50) -> List[str]:
    """Find seed URLs from paper metadata (homepages, affiliations).
    
    Extracts:
    - Homepage URLs from author metadata
    - Institution homepages from affiliations
    - Conference/proceedings URLs
    
    Args:
        db_path: Path to SQLite database
        limit: Maximum number of seeds
        
    Returns:
        List of seed URLs
    """
    engine, SessionLocal = create_sqlite_engine(db_path)
    session = SessionLocal()
    
    try:
        seeds: Set[str] = set()
        
        # Query documents with affiliations or authors
        documents = session.query(Document).filter(
            (Document.affiliations.isnot(None)) | (Document.authors.isnot(None))
        ).limit(limit * 5).all()
        
        for doc in documents:
            # Extract from affiliations
            if doc.affiliations:
                import json
                try:
                    affs = json.loads(doc.affiliations) if isinstance(doc.affiliations, str) else doc.affiliations
                    for aff in affs if isinstance(affs, list) else [affs]:
                        urls = _extract_urls_from_text(str(aff))
                        seeds.update(urls)
                except:
                    pass
            
            # Extract from source_url (get domain homepage)
            if doc.source_url:
                parsed = urlparse(doc.source_url)
                if parsed.netloc:
                    homepage = f"{parsed.scheme}://{parsed.netloc}"
                    seeds.add(homepage)
            
            # Extract from landing_url
            if doc.landing_url:
                parsed = urlparse(doc.landing_url)
                if parsed.netloc:
                    homepage = f"{parsed.scheme}://{parsed.netloc}"
                    seeds.add(homepage)
        
        # Convert to list and limit
        seed_list = list(seeds)[:limit]
        return seed_list
        
    finally:
        session.close()


def get_default_academic_seeds() -> List[str]:
    """Get default seed URLs for academic domains.
    
    Returns:
        List of common academic/research websites
    """
    return [
        # Add common research group websites here
        # Example: "https://example-research-group.edu",
    ]

