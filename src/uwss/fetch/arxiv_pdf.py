from __future__ import annotations

import os
import time
import random
import hashlib
from datetime import datetime, timedelta
import re
from pathlib import Path
from typing import Optional, Dict, Any

import requests

from ..store import Document, VisitedUrl
from sqlalchemy import or_, and_
from ..utils.http import session_with_retries
from ..constants import PDF_UA


def _safe_filename(base: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in base)[:128]


def _guess_arxiv_id(landing_url: Optional[str], pdf_url: Optional[str]) -> Optional[str]:
    for u in (pdf_url, landing_url):
        if not u:
            continue
        if "/pdf/" in u:
            # https://arxiv.org/pdf/xxxx.pdf
            part = u.split("/pdf/")[-1]
            return part.replace(".pdf", "")
        if "/abs/" in u:
            part = u.split("/abs/")[-1]
            return part
    return None


_ARXIV_VERSION_RE = re.compile(r"^(?P<base>\d{4}\.\d{4,5})(?P<ver>v\d+)?$")


def _split_arxiv_id_version(arxiv_id: str) -> tuple[str, Optional[str]]:
    """Split arXiv id into base and version suffix if present.

    Examples:
    - 2101.01234v2 -> ("2101.01234", "v2")
    - 2101.01234 -> ("2101.01234", None)
    """
    m = _ARXIV_VERSION_RE.match(arxiv_id or "")
    if not m:
        return arxiv_id, None
    return m.group("base"), m.group("ver")


def _candidate_pdf_urls(landing_url: Optional[str], pdf_url: Optional[str]) -> list[str]:
    """Build ordered candidate PDF URLs: pinned (if versioned) → latest.

    Prefer version-pinned URL for reproducibility, then fall back to latest.
    """
    arxiv_id = _guess_arxiv_id(landing_url, pdf_url)
    if not arxiv_id:
        return [u for u in [pdf_url] if u]
    base, ver = _split_arxiv_id_version(arxiv_id)
    candidates: list[str] = []
    if ver:  # pinned first
        candidates.append(f"https://arxiv.org/pdf/{base}{ver}.pdf")
    # latest as fallback
    candidates.append(f"https://arxiv.org/pdf/{base}.pdf")
    # if an explicit pdf_url exists and is not already in the list, try it last
    if pdf_url and pdf_url not in candidates:
        candidates.append(pdf_url)
    return candidates


