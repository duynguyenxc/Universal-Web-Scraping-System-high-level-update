"""Mappers: Convert paperscraper output to UWSS Document schema.

This module handles the mapping between paperscraper's output format
and UWSS's universal Document schema.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def _clip(text: Optional[str], max_len: int) -> Optional[str]:
    """Clip text to maximum length for database constraints."""
    if text is None:
        return None
    try:
        s = str(text)
        return s[:max_len] if len(s) > max_len else s
    except Exception:
        return text


def map_paperscraper_to_document(
    paper: dict, source: str = "paperscraper"
) -> Optional[dict]:
    """Map paperscraper paper dictionary to UWSS Document schema.

    Args:
        paper: Dictionary from paperscraper with fields like:
            - title, abstract, authors, doi, year, url, pdf_url, journal, etc.
        source: Source identifier (e.g., "paperscraper_pubmed")

    Returns:
        Dictionary with fields matching Document model, or None if mapping fails

    Notes:
        - Handles various paperscraper output formats
        - Normalizes fields (DOI, authors, etc.)
        - Generates URL hash for deduplication
    """
    try:
        # Extract title (required)
        title = paper.get("title") or paper.get("Title") or ""
        title = title.strip()
        if not title:
            logger.debug("Skipping paper with no title")
            return None

        # Extract abstract
        abstract = (
            paper.get("abstract")
            or paper.get("Abstract")
            or paper.get("summary")
            or ""
        )
        abstract = abstract.strip()

        # Extract authors (can be list or string)
        authors = []
        authors_raw = paper.get("authors") or paper.get("Authors") or []
        if isinstance(authors_raw, str):
            # Try to parse if it's a JSON string
            try:
                authors_raw = json.loads(authors_raw)
            except Exception:
                # Split by common delimiters
                authors_raw = [a.strip() for a in re.split(r"[;,]", authors_raw) if a.strip()]
        if isinstance(authors_raw, list):
            authors = [str(a).strip() for a in authors_raw if str(a).strip()]
        authors_json = json.dumps(authors) if authors else None

        # Extract affiliations
        affiliations = []
        affils_raw = paper.get("affiliations") or paper.get("Affiliation") or []
        if isinstance(affils_raw, str):
            try:
                affils_raw = json.loads(affils_raw)
            except Exception:
                affils_raw = [a.strip() for a in re.split(r"[;,]", affils_raw) if a.strip()]
        if isinstance(affils_raw, list):
            affiliations = [str(a).strip() for a in affils_raw if str(a).strip()]
        affiliations_json = json.dumps(affiliations) if affiliations else None

        # Extract keywords/subjects
        keywords = []
        keywords_raw = paper.get("keywords") or paper.get("Keywords") or paper.get("subjects") or []
        if isinstance(keywords_raw, str):
            try:
                keywords_raw = json.loads(keywords_raw)
            except Exception:
                keywords_raw = [k.strip() for k in re.split(r"[;,]", keywords_raw) if k.strip()]
        if isinstance(keywords_raw, list):
            keywords = [str(k).strip() for k in keywords_raw if str(k).strip()]
        keywords_json = json.dumps(keywords) if keywords else None

        # Extract DOI (normalize to lowercase)
        doi = None
        doi_raw = paper.get("doi") or paper.get("DOI") or paper.get("doi_url") or ""
        if doi_raw:
            # Extract DOI from URL if needed
            if "doi.org" in str(doi_raw).lower():
                doi = str(doi_raw).split("doi.org/")[-1].split("/")[0].lower()
            else:
                doi = str(doi_raw).replace("doi:", "").strip().lower()

        # Extract year (from year field or date field)
        year = None
        year_raw = paper.get("year") or paper.get("Year") or paper.get("publication_year")
        if not year_raw:
            # Try to extract from date field
            date_raw = paper.get("date") or paper.get("Date") or paper.get("publication_date")
            if date_raw:
                year_raw = date_raw
        
        if year_raw:
            try:
                # Extract year from date string if needed
                if isinstance(year_raw, str):
                    year_match = re.search(r"\d{4}", year_raw)
                    if year_match:
                        year = int(year_match.group(0))
                else:
                    year = int(year_raw)
            except Exception:
                year = None

        # Extract URLs
        source_url = paper.get("url") or paper.get("URL") or paper.get("link") or ""
        landing_url = paper.get("landing_url") or source_url
        pdf_url = paper.get("pdf_url") or paper.get("PDF") or paper.get("pdf_link") or None

        # Extract venue/journal
        venue = (
            paper.get("journal")
            or paper.get("Journal")
            or paper.get("venue")
            or paper.get("publication")
            or None
        )

        # Determine open access status
        open_access = bool(pdf_url) or paper.get("open_access", False)
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
        # Source format: "paperscraper_pubmed" -> "PubMed (via paperscraper)" for display
        # But we keep original source for database consistency
        return {
            "source": source,  # e.g., "paperscraper_pubmed", "paperscraper_arxiv"
            "source_url": source_url or "",
            "landing_url": landing_url or "",
            "pdf_url": pdf_url,
            "doi": _clip(doi, 255),
            "title": _clip(title, 1000),
            "abstract": _clip(abstract, 20000),
            "authors": authors_json,
            "affiliations": affiliations_json,
            "keywords": keywords_json,
            "venue": _clip(venue, 255),
            "year": year,
            "open_access": open_access,
            "oa_status": oa_status,
            "url_hash_sha1": url_hash,
        }

    except Exception as e:
        logger.error(f"Error mapping paperscraper paper to Document schema: {e}")
        return None

