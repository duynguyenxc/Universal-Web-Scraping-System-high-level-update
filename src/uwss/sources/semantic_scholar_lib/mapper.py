"""Mapper: Convert Semantic Scholar API response to UWSS Document schema."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _clip(text: Optional[str], max_len: int) -> Optional[str]:
    """Clip text to maximum length."""
    if not text:
        return None
    if len(text) <= max_len:
        return text
    return text[:max_len]


def map_semantic_scholar_to_document(
    paper: dict, source: str = "semantic_scholar", paper_obj=None
) -> Optional[dict]:
    """Map Semantic Scholar paper to UWSS Document schema.

    Args:
        paper: Dictionary from Semantic Scholar API with fields like:
            - title, authors, doi, year, abstract, url, etc.
        source: Source identifier (e.g., "semantic_scholar")

    Returns:
        Dictionary with fields matching Document model, or None if mapping fails
    """
    try:
        # Try to get data from paper_obj if available (Semantic Scholar returns objects, not dicts)
        if paper_obj and hasattr(paper_obj, 'title'):
            # Use object attributes
            title = getattr(paper_obj, 'title', '').strip() if getattr(paper_obj, 'title', None) else ''
            abstract = getattr(paper_obj, 'abstract', '').strip() if getattr(paper_obj, 'abstract', None) else ''
            year = getattr(paper_obj, 'year', None)
            if year:
                try:
                    year = int(year)
                except (ValueError, TypeError):
                    year = None
            
            # Extract authors
            authors = []
            authors_raw = getattr(paper_obj, 'authors', [])
            if authors_raw:
                for author in authors_raw:
                    if hasattr(author, 'name'):
                        name = author.name
                    elif isinstance(author, dict):
                        name = author.get("name", "")
                    elif isinstance(author, str):
                        name = author
                    else:
                        continue
                    if name:
                        authors.append(str(name).strip())
            
            # Extract DOI
            doi = None
            external_ids = getattr(paper_obj, 'externalIds', None)
            if external_ids:
                if hasattr(external_ids, 'get'):
                    doi = external_ids.get("DOI", "").strip() if external_ids.get("DOI") else None
                elif isinstance(external_ids, dict):
                    doi = external_ids.get("DOI", "").strip() if external_ids.get("DOI") else None
            
            # Extract URLs
            landing_url = getattr(paper_obj, 'url', '') or ''
            pdf_url = None
            open_access_pdf = getattr(paper_obj, 'openAccessPdf', None)
            if open_access_pdf:
                if hasattr(open_access_pdf, 'url'):
                    pdf_url = open_access_pdf.url
                elif isinstance(open_access_pdf, dict):
                    pdf_url = open_access_pdf.get("url", "")
            # Normalize empty string to None
            if pdf_url == "":
                pdf_url = None
            
            venue = getattr(paper_obj, 'venue', None)
            if venue:
                venue = str(venue).strip()
        else:
            # Fallback to dict access
            title = paper.get("title", "").strip()
            abstract = paper.get("abstract", "").strip()
            year = paper.get("year")
            if year:
                try:
                    year = int(year)
                except (ValueError, TypeError):
                    year = None
            
            # Extract authors
            authors = []
            authors_raw = paper.get("authors", [])
            if isinstance(authors_raw, list):
                for author in authors_raw:
                    if isinstance(author, dict):
                        name = author.get("name", "")
                    elif isinstance(author, str):
                        name = author
                    elif hasattr(author, 'name'):
                        name = author.name
                    else:
                        continue
                    if name:
                        authors.append(str(name).strip())
            
            # Extract DOI
            doi = None
            external_ids = paper.get("externalIds", {})
            if external_ids:
                doi = external_ids.get("DOI", "").strip() if external_ids.get("DOI") else None
            
            # Extract URLs
            landing_url = paper.get("url", "")
            pdf_url = None
            open_access_pdf = paper.get("openAccessPdf", {})
            if open_access_pdf:
                pdf_url = open_access_pdf.get("url", "") if isinstance(open_access_pdf, dict) else None
            # Normalize empty string to None
            if pdf_url == "":
                pdf_url = None
            
            venue = paper.get("venue", "").strip() if paper.get("venue") else None

        if not title:
            logger.debug("Skipping paper with no title")
            return None

        authors_json = json.dumps(authors) if authors else None
        source_url = landing_url or (f"https://doi.org/{doi}" if doi else "")

        # Determine open access status
        open_access = bool(pdf_url) or bool(open_access_pdf)
        oa_status = "fulltext_pdf" if pdf_url else ("open" if open_access else "closed")

        # Generate URL hash for deduplication
        url_hash = None
        url_for_hash = pdf_url or landing_url or source_url or doi
        if url_for_hash:
            try:
                url_hash = hashlib.sha1(str(url_for_hash).encode("utf-8")).hexdigest()
            except Exception:
                pass

        # Build Document-compatible dictionary
        return {
            "source": source,
            "source_url": source_url or "",
            "landing_url": landing_url or "",
            "pdf_url": pdf_url,
            "doi": _clip(doi, 255),
            "title": _clip(title, 1000),
            "abstract": _clip(abstract, 20000),
            "authors": authors_json,
            "affiliations": None,  # Semantic Scholar doesn't provide affiliations in basic response
            "keywords": None,  # Can be extracted from fieldsOfStudy if needed
            "venue": _clip(venue, 255),
            "year": year,
            "open_access": open_access,
            "oa_status": oa_status,
            "url_hash_sha1": url_hash,
        }

    except Exception as e:
        logger.error(f"Error mapping Semantic Scholar paper to document: {e}")
        return None