def fetch_arxiv_pdfs(
    session,
    out_dir: Path,
    limit: int = 50,
    contact_email: Optional[str] = None,
    throttle_sec: float = 1.0,
    jitter_sec: float = 0.5,
    max_mb: float = 60.0,
    dry_run: bool = False,
    since_days: Optional[int] = None,
    ids: Optional[set[int]] = None,
) -> Dict[str, Any]:
    """Download canonical arXiv PDFs for arXiv-sourced documents.

    - Respects polite UA and pacing.
    - Writes to out_dir; updates Document.local_path, http_status, file_size, fetched_at, mime_type, status.
    - Records VisitedUrl for provenance.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    ua = f"{PDF_UA}; {contact_email or 'contact@unknown'}"
    headers = {"User-Agent": ua, "Accept": "application/pdf, */*;q=0.8", "Connection": "close"}
    http = session_with_retries(user_agent=ua)

    # If caller supplied an IDs set but it's empty, do NOT fallback to all rows.
    # Return a zero-attempt metrics block so that PDF downloads always reflect the export gate.
    if ids is not None and len(ids) == 0:
        return {
            "attempted": 0,
            "downloaded": 0,
            "failed": 0,
            "not_found_404": 0,
            "forbidden_403": 0,
            "errors_5xx": 0,
            "timeouts": 0,
            "too_large": 0,
            "retries": 0,
            "bytes_downloaded": 0,
            "latency_ms": {"p50": None, "p95": None, "max": None},
            "items": [],
        }

    q = session.query(Document).filter(Document.source == "arxiv").filter(Document.pdf_url != None)
    if ids is not None:
        try:
            q = q.filter(Document.id.in_(list(ids)))
        except Exception:
            # If the provided IDs cannot be applied, treat as zero-attempts rather than silently falling back.
            return {
                "attempted": 0,
                "downloaded": 0,
                "failed": 0,
                "not_found_404": 0,
                "forbidden_403": 0,
                "errors_5xx": 0,
                "timeouts": 0,
                "too_large": 0,
                "retries": 0,
                "bytes_downloaded": 0,
                "latency_ms": {"p50": None, "p95": None, "max": None},
                "items": [],
            }
    if since_days is not None and since_days >= 0:
        cutoff = datetime.utcnow() - timedelta(days=since_days)
        q = q.filter(or_(Document.local_path == None, Document.local_path == "", Document.fetched_at == None, Document.fetched_at < cutoff))
    else:
        q = q.filter(or_(Document.local_path == None, Document.local_path == ""))
    q = q.limit(limit)
    rows = q.all()

    downloaded = 0
    failed = 0
    not_found_404 = 0
    forbidden_403 = 0
    errors_5xx = 0
    timeouts = 0
    too_large = 0
    retries_total = 0
    bytes_downloaded = 0
    latencies_ms: list[int] = []
    downloaded_items: list[Dict[str, Any]] = []
    for d in rows:
        cand_urls = _candidate_pdf_urls(d.landing_url, d.pdf_url)
        if not cand_urls:
            continue
        # build filename
        arxiv_id = _guess_arxiv_id(d.landing_url, d.pdf_url) or hashlib.sha1((d.pdf_url or d.source_url or str(d.id)).encode("utf-8")).hexdigest()[:12]
        fname = _safe_filename(f"arxiv_{arxiv_id}.pdf")
        fpath = out_dir / fname
        meta_path = out_dir / (fname.replace(".pdf", ".meta.json"))
        # skip if already exists
        if fpath.exists():
            d.local_path = str(fpath)
            d.status = "fetched"
            d.fetched_at = datetime.utcnow()
            session.add(d)
            downloaded += 1
            continue
        # Try candidates in order (pinned → latest → explicit pdf_url)
        chosen_url: Optional[str] = None
        head: Optional[requests.Response] = None
        # HEAD size cap & dry-run, iterate until acceptable candidate
        for url_try in cand_urls:
            try:
                head = http.head(url_try, headers=headers, allow_redirects=True)
                # record visited for HEAD
                try:
                    existing = session.get(VisitedUrl, url_try)
                    now = datetime.utcnow()
                    if existing:
                        existing.last_seen = now
                        existing.status = str(head.status_code)
                        session.add(existing)
                    else:
                        vu = VisitedUrl(url=url_try, first_seen=now, last_seen=now, status=str(head.status_code))
                        session.add(vu)
                    session.flush()
                except Exception:
                    pass
                cl = head.headers.get("Content-Length")
                if cl and max_mb is not None:
                    try:
                        if int(cl) > int(max_mb * 1024 * 1024):
                            # too large for this candidate; try next
                            continue
                    except Exception:
                        pass
                # if HEAD indicates not found/forbidden, try next candidate
                if head.status_code in (403, 404):
                    continue
                chosen_url = url_try
                break
            except Exception:
                # network issues: fall through to try next or eventually GET first candidate
                continue
        # If dry-run, mark and continue once a candidate was considered
        if dry_run:
            d.pdf_status = "dry_run"
            d.pdf_fetched_at = datetime.utcnow()
            session.add(d)
            session.commit()
            time.sleep(throttle_sec + random.random() * jitter_sec)
            continue
        # If none chosen from HEAD phase, default to first candidate
        url = chosen_url or cand_urls[0]
        # If HEAD deemed too large for selected candidate, record and skip
        try:
            if head is not None:
                cl = head.headers.get("Content-Length")
                if cl and max_mb is not None and int(cl) > int(max_mb * 1024 * 1024):
                    d.pdf_status = "too_large"
                    d.pdf_fetched_at = datetime.utcnow()
                    too_large += 1
                    session.add(d)
                    session.commit()
                    # write meta sidecar quickly
                    meta_path = out_dir / (fname.replace(".pdf", ".meta.json"))
                    try:
                        import json
                        authors_val = None
                        try:
                            import json as _json
                            if isinstance(d.authors, str):
                                a = _json.loads(d.authors)
                                if isinstance(a, list):
                                    authors_val = a
                        except Exception:
                            authors_val = None
                        if authors_val is None and isinstance(d.authors, str):
                            parts = [p.strip() for p in re.split(r"[;,]", d.authors) if p.strip()]
                            authors_val = parts or None
                        meta = {
                            "document_id": int(d.id) if d.id is not None else None,
                            "source": d.source or "arxiv",
                            "arxiv_id": _guess_arxiv_id(d.landing_url, d.pdf_url),
                            "doi": d.doi,
                            "title": d.title,
                            "authors": authors_val,
                            "abstract": d.abstract,
                            "year": int(d.year) if d.year is not None else None,
                            "topic": d.topic,
                            "local_path": str(fpath),
                            "url_used": url,
                            "status": int(head.status_code) if head is not None else None,
                            "content_length": int(cl) if cl else None,
                            "too_large": True,
                            "cap_mb": max_mb,
                            "http_status": int(head.status_code) if head is not None else None,
                            "pdf_status": d.pdf_status,
                            "pdf_fetched_at": d.pdf_fetched_at.isoformat() + "Z" if d.pdf_fetched_at else None,
                            "s3_key": None,
                        }
                        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
                    except Exception:
                        pass
                    time.sleep(throttle_sec + random.random() * jitter_sec)
                    continue
        except Exception:
            pass
            if cl and max_mb is not None:
                try:
                    if int(cl) > int(max_mb * 1024 * 1024):
                        d.pdf_status = "too_large"
                        d.pdf_fetched_at = datetime.utcnow()
                        too_large += 1
                        session.add(d)
                        session.commit()
                        # write meta sidecar quickly
                        meta_path = out_dir / (fname.replace(".pdf", ".meta.json"))
                        try:
                            import json
                            authors_val = None
                            try:
                                import json as _json
                                if isinstance(d.authors, str):
                                    a = _json.loads(d.authors)
                                    if isinstance(a, list):
                                        authors_val = a
                            except Exception:
                                authors_val = None
                            if authors_val is None and isinstance(d.authors, str):
                                parts = [p.strip() for p in re.split(r"[;,]", d.authors) if p.strip()]
                                authors_val = parts or None
                            meta = {
                                "document_id": int(d.id) if d.id is not None else None,
                                "source": d.source or "arxiv",
                                "arxiv_id": _guess_arxiv_id(d.landing_url, d.pdf_url),
                                "doi": d.doi,
                                "title": d.title,
                                "authors": authors_val,
                                "abstract": d.abstract,
                                "year": int(d.year) if d.year is not None else None,
                                "topic": d.topic,
                                "local_path": str(fpath),
                                "url_used": url,
                                "status": int(head.status_code) if head is not None else None,
                                "content_length": int(cl) if cl else None,
                                "too_large": True,
                                "cap_mb": max_mb,
                                "http_status": int(head.status_code) if head is not None else None,
                                "pdf_status": d.pdf_status,
                                "pdf_fetched_at": d.pdf_fetched_at.isoformat() + "Z" if d.pdf_fetched_at else None,
                                "s3_key": None,
                            }
                            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
                        except Exception:
                            pass
                        # skip download entirely
                        # pacing
                        time.sleep(throttle_sec + random.random() * jitter_sec)
                        continue
                except Exception:
                    pass
            if dry_run:
                d.pdf_status = "dry_run"
                d.pdf_fetched_at = datetime.utcnow()
                session.add(d)
                session.commit()
                time.sleep(throttle_sec + random.random() * jitter_sec)
                continue
        except Exception:
            # ignore head errors; proceed with GET/retries below
            pass

        # retry for transient errors
        attempt = 0
        max_retries = 3
        start_ts = time.time()
        while True:
            attempt += 1
            try:
                resp = http.get(url, headers=headers, stream=True)
                d.http_status = resp.status_code
                ct = (resp.headers.get("Content-Type") or "").lower()
                if resp.status_code == 200 and ct.startswith("application/pdf"):
                    tmp_path = fpath.with_suffix(".part")
                    sha = hashlib.sha256()
                    total_bytes = 0
                    with open(tmp_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=1024 * 64):
                            if chunk:
                                f.write(chunk)
                                sha.update(chunk)
                                total_bytes += len(chunk)
                    os.replace(tmp_path, fpath)
                    checksum = sha.hexdigest()
                    d.local_path = str(fpath)
                    d.status = "fetched"
                    d.pdf_status = "ok"
                    d.mime_type = resp.headers.get("Content-Type")
                    d.file_size = total_bytes
                    d.checksum_sha256 = checksum
                    now = datetime.utcnow()
                    d.fetched_at = now
                    d.pdf_fetched_at = now
                    downloaded += 1
                    bytes_downloaded += total_bytes
                    # write enriched meta.json (identification + fetch provenance)
                    try:
                        import json
                        # attempt to normalize authors field to a list
                        authors_val = None
                        try:
                            import json as _json
                            if isinstance(d.authors, str):
                                a = _json.loads(d.authors)
                                if isinstance(a, list):
                                    authors_val = a
                        except Exception:
                            authors_val = None
                        if authors_val is None and isinstance(d.authors, str):
                            # fallback split by ';' or ','
                            parts = [p.strip() for p in re.split(r"[;,]", d.authors) if p.strip()]
                            authors_val = parts or None
                        meta = {
                            # identification
                            "document_id": int(d.id) if d.id is not None else None,
                            "source": d.source or "arxiv",
                            "arxiv_id": _guess_arxiv_id(d.landing_url, d.pdf_url),
                            "doi": d.doi,
                            "title": d.title,
                            "authors": authors_val,
                            "abstract": d.abstract,
                            "year": int(d.year) if d.year is not None else None,
                            "topic": d.topic,
                            # file + fetch provenance
                            "local_path": str(fpath),
                            "url_used": url,
                            "status": resp.status_code,
                            "etag": resp.headers.get("ETag"),
                            "last_modified": resp.headers.get("Last-Modified"),
                            "content_type": resp.headers.get("Content-Type"),
                            "sha256": checksum,
                            "file_size": total_bytes,
                            "http_status": int(resp.status_code),
                            "pdf_status": d.pdf_status,
                            "pdf_fetched_at": d.pdf_fetched_at.isoformat() + "Z" if d.pdf_fetched_at else None,
                            "fetched_at": d.fetched_at.isoformat() + "Z",
                            # optional placeholders (to be filled after S3 upload)
                            "s3_key": None,
                        }
                        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
                    except Exception:
                        pass
                    # collect item for run manifest
                    try:
                        downloaded_items.append({
                            "id": d.id,
                            "title": d.title,
                            "arxiv_id": _guess_arxiv_id(d.landing_url, d.pdf_url),
                            "local_path": str(fpath),
                            "pdf_url_used": url,
                            "file_size": total_bytes,
                            "sha256": checksum,
                            "fetched_at": d.fetched_at.isoformat() + "Z",
                        })
                    except Exception:
                        pass
                else:
                    failed += 1
                    if resp.status_code == 404:
                        not_found_404 += 1
                    elif resp.status_code == 403:
                        forbidden_403 += 1
                    elif 500 <= resp.status_code < 600:
                        errors_5xx += 1
                    d.status = "fetch_failed"
                    d.pdf_status = "error" if 500 <= resp.status_code < 600 else ("forbidden" if resp.status_code == 403 else ("not_found" if resp.status_code == 404 else "error"))
                # visited url (GET)
                try:
                    existing = session.get(VisitedUrl, url)
                    now = datetime.utcnow()
                    if existing:
                        existing.last_seen = now
                        existing.status = str(resp.status_code)
                        session.add(existing)
                    else:
                        vu = VisitedUrl(url=url, first_seen=now, last_seen=now, status=str(resp.status_code))
                        session.add(vu)
                    session.flush()
                except Exception:
                    pass
            except requests.Timeout:
                timeouts += 1
                failed += 1
                d.status = "fetch_failed"
                d.pdf_status = "timeout"
            except Exception:
                failed += 1
                d.status = "fetch_failed"
                d.pdf_status = "error"
            finally:
                latency_ms = int((time.time() - start_ts) * 1000)
                latencies_ms.append(latency_ms)
                session.add(d)
                session.commit()
            if d.status == "fetched":
                break
            if attempt <= max_retries and (d.http_status in (429,) or (d.http_status and 500 <= d.http_status < 600)):
                retries_total += 1
                time.sleep(throttle_sec + random.random() * jitter_sec)
                continue
            break
        # pacing per attempt group
        time.sleep(throttle_sec + random.random() * jitter_sec)

    lat_sorted = sorted(latencies_ms)
    def pct(p: float):
        if not lat_sorted:
            return None
        k = int(max(0, min(len(lat_sorted) - 1, round(p * (len(lat_sorted) - 1)))))
        return lat_sorted[k]
    return {
        "attempted": len(rows),
        "downloaded": downloaded,
        "failed": failed,
        "not_found_404": not_found_404,
        "forbidden_403": forbidden_403,
        "errors_5xx": errors_5xx,
        "timeouts": timeouts,
        "too_large": too_large,
        "retries": retries_total,
        "bytes_downloaded": bytes_downloaded,
        "latency_ms": {"p50": pct(0.5), "p95": pct(0.95), "max": (max(lat_sorted) if lat_sorted else None)},
        "items": downloaded_items,
    }


