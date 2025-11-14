"""Mapper: Convert Crossref API response to UWSS Document schema."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def _clip(text: Optional[str], max_len: int) -> Optional[str]:
    """Clip text to maximum length."""
    if not text:
        return None
    if len(text) <= max_len:
        return text
    return text[:max_len]


def map_crossref_to_document(
    item: dict, source: str = "crossref"
) -> Optional[dict]:
    """Map Crossref API item to UWSS Document schema.

    Args:
        item: Dictionary from Crossref API with fields like:
            - title, author, DOI, published-print, abstract, etc.
        source: Source identifier (e.g., "crossref")

    Returns:
        Dictionary with fields matching Document model, or None if mapping fails
    """
    try:
        # Extract title (required)
        title_list = item.get("title", [])
        title = title_list[0] if title_list and len(title_list) > 0 else ""
        title = title.strip()
        if not title:
            logger.debug("Skipping item with no title")
            return None

        # Extract abstract
        abstract = ""
        if "abstract" in item:
            # Crossref abstract can be in different formats
            abstract_raw = item.get("abstract")
            if isinstance(abstract_raw, str):
                abstract = abstract_raw.strip()
            elif isinstance(abstract_raw, dict):
                # Sometimes abstract is a dict with text
                abstract = abstract_raw.get("text", "").strip()
        
        # Clean HTML tags from abstract (Crossref sometimes includes JATS XML tags)
        if abstract:
            # Remove JATS XML tags (e.g., <jats:title>, <jats:p>, etc.)
            abstract = re.sub(r"<jats:[^>]*>", "", abstract)
            abstract = re.sub(r"</jats:[^>]*>", "", abstract)
            # Remove other HTML tags
            abstract = re.sub(r"<[^>]+>", "", abstract)
            # Normalize whitespace
            abstract = re.sub(r"\s+", " ", abstract).strip()

        # Extract authors
        authors = []
        authors_raw = item.get("author", [])
        if isinstance(authors_raw, list):
            for author in authors_raw:
                given = author.get("given", "")
                family = author.get("family", "")
                if given or family:
                    name = f"{given} {family}".strip()
                    if name:
                        authors.append(name)
        authors_json = json.dumps(authors) if authors else None

        # Extract DOI
        doi = item.get("DOI", "").strip() if item.get("DOI") else None

        # Extract year from published-print or published-online
        year = None
        for date_type in ["published-print", "published-online", "issued"]:
            date_parts = item.get(date_type, {}).get("date-parts", [])
            if date_parts and date_parts[0] and len(date_parts[0]) > 0:
                try:
                    year = int(date_parts[0][0])
                    break
                except (ValueError, TypeError):
                    continue

        # Extract URLs
        source_url = ""
        landing_url = ""
        pdf_url = None

        # Crossref provides links in the "link" field
        links = item.get("link", [])
        for link in links:
            if isinstance(link, dict):
                url = link.get("URL", "")
                content_type = link.get("content-type", "")
                if url:
                    if not landing_url:
                        landing_url = url
                    if content_type == "application/pdf" and not pdf_url:
                        pdf_url = url

        # If no landing URL, try to construct from DOI
        if not landing_url and doi:
            landing_url = f"https://doi.org/{doi}"

        source_url = landing_url

        # Extract venue/journal
        container_title = item.get("container-title", [])
        venue = container_title[0] if container_title and len(container_title) > 0 else None

        # Determine open access status
        open_access = item.get("is-referenced-by-count", 0) > 0  # Heuristic
        # Better: check for open access indicators
        if "license" in item:
            open_access = True
        if pdf_url:
            open_access = True

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
            "affiliations": None,  # Crossref doesn't provide affiliations in basic response
            "keywords": None,  # Can be extracted from subject field if needed
            "venue": _clip(venue, 255),
            "year": year,
            "open_access": open_access,
            "oa_status": oa_status,
            "url_hash_sha1": url_hash,
        }

    except Exception as e:
        logger.error(f"Error mapping Crossref item to document: {e}")
        return None

