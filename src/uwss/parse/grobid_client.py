from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import time
import json
import hashlib
import requests

from ..store import Document


def _safe_filename(base: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in base)[:128]


def parse_with_grobid(
    session,
    content_dir: Path,
    limit: int = 20,
    grobid_url: str = "http://localhost:8070",
    consolidate_header: int = 1,
    consolidate_citations: int = 1,
) -> Dict[str, Any]:
    """Send local PDFs to a running GROBID service and store TEI/XML and text.

    Updates Document.content_path, content_chars, extractor='grobid'.
    """
    content_dir.mkdir(parents=True, exist_ok=True)

    q = (
        session.query(Document)
        .filter(Document.source == "arxiv")
        .filter(Document.local_path != None)
        .filter((Document.content_path == None) | (Document.content_path == ""))
        .limit(limit)
    )
    rows = q.all()

    ok = 0
    fail = 0
    for d in rows:
        pdf_path = Path(d.local_path) if d.local_path else None
        if not pdf_path or not pdf_path.exists():
            fail += 1
            continue
        # derive output file names
        base = _safe_filename((pdf_path.stem or f"doc_{d.id}"))
        out_tei = content_dir / f"{base}.tei.xml"
        out_txt = content_dir / f"{base}.text.json"
        meta_path = content_dir / f"{base}.meta.json"
        try:
            with open(pdf_path, "rb") as f:
                files = {"input": (pdf_path.name, f, "application/pdf")}
                params = {
                    "consolidateHeader": str(consolidate_header),
                    "consolidateCitations": str(consolidate_citations),
                }
                url = f"{grobid_url.rstrip('/')}/api/processFulltextDocument"
                resp = requests.post(url, files=files, data=params, timeout=120)
            if resp.status_code != 200:
                fail += 1
                continue
            tei_xml = resp.text or ""
            out_tei.write_text(tei_xml, encoding="utf-8")
            # basic plain text extraction from TEI (very light): keep as JSON for downstream
            try:
                from xml.etree import ElementTree as ET
                root = ET.fromstring(tei_xml)
                # TEI body paragraphs
                texts = [el.text or "" for el in root.findall('.//{*}body//{*}p')]
                text_joined = "\n\n".join([t.strip() for t in texts if t and t.strip()])
            except Exception:
                text_joined = ""
            payload = {
                "path": str(pdf_path),
                "tei": str(out_tei),
                "chars": len(text_joined),
                "preview": text_joined[:2000],
            }
            out_txt.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            # meta
            now = datetime.utcnow().isoformat() + "Z"
            meta = {"grobid_url": grobid_url, "status": 200, "parsed_at": now}
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

            d.content_path = str(out_tei)
            d.content_chars = len(text_joined) if text_joined else None
            d.extractor = "grobid"
            session.add(d)
            session.commit()
            ok += 1
        except Exception:
            fail += 1
            session.rollback()
    return {"attempted": len(rows), "parsed_ok": ok, "parsed_fail": fail}



