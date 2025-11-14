"""Crawl utilities: resolve publisher links, enrich Open Access, and download content.

This module centralizes all network I/O that fetches publisher pages, follows
redirects, enriches OA metadata (via Unpaywall), and downloads PDF/HTML files.

Key design points:
- Robustness: retries with exponential backoff; honors Retry-After; per-host
  throttling and jitter to avoid rate-limits.
- Idempotency: file paths and DB fields (`local_path`, `content_path`) are filled
  only if missing; repeated runs safely skip completed work.
- Deduplication: a per-run in-memory set plus a `visited_urls` registry prevents
  repeated URL inserts; URL SHA1 is stored on documents for downstream checks.
- Configurable identity: optional User-Agent rotation and optional proxies can
  be enabled through environment variables without code changes.
"""
from __future__ import annotations

import os
import json
import time
import random
from pathlib import Path
import hashlib
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from sqlalchemy import select
from datetime import datetime
import mimetypes
import re

from ..store import create_sqlite_engine, Document
from ..store.db import create_engine_from_url
from ..store.models import VisitedUrl
from bs4 import BeautifulSoup


def safe_filename(s: str) -> str:
	return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in s)[:200]


def enrich_open_access_with_unpaywall(db_path: Path, contact_email: Optional[str] = None, limit: int = 50, db_url: Optional[str] = None) -> int:
	"""Enrich documents with Open Access metadata from Unpaywall.

	Args:
		db_path: SQLite path (unused when db_url is provided).
		contact_email: Contact email recommended by Unpaywall for identification.
		limit: Maximum number of DOI entries to enrich in this run.
		db_url: Optional SQLAlchemy URL (e.g., Postgres). When provided, overrides db_path.

	Returns:
		The number of documents updated with OA information.
	"""
	"""Mark documents as open_access if Unpaywall reports OA and set source_url to best OA URL."""
	engine, SessionLocal = (create_engine_from_url(db_url) if db_url else create_sqlite_engine(db_path))
	session = SessionLocal()
	# Session with retries/backoff and Retry-After respect
	s = requests.Session()
	retry = Retry(
		total=3,
		backoff_factor=0.5,
		status_forcelist=(429, 500, 502, 503, 504),
		respect_retry_after_header=True,
		allowed_methods=("GET",),
	)
	adapter = HTTPAdapter(max_retries=retry)
	s.mount("http://", adapter)
	s.mount("https://", adapter)

	metrics = {"unpaywall_ok": 0, "unpaywall_fail": 0, "unpaywall_429_5xx": 0}
	updated = 0
	try:
		q = session.execute(select(Document).where(Document.doi != None))
		for (doc,) in q:
			if updated >= limit:
				break
			if not doc.doi:
				continue
			url = f"https://api.unpaywall.org/v2/{doc.doi}?email={contact_email or 'example@example.com'}"
			r = s.get(url, timeout=30)
			if r.status_code != 200:
				metrics["unpaywall_fail"] += 1
				if r.status_code in (429, 500, 502, 503, 504):
					metrics["unpaywall_429_5xx"] += 1
					# Honor Retry-After if present
					ra = r.headers.get("Retry-After")
					if ra:
						try:
							wait = int(ra)
						except Exception:
							wait = 0
						if wait > 0:
							time.sleep(wait)
				continue
			js = r.json()
			is_oa = bool(js.get("is_oa"))
			best = js.get("best_oa_location") or {}
			best_pdf = best.get("url_for_pdf")
			best_html = best.get("url")
			if is_oa and (best_pdf or best_html):
				doc.open_access = True
				doc.oa_status = best.get("host_type") or js.get("oa_status") or None
				# license if available
				lic = best.get("license") or js.get("license")
				if lic:
					doc.license = lic
				# fill landing/pdf fields consistently without clobbering when already set
				if best_pdf:
					doc.pdf_url = best_pdf
				if best_html and not getattr(doc, "landing_url", None):
					doc.landing_url = best_html
				# keep source_url as-is; downloader prefers pdf_url
				updated += 1
				metrics["unpaywall_ok"] += 1
		session.commit()
		# Structured metrics log
		print(json.dumps({"uwss_event": "unpaywall_enrich_summary", "updated": updated, **metrics}))
		return updated
	finally:
		session.close()


def _sha256_bytes(data: bytes) -> str:
	h = hashlib.sha256()
	h.update(data)
	return h.hexdigest()


def _get_env_user_agents() -> list[str]:
	ua_file = os.getenv("UWSS_UA_FILE")
	ua_list = []
	if ua_file and Path(ua_file).exists():
		try:
			ua_list = [ln.strip() for ln in Path(ua_file).read_text(encoding="utf-8").splitlines() if ln.strip()]
		except Exception:
			ua_list = []
	else:
		ua_csv = os.getenv("UWSS_UA_LIST", "")
		if ua_csv:
			ua_list = [x.strip() for x in ua_csv.split("|") if x.strip()]
	return ua_list


