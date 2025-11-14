"""DOAJ adapter: Discovers papers via OAI-PMH protocol.

Key features:
1. OAI-PMH endpoint: https://doaj.org/oai
2. Uses generic OAI-PMH adapter (iter_oai_dc)
3. Maps to universal Document schema
4. Polite rate limiting (1 req/sec recommended)
"""

from __future__ import annotations

import json
import logging
from typing import Iterator, Optional

from ...discovery.oai import iter_oai_dc
from ...store.models import Document

logger = logging.getLogger(__name__)

# DOAJ OAI-PMH endpoints (separate for articles and journals)
DOAJ_ARTICLE_ENDPOINT = "https://doaj.org/oai.article"
DOAJ_JOURNAL_ENDPOINT = "https://doaj.org/oai.journal"


def discover_doaj(
    max_records: Optional[int] = None,
    from_date: Optional[str] = None,
    until_date: Optional[str] = None,
    throttle_sec: float = 1.0,
    include_journals: bool = True,
    include_articles: bool = True,
) -> Iterator[dict]:
    """Discover DOAJ papers via OAI-PMH.
    
    Args:
        max_records: Maximum number of records to discover (total across both types)
        from_date: Start date (YYYY-MM-DD format)
        until_date: End date (YYYY-MM-DD format)
        throttle_sec: Delay between requests (seconds, default 1.0)
        include_journals: Whether to include journals (default: True)
        include_articles: Whether to include articles (default: True)
        
    Yields:
        Dictionary with metadata mapped to Document schema fields
        
    Notes:
        - DOAJ provides separate endpoints for articles and journals
        - Articles endpoint: https://doaj.org/oai.article
        - Journals endpoint: https://doaj.org/oai.journal
        - Polite rate limiting recommended (1 req/sec)
    """
    count = 0
    
    logger.info(f"Starting DOAJ discovery (articles={include_articles}, journals={include_journals})")
    
    # Discover articles
    if include_articles:
        try:
            logger.info(f"Discovering DOAJ articles from {DOAJ_ARTICLE_ENDPOINT}")
            for oai_record in iter_oai_dc(
                base_url=DOAJ_ARTICLE_ENDPOINT,
                from_date=from_date,
                until_date=until_date,
                set_spec=None,
                resume_token=None,
                throttle_sec=throttle_sec,
            ):
                if max_records is not None and count >= max_records:
                    break
                
                # Map OAI-PMH record to Document schema
                mapped = _map_oai_to_document_schema(oai_record, source="doaj", record_type="article")
                if mapped:
                    yield mapped
                    count += 1
                    
                    if count % 10 == 0:
                        logger.debug(f"DOAJ: discovered {count} records...")
        except Exception as e:
            logger.error(f"Error during DOAJ articles discovery: {e}")
            # Continue with journals even if articles fail
    
    # Discover journals
    if include_journals and (max_records is None or count < max_records):
        try:
            logger.info(f"Discovering DOAJ journals from {DOAJ_JOURNAL_ENDPOINT}")
            for oai_record in iter_oai_dc(
                base_url=DOAJ_JOURNAL_ENDPOINT,
                from_date=from_date,
                until_date=until_date,
                set_spec=None,
                resume_token=None,
                throttle_sec=throttle_sec,
            ):
                if max_records is not None and count >= max_records:
                    break
                
                # Map OAI-PMH record to Document schema
                mapped = _map_oai_to_document_schema(oai_record, source="doaj", record_type="journal")
                if mapped:
                    yield mapped
                    count += 1
                    
                    if count % 10 == 0:
                        logger.debug(f"DOAJ: discovered {count} records...")
        except Exception as e:
            logger.error(f"Error during DOAJ journals discovery: {e}")
            raise
    
    logger.info(f"DOAJ discovery complete: {count} records")


def _map_oai_to_document_schema(oai_record: dict, source: str = "doaj", record_type: str = "article") -> Optional[dict]:
    """Map OAI-PMH record to universal Document schema.
    
    Args:
        oai_record: Dictionary from iter_oai_dc() with fields:
            - title, authors (list), abstract, doi, source_url, pdf_url, year
        source: Source identifier ("core" or "doaj")
        
    Returns:
        Dictionary with fields matching Document model, or None if mapping fails
    """
    try:
        title = oai_record.get("title", "").strip()
        if not title:
            return None
        
        # Authors (already a list from OAI-PMH)
        authors = oai_record.get("authors", [])
        authors_json = json.dumps(authors) if authors else None
        
        # Abstract
        abstract = oai_record.get("abstract", "").strip() if oai_record.get("abstract") else None
        
        # DOI
        doi = oai_record.get("doi")
        if doi:
            # Normalize DOI (remove doi: prefix if present)
            doi = doi.replace("doi:", "").strip().lower()
        
        # Source URL
        source_url = oai_record.get("source_url", "")
        if not source_url and doi:
            source_url = f"https://doi.org/{doi}"
        
        # PDF URL (may not be present in OAI-PMH, but check)
        pdf_url = oai_record.get("pdf_url")
        
        # Year
        year = oai_record.get("year")
        
        # Open access status
        # DOAJ is open access only, so assume open access
        oa_status = "open" if pdf_url else "abstract_only"
        
        # Generate URL hash for deduplication
        import hashlib
        url_hash = hashlib.sha1(source_url.encode()).hexdigest() if source_url else None
        
        # Add record type to source for identification
        source_with_type = f"{source}_{record_type}"
        
        return {
            "source": source_with_type,
            "source_url": source_url or "",
            "landing_url": source_url or "",
            "title": title,
            "abstract": abstract,
            "authors": authors_json,
            "affiliations": None,  # OAI-PMH oai_dc doesn't provide affiliations
            "keywords": None,  # OAI-PMH oai_dc doesn't provide keywords
            "doi": doi,
            "year": year,
            "oa_status": oa_status,
            "pdf_url": pdf_url,
            "url_hash_sha1": url_hash,
        }
        
    except Exception as e:
        logger.error(f"Error mapping OAI record to schema: {e}")
        return None

