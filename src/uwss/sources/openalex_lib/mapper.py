"""Mapper: Convert OpenAlex API response to UWSS Document schema."""

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


def map_openalex_to_document(
    work: dict, source: str = "openalex"
) -> Optional[dict]:
    """Map OpenAlex work to UWSS Document schema.

    Args:
        work: Dictionary from OpenAlex API with fields like:
            - title, authors, doi, publication_date, abstract, etc.
        source: Source identifier (e.g., "openalex")

    Returns:
        Dictionary with fields matching Document model, or None if mapping fails
    """
    try:
        # Extract title (required)
        title = work.get("title", "").strip()
        if not title:
            logger.debug("Skipping work with no title")
            return None

        # Extract abstract
        # OpenAlex doesn't provide abstracts in basic response
        # Need to fetch full work details for abstract
        abstract = ""
        if "abstract" in work:
            abstract_raw = work.get("abstract")
            if isinstance(abstract_raw, str):
                abstract = abstract_raw.strip()
            elif isinstance(abstract_raw, dict):
                abstract = abstract_raw.get("text", "").strip()

        # Extract authors
        authors = []
        authorships = work.get("authorships", [])
        if isinstance(authorships, list):
            for authorship in authorships:
                author = authorship.get("author", {})
                if author:
                    display_name = author.get("display_name", "")
                    if display_name:
                        authors.append(display_name)
        authors_json = json.dumps(authors) if authors else None

        # Extract DOI
        doi = None
        dois = work.get("doi", "")
        if dois:
            # OpenAlex returns DOI as URL, extract just the DOI part
            if isinstance(dois, str):
                if dois.startswith("https://doi.org/"):
                    doi = dois.replace("https://doi.org/", "")
                else:
                    doi = dois.strip()
            elif isinstance(dois, dict):
                doi = dois.get("value", "").strip()

        # Extract year from publication_date
        year = None
        pub_date = work.get("publication_date")
        if pub_date:
            try:
                # OpenAlex date format: YYYY-MM-DD
                year = int(pub_date.split("-")[0])
            except (ValueError, TypeError):
                pass

        # Extract URLs
        landing_url = work.get("primary_location", {}).get("landing_page_url", "")
        pdf_url = work.get("primary_location", {}).get("pdf_url")
        
        # Also check open_access field
        open_access_info = work.get("open_access", {})
        is_oa = open_access_info.get("is_oa", False)
        
        if not pdf_url and is_oa:
            # Try to get PDF from locations
            locations = work.get("locations", [])
            for location in locations:
                if location.get("pdf_url"):
                    pdf_url = location.get("pdf_url")
                    break

        source_url = landing_url or (f"https://doi.org/{doi}" if doi else "")

        # Extract venue/journal
        venue = None
        primary_location = work.get("primary_location", {})
        source_info = primary_location.get("source", {})
        if source_info:
            venue = source_info.get("display_name") or source_info.get("name")

        # Determine open access status
        open_access = is_oa or bool(pdf_url)
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
            "affiliations": None,  # Can be extracted from authorships if needed
            "keywords": None,  # OpenAlex has concepts, but not keywords
            "venue": _clip(venue, 255),
            "year": year,
            "open_access": open_access,
            "oa_status": oa_status,
            "url_hash_sha1": url_hash,
        }

    except Exception as e:
        logger.error(f"Error mapping OpenAlex work to document: {e}")
        return None