def _pick_user_agent(contact_email: Optional[str] = None) -> str:
	ua_list = _get_env_user_agents()
	if ua_list:
		return random.choice(ua_list)
	return f"uwss/0.1 ({contact_email})" if contact_email else "uwss/0.1"


def _pick_proxy() -> Optional[str]:
	# UWSS_PROXIES supports csv or file
	px_file = os.getenv("UWSS_PROXY_FILE")
	candidates: list[str] = []
	if px_file and Path(px_file).exists():
		try:
			candidates = [ln.strip() for ln in Path(px_file).read_text(encoding="utf-8").splitlines() if ln.strip()]
		except Exception:
			candidates = []
	else:
		px_csv = os.getenv("UWSS_PROXIES", "")
		if px_csv:
			candidates = [x.strip() for x in px_csv.split("|") if x.strip()]
	return random.choice(candidates) if candidates else None


def _apply_proxy(session: requests.Session, proxy_url: Optional[str]) -> None:
	if not proxy_url:
		return
	session.proxies.update({
		"http": proxy_url,
		"https": proxy_url,
	})


def download_open_links(db_path: Path, out_dir: Path, limit: int = 10, contact_email: Optional[str] = None, db_url: Optional[str] = None) -> int:
	"""Download open-access documents using known PDF or landing URLs.

	Behavior:
	- Prefers `pdf_url`; falls back to `source_url` when needed.
	- Detects file type using Content-Type, Content-Disposition, or URL suffix.
	- Writes files into `out_dir` with stable names including the document id.
	- Updates database fields: `local_path`, `status`, `mime_type`, `file_size`,
	  `checksum_sha256`, `url_hash_sha1`, and the `visited_urls` registry.

	Args:
		db_path: SQLite path (unused when db_url is provided).
		out_dir: Directory to place downloaded files.
		limit: Maximum number of downloads in this run.
		contact_email: Used for polite User-Agent identification.
		db_url: Optional SQLAlchemy URL (e.g., Postgres). When provided, overrides db_path.

	Returns:
		Number of files successfully downloaded.
	"""
	out_dir.mkdir(parents=True, exist_ok=True)
	engine, SessionLocal = (create_engine_from_url(db_url) if db_url else create_sqlite_engine(db_path))
	session = SessionLocal()
	# Build a requests session with retries/backoff for robustness
	s = requests.Session()
	retry = Retry(
		total=3,
		backoff_factor=0.5,
		status_forcelist=(429, 500, 502, 503, 504),
		respect_retry_after_header=True,
		allowed_methods=("GET",),
	)
	adapter = HTTPAdapter(max_retries=retry)
	s.mount("http://", adapter)
	s.mount("https://", adapter)
	# optional proxy
	_apply_proxy(s, _pick_proxy())

	# Observability counters
	metrics = {
		"downloads_ok": 0,
		"downloads_fail": 0,
		"status_counts": {},
		"429_5xx_count": 0,
	}

	# Track visited URLs within this run to avoid inserting duplicates in one commit
	visited_seen: set[str] = set()

	# Throttle config
	throttle_sec = float(os.getenv("UWSS_THROTTLE_SEC", "0"))
	jitter_max = float(os.getenv("UWSS_JITTER_SEC", "0.2"))
	last_request_per_host: dict[str, float] = {}
	count = 0
	try:
		# Only download documents that are open_access and missing local_path
		q = session.execute(select(Document).where((Document.open_access == True) & ((Document.local_path == None) | (Document.local_path == ""))))
		for (doc,) in q:
			if count >= limit:
				break
			# Prefer pdf_url if available; else landing/source_url
			url = getattr(doc, "pdf_url", None) or getattr(doc, "source_url", None)
			if not url:
				continue
			headers = {"User-Agent": _pick_user_agent(contact_email)}
			# Per-host throttle + jitter
			host = None
			try:
				from urllib.parse import urlparse
				host = urlparse(url).netloc
			except Exception:
				host = None
			if host:
				last = last_request_per_host.get(host)
				if last is not None and throttle_sec > 0:
					elapsed = time.time() - last
					wait = max(0.0, throttle_sec - elapsed)
					if wait > 0:
						time.sleep(wait + random.uniform(0, jitter_max))
			r = s.get(url, headers=headers, timeout=30, allow_redirects=True)
			if host:
				last_request_per_host[host] = time.time()
			# Track status metrics
			metrics["status_counts"][str(r.status_code)] = metrics["status_counts"].get(str(r.status_code), 0) + 1
			if r.status_code in (429, 500, 502, 503, 504):
				metrics["429_5xx_count"] += 1
			# Non-OK responses
			if r.status_code != 200 or not r.content:
				metrics["downloads_fail"] += 1
				# Honor Retry-After if provided
				ra = r.headers.get("Retry-After")
				if ra:
					try:
						wait = int(ra)
					except Exception:
						wait = 0
					if wait > 0:
						time.sleep(wait)
				continue
			content_type = r.headers.get("Content-Type", "")
			if not content_type:
				guess, _ = mimetypes.guess_type(url)
				content_type = guess or ""
			# detect via Content-Disposition
			cd = r.headers.get("Content-Disposition", "")
			is_pdf = ("application/pdf" in content_type.lower()) or url.lower().endswith(".pdf") or ("filename=" in cd.lower() and cd.lower().endswith(".pdf"))
			ext = ".pdf" if is_pdf else ".html"
			base = safe_filename(doc.doi or doc.title or f"doc_{doc.id}") or f"doc_{doc.id}"
			# add id suffix to avoid name collision
			name = f"{base}_id{doc.id}{ext}"
			path = out_dir / name
			with open(path, "wb") as f:
				f.write(r.content)
			doc.local_path = str(path)
			doc.status = "fetched"
			# provenance
			doc.http_status = r.status_code
			doc.file_size = path.stat().st_size if path.exists() else None
			doc.mime_type = content_type or None
			from datetime import datetime as _dt
			doc.fetched_at = _dt.utcnow()
			try:
				doc.checksum_sha256 = _sha256_bytes(r.content)
			except Exception:
				doc.checksum_sha256 = None
			# url hash for dedupe/logging
			try:
				doc.url_hash_sha1 = hashlib.sha1((url or "").encode("utf-8")).hexdigest()
			except Exception:
				doc.url_hash_sha1 = None
			# Mark URL visited in registry (set first_seen on insert); avoid duplicate inserts in same batch
			try:
				from datetime import datetime
				if url not in visited_seen:
					visited_seen.add(url)
					existing = session.get(VisitedUrl, url)
					if existing:
						existing.last_seen = datetime.utcnow()
						existing.status = str(r.status_code)
						session.add(existing)
					else:
						vu = VisitedUrl(url=url, first_seen=datetime.utcnow(), last_seen=datetime.utcnow(), status=str(r.status_code))
						session.add(vu)
			except Exception:
				pass
			count += 1
			metrics["downloads_ok"] += 1
		session.commit()
		# Structured metrics log
		print(json.dumps({"uwss_event": "download_summary", "downloaded": count, **metrics}))
		return count
	finally:
		session.close()


