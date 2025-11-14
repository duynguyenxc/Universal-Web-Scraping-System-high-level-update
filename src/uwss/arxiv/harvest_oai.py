from __future__ import annotations

import time
from datetime import datetime
from typing import Iterable, Optional, Dict, Any, List
import requests
import xml.etree.ElementTree as ET

from ..store import Document, IngestionState


ARXIV_OAI_BASE = "https://export.arxiv.org/oai2"


def _clip(text: Optional[str], max_len: int) -> Optional[str]:
    if text is None:
        return None
    try:
        s = str(text)
        return s[:max_len]
    except Exception:
        return text


def _parse_oai_record(record_el: ET.Element) -> Dict[str, Any]:
    ns = {
        "oai": "http://www.openarchives.org/OAI/2.0/",
        "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
        "dc": "http://purl.org/dc/elements/1.1/",
    }
    header = record_el.find("oai:header", ns)
    metadata = record_el.find("oai:metadata", ns)
    if metadata is None:
        return {}
    # arXiv uses oai_dc:dc; fall back to dc:dc if present
    dc = metadata.find("oai_dc:dc", ns)
    if dc is None:
        dc = metadata.find("dc:dc", ns)
    if dc is None:
        # try any child element ending with 'dc'
        for child in list(metadata):
            if child.tag.endswith("}dc"):
                dc = child
                break
    if dc is None:
        return {}

    get_all = lambda tag: [el.text.strip() for el in dc.findall(f"dc:{tag}", ns) if (el.text or "").strip()]

    identifiers = get_all("identifier")
    title_list = get_all("title")
    authors = get_all("creator")
    abstract_list = get_all("description")
    dates = get_all("date")

    title = title_list[0] if title_list else None
    abstract = abstract_list[0] if abstract_list else None

    # arXiv id and DOI extraction from identifiers
    arxiv_id: Optional[str] = None
    doi: Optional[str] = None
    landing_url: Optional[str] = None
    for ident in identifiers:
        low = ident.lower()
        if low.startswith("http://arxiv.org/abs/") or low.startswith("https://arxiv.org/abs/"):
            landing_url = ident
            arxiv_id = ident.split("/abs/")[-1]
        elif low.startswith("doi:"):
            doi = ident.split(":", 1)[-1].strip()
        elif low.startswith("http://dx.doi.org/") or low.startswith("https://doi.org/"):
            doi = ident.split("/doi.org/")[-1] if "/doi.org/" in ident else ident.split("/dx.doi.org/")[-1]

    year: Optional[int] = None
    if dates:
        try:
            year = int(dates[0][:4])
        except Exception:
            year = None

    pdf_url: Optional[str] = None
    if arxiv_id:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

    return {
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "doi": doi,
        "arxiv_id": arxiv_id,
        "landing_url": landing_url or (f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None),
        "pdf_url": pdf_url,
        "year": year,
    }


def harvest_oai_records(
    session,
    contact_email: Optional[str] = None,
    from_date: Optional[str] = None,
    until_date: Optional[str] = None,
    set_spec: Optional[str] = None,
    max_records: Optional[int] = None,
    resume: bool = False,
    throttle_sec: float = 1.0,
) -> Dict[str, Any]:
    """Harvest arXiv via OAI-PMH ListRecords and upsert into DB.

    Stores resumptionToken in IngestionState(source="arxiv_oai", checkpoint_key="resumptionToken").
    """
    headers = {
        "User-Agent": f"uwss/0.1 (+harvest; {contact_email or 'contact@unknown'})",
        "Accept": "application/xml, text/xml;q=0.9, */*;q=0.8",
    }

    # Resume token if requested
    token: Optional[str] = None
    if resume:
        st = (
            session.query(IngestionState)
            .filter(IngestionState.source == "arxiv_oai", IngestionState.checkpoint_key == "resumptionToken")
            .first()
        )
        if st and st.checkpoint_value:
            token = st.checkpoint_value

    inserted = 0
    processed = 0
    failed = 0
    pages = 0
    start_ts = time.time()

    while True:
        params = {"verb": "ListRecords"}
        if token:
            params["resumptionToken"] = token
        else:
            params["metadataPrefix"] = "oai_dc"
            if from_date:
                params["from"] = from_date
            if until_date:
                params["until"] = until_date
            if set_spec:
                params["set"] = set_spec

        resp = requests.get(ARXIV_OAI_BASE, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        ns = {"oai": "http://www.openarchives.org/OAI/2.0/"}
        recs = root.findall(".//oai:record", ns)
        pages += 1

        # Upsert each record
        for rec in recs:
            try:
                obj = _parse_oai_record(rec)
                if not obj or not (obj.get("title") or obj.get("doi")):
                    processed += 1
                    # cap by processed count too
                    if max_records and processed >= max_records:
                        break
                    continue
                # Deduplicate by arXiv ID, DOI, title
                existing = None
                if obj.get("arxiv_id"):
                    existing = session.query(Document).filter(Document.source == "arxiv", Document.source_url.like(f"%/{obj['arxiv_id']}")).first()
                if existing is None and obj.get("doi"):
                    existing = session.query(Document).filter(Document.doi == obj["doi"]).first()
                if existing is None and obj.get("title"):
                    existing = session.query(Document).filter(Document.title == obj["title"]).first()
                if existing:
                    processed += 1
                    if max_records and processed >= max_records:
                        break
                    continue
                doc = Document(
                    source_url=obj.get("landing_url") or "",
                    landing_url=obj.get("landing_url"),
                    pdf_url=obj.get("pdf_url"),
                    doi=_clip(obj.get("doi"), 255),
                    title=_clip(obj.get("title"), 1000),
                    authors=None if not obj.get("authors") else __import__("json").dumps(obj.get("authors")),
                    venue=_clip("arXiv", 255),
                    year=obj.get("year"),
                    open_access=True if obj.get("pdf_url") else False,
                    abstract=_clip(obj.get("abstract"), 20000),
                    status="metadata_only",
                    source="arxiv",
                )
                session.add(doc)
                inserted += 1
                processed += 1
            except Exception:
                failed += 1
            # Optional limit on processed
            if max_records and processed >= max_records:
                break
        session.commit()

        # Get resumptionToken
        tok_el = root.find(".//oai:resumptionToken", ns)
        next_token = tok_el.text.strip() if (tok_el is not None and (tok_el.text or "").strip()) else None
        # Save checkpoint when resume flag is on
        if resume:
            st = (
                session.query(IngestionState)
                .filter(IngestionState.source == "arxiv_oai", IngestionState.checkpoint_key == "resumptionToken")
                .first()
                or IngestionState(source="arxiv_oai", checkpoint_key="resumptionToken")
            )
            st.checkpoint_value = next_token or ""
            st.updated_at = datetime.utcnow()
            session.merge(st)
            session.commit()

        token = next_token
        if (max_records and processed >= max_records) or not token:
            break
        time.sleep(throttle_sec)

    return {
        "inserted": inserted,
        "failed": failed,
        "pages": pages,
        "elapsed_sec": round(time.time() - start_ts, 3),
        "resumed": bool(resume),
    }


