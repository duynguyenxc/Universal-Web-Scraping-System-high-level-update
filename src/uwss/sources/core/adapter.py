"""CORE adapter: Discovers papers via OAI-PMH protocol.

Key features:
1. OAI-PMH endpoint: https://core.ac.uk/oai
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

# CORE OAI-PMH endpoint
CORE_OAI_BASE = "https://core.ac.uk/oai"


def discover_core(
    max_records: Optional[int] = None,
    from_date: Optional[str] = None,
    until_date: Optional[str] = None,
    throttle_sec: float = 1.0,
) -> Iterator[dict]:
    """Discover CORE papers via OAI-PMH.
    
    Args:
        max_records: Maximum number of records to discover
        from_date: Start date (YYYY-MM-DD format)
        until_date: End date (YYYY-MM-DD format)
        throttle_sec: Delay between requests (seconds, default 1.0)
        
    Yields:
        Dictionary with metadata mapped to Document schema fields
        
    Notes:
        - CORE is an open repository aggregator
        - Uses OAI-PMH protocol (same as arXiv)
        - Polite rate limiting recommended (1 req/sec)
    """
    count = 0
    
    logger.info(f"Starting CORE discovery (OAI-PMH: {CORE_OAI_BASE})")
    
    try:
        for oai_record in iter_oai_dc(
            base_url=CORE_OAI_BASE,
            from_date=from_date,
            until_date=until_date,
            set_spec=None,  # CORE doesn't use sets
            resume_token=None,
            throttle_sec=throttle_sec,
        ):
            if max_records is not None and count >= max_records:
                break
            
            # Map OAI-PMH record to Document schema
            mapped = _map_oai_to_document_schema(oai_record, source="core")
            if mapped:
                yield mapped
                count += 1
                
                if count % 10 == 0:
                    logger.debug(f"CORE: discovered {count} records...")
    
    except Exception as e:
        logger.error(f"Error during CORE discovery: {e}")
        raise
    
    logger.info(f"CORE discovery complete: {count} records")


def _map_oai_to_document_schema(oai_record: dict, source: str = "core") -> Optional[dict]:
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
        # CORE is an open repository, so assume open access
        oa_status = "open" if pdf_url else "abstract_only"
        
        # Generate URL hash for deduplication
        import hashlib
        url_hash = hashlib.sha1(source_url.encode()).hexdigest() if source_url else None
        
        return {
            "source": source,
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