def _build_session() -> requests.Session:
	"""Create a requests session with sane retry/backoff defaults.

	The session honors Retry-After, retries common transient status codes, and is
	used uniformly for all outbound HTTP requests in this module.
	"""
	s = requests.Session()
	retry = Retry(
		total=3,
		backoff_factor=0.5,
		status_forcelist=(429, 500, 502, 503, 504),
		respect_retry_after_header=True,
		allowed_methods=("GET",),
	)
	adapter = HTTPAdapter(max_retries=retry)
	s.mount("http://", adapter)
	s.mount("https://", adapter)
	return s


def resolve_publisher_links(db_path: Path, limit: int = 50, contact_email: Optional[str] = None, db_url: Optional[str] = None) -> int:
	"""Follow landing pages to discover better publisher and PDF links.

	Typical flow:
	1. Start from `landing_url` or `source_url`.
	2. If on an aggregator (e.g., Semantic Scholar), follow "View via Publisher".
	3. On publisher page, detect PDF via common meta/link patterns or .pdf anchors.
	4. If only DOI is known, follow doi.org redirects to derive landing or PDF.

	Args:
		db_path: SQLite path (unused when db_url is provided).
		limit: Max number of documents to attempt in this run.
		contact_email: Used to form a polite User-Agent.
		db_url: Optional SQLAlchemy URL (e.g., Postgres). When provided, overrides db_path.

	Returns:
		Number of documents with improved landing/pdf links.
	"""
	"""Try to resolve publisher landing/PDF links starting from landing_url/source_url.
	- For Semantic Scholar pages: follow "View via Publisher" link
	- On publisher pages: detect PDF via common selectors and meta tags
	- If only DOI is present or pdf_url is a doi.org URL: follow redirects to get final landing/PDF
	"""
	engine, SessionLocal = (create_engine_from_url(db_url) if db_url else create_sqlite_engine(db_path))
	session = SessionLocal()
	client = _build_session()
	updated = 0
	updated_pdf = 0
	try:
		q = session.execute(select(Document))
		for (doc,) in q:
			if updated >= limit:
				break
			landing = getattr(doc, "landing_url", None) or getattr(doc, "source_url", None)
			if not landing:
				continue
			# Skip if already has a clear PDF (non-doi)
			pdf_url = getattr(doc, "pdf_url", None)
			if pdf_url and ("doi.org" not in pdf_url.lower()):
				continue
			headers = {"User-Agent": _pick_user_agent(contact_email)}
			try:
				r = client.get(landing, headers=headers, timeout=20, allow_redirects=True)
			except Exception:
				continue
			if r.status_code != 200:
				continue
			final_url = r.url or landing
			html = r.text or ""
			# handle meta refresh
			try:
				soup0 = BeautifulSoup(html, "html.parser")
				mrf = soup0.find("meta", attrs={"http-equiv": re.compile("refresh", re.I)})
				if mrf and mrf.get("content"):
					m = re.search(r"url=([^;]+)", mrf.get("content"), flags=re.I)
					if m:
						from urllib.parse import urljoin
						next_url = urljoin(final_url, m.group(1).strip())
						r1 = client.get(next_url, headers=headers, timeout=20, allow_redirects=True)
						if r1.status_code == 200:
							final_url = r1.url or next_url
							html = r1.text or html
			except Exception:
				pass
			# If this is a Semantic Scholar page, find View via Publisher link
			if "semanticscholar.org" in final_url.lower():
				try:
					soup = BeautifulSoup(html, "html.parser")
					publisher_a = None
					for a in soup.find_all("a"):
						text = (a.get_text(" ", strip=True) or "").lower()
						if "view via publisher" in text or "publisher" in text:
							publisher_a = a
							break
					if publisher_a and publisher_a.get("href"):
						from urllib.parse import urljoin
						landing2 = urljoin(final_url, publisher_a.get("href"))
						# follow publisher page
						try:
							r2 = client.get(landing2, headers=headers, timeout=20, allow_redirects=True)
						except Exception:
							landing2 = None
						if r2 is not None and r2.status_code == 200:
							final_url = r2.url or landing2 or final_url
							html = r2.text or html
							doc.landing_url = final_url
							session.add(doc)
							updated += 1
				except Exception:
					pass

			# On final page, try to detect PDF
			try:
				soup = BeautifulSoup(html, "html.parser")
				# meta citation_pdf_url
				meta_pdf = soup.find("meta", attrs={"name": "citation_pdf_url"})
				if meta_pdf and meta_pdf.get("content"):
					doc.pdf_url = meta_pdf["content"].strip()
					session.add(doc)
					updated_pdf += 1
					continue
				# link rel alternate type application/pdf
				lnk = soup.find("link", attrs={"rel": "alternate", "type": "application/pdf"})
				if lnk and lnk.get("href"):
					from urllib.parse import urljoin
					doc.pdf_url = urljoin(final_url, lnk["href"].strip())
					session.add(doc)
					updated_pdf += 1
					continue
				# any anchor to *.pdf or labeled pdf
				for a in soup.find_all("a"):
					href = (a.get("href") or "").strip()
					txt = (a.get_text(" ", strip=True) or "").lower()
					if href.lower().endswith(".pdf") or "pdf" in txt:
						from urllib.parse import urljoin
						doc.pdf_url = urljoin(final_url, href)
						session.add(doc)
						updated_pdf += 1
						break
			except Exception:
				pass

			# If pdf_url is a DOI link or still empty but DOI present, try doi.org redirect
			doi = getattr(doc, "doi", None)
			if (not getattr(doc, "pdf_url", None)) and doi:
				try:
					rh = client.get(f"https://doi.org/{doi}", headers=headers, timeout=20, allow_redirects=True)
					if rh.status_code == 200:
						ct = rh.headers.get("Content-Type", "").lower()
						if "application/pdf" in ct or (rh.url or "").lower().endswith(".pdf"):
							doc.pdf_url = rh.url
							updated_pdf += 1
						else:
							doc.landing_url = rh.url or doc.landing_url
						session.add(doc)
				except Exception:
					pass

			session.commit()
			# mark landing visited
			try:
				from datetime import datetime
				existing = session.get(VisitedUrl, final_url)
				if existing:
					existing.last_seen = datetime.utcnow()
					session.add(existing)
				else:
					vu = VisitedUrl(url=final_url, first_seen=datetime.utcnow(), last_seen=datetime.utcnow(), status="200")
					session.add(vu)
			except Exception:
				pass
		# simple structured log to stdout
		try:
			print(json.dumps({"uwss_event": "resolve_publisher_done_detail", "updated_landing": updated, "updated_pdf": updated_pdf}))
		except Exception:
			pass
		return max(updated, updated_pdf)
	finally:
		session.close()


