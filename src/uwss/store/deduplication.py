"""Deduplication utilities for cross-source document matching.

Provides standardized deduplication logic that can be reused across all source adapters.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from .models import Document

logger = logging.getLogger(__name__)


def find_duplicate(
    session: Session,
    metadata: dict,
    check_doi: bool = True,
    check_source_url: bool = True,
    check_title: bool = False,
) -> Optional[Document]:
    """Find duplicate document using multiple strategies.
    
    Args:
        session: SQLAlchemy session
        metadata: Document metadata dictionary with fields:
            - doi: Optional DOI string
            - source_url: Optional source URL string
            - title: Optional title string (for title-based matching)
        check_doi: Whether to check for duplicates by DOI (default: True)
        check_source_url: Whether to check for duplicates by source_url (default: True)
        check_title: Whether to check for duplicates by normalized title (default: False)
        
    Returns:
        Existing Document if duplicate found, None otherwise
        
    Strategy (in order of priority):
    1. DOI-based matching (most reliable)
    2. source_url-based matching
    3. Title-based matching (if enabled, less reliable)
    
    Notes:
        - DOI matching is case-insensitive and normalized (lowercase, stripped)
        - source_url matching is exact
        - Title matching (if enabled) is case-insensitive and normalized
    """
    # Strategy 1: DOI-based matching (most reliable)
    if check_doi and metadata.get("doi"):
        doi = metadata["doi"].strip().lower()
        if doi:
            existing = (
                session.query(Document)
                .filter(Document.doi == doi)
                .first()
            )
            if existing:
                logger.debug(f"Duplicate found by DOI: {doi[:50]}...")
                return existing
    
    # Strategy 2: source_url-based matching
    if check_source_url and metadata.get("source_url"):
        source_url = metadata["source_url"].strip()
        if source_url:
            existing = (
                session.query(Document)
                .filter(Document.source_url == source_url)
                .first()
            )
            if existing:
                logger.debug(f"Duplicate found by source_url: {source_url[:50]}...")
                return existing
    
    # Strategy 3: Title-based matching (optional, less reliable)
    if check_title and metadata.get("title"):
        title = _normalize_title(metadata["title"])
        if title:
            existing = (
                session.query(Document)
                .filter(Document.title.isnot(None))
                .all()
            )
            # Check normalized title match
            for doc in existing:
                if doc.title and _normalize_title(doc.title) == title:
                    logger.debug(f"Duplicate found by title: {title[:50]}...")
                    return doc
    
    return None


def _normalize_title(title: str) -> str:
    """Normalize title for comparison.
    
    Args:
        title: Title string
        
    Returns:
        Normalized title (lowercase, stripped, extra spaces removed)
    """
    if not title:
        return ""
    # Lowercase, strip, remove extra spaces
    normalized = " ".join(title.lower().strip().split())
    return normalized


def merge_document_metadata(existing: Document, new_metadata: dict) -> None:
    """Merge new metadata into existing document (fill missing fields).
    
    Args:
        existing: Existing Document object
        new_metadata: New metadata dictionary
        
    Notes:
        - Only fills missing/None fields
        - Prefers existing data over new data
        - Useful for enriching documents from multiple sources
    """
    # Fill missing title
    if not existing.title and new_metadata.get("title"):
        existing.title = new_metadata["title"]
    
    # Fill missing abstract
    if not existing.abstract and new_metadata.get("abstract"):
        existing.abstract = new_metadata["abstract"]
    
    # Fill missing authors (merge if both exist)
    if new_metadata.get("authors"):
        if not existing.authors:
            existing.authors = new_metadata["authors"]
        # Could merge authors lists here if needed
    
    # Fill missing DOI
    if not existing.doi and new_metadata.get("doi"):
        existing.doi = new_metadata["doi"]
    
    # Fill missing year
    if not existing.year and new_metadata.get("year"):
        existing.year = new_metadata["year"]
    
    # Fill missing affiliations
    if not existing.affiliations and new_metadata.get("affiliations"):
        existing.affiliations = new_metadata["affiliations"]
    
    # Fill missing keywords
    if not existing.keywords and new_metadata.get("keywords"):
        existing.keywords = new_metadata["keywords"]
    
    # Update OA status if new one is better (open > closed)
    if new_metadata.get("oa_status"):
        if existing.oa_status in (None, "closed", "abstract_only"):
            if new_metadata["oa_status"] in ("open", "fulltext_pdf"):
                existing.oa_status = new_metadata["oa_status"]
    
    # Update PDF URL if missing
    if not existing.pdf_url and new_metadata.get("pdf_url"):
        existing.pdf_url = new_metadata["pdf_url"]


