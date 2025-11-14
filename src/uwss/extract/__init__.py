"""Content extraction: build text for HTML/PDF content.

Responsibilities:
- `extract_full_text`: read local files (PDF/HTML) and produce plain text,
  updating `content_path` and `content_chars` in the database.
- `scrape_full_content`: fetch landing URL and parse text for documents that
  lack local files, respecting polite headers/timeouts.

Notes:
- Keep extraction idempotent; only fill missing fields unless overwrite=true.
- Prefer robust libraries (pdfminer.six, BeautifulSoup) with sensible defaults.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from sqlalchemy import select

from ..store import create_sqlite_engine, Document
from ..store.db import create_engine_from_url
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import mimetypes

def extract_from_html(path: Path) -> str:
	try:
		html = path.read_text(encoding="utf-8", errors="ignore")
		soup = BeautifulSoup(html, "html.parser")
		# prefer title + first paragraphs
		title = (soup.title.get_text(strip=True) if soup.title else "")
		paras = " ".join(p.get_text(" ", strip=True) for p in soup.find_all("p")[:10])
		content = (title + "\n" + paras).strip()
		return content
	except Exception:
		return ""

def extract_from_pdf(path: Path) -> str:
	# lightweight fallback using text extraction if pdfminer.six not installed at runtime
	try:
		from pdfminer.high_level import extract_text
		text = extract_text(str(path)) or ""
		return text
	except Exception:
		return ""


def _first_n_chars(text: str, n: int = 500) -> str:
	if not text:
		return ""
	return (text[:n] + "…") if len(text) > n else text


def extract_text_excerpt(db_path: Path, limit: int = 20, db_url: Optional[str] = None) -> int:
	"""Stub: populate text_excerpt using existing abstract/title for quick preview.
	Later can be replaced with PDF/HTML parsing.
	"""
	engine, SessionLocal = (create_engine_from_url(db_url) if db_url else create_sqlite_engine(db_path))
	s = SessionLocal()
	try:
		count = 0
		for (doc,) in s.execute(select(Document)):
			if count >= limit:
				break
			if getattr(doc, "text_excerpt", None):
				continue
			text = (doc.abstract or "") or (doc.title or "")
			# try from local file when available
			lp = getattr(doc, "local_path", None)
			if lp and Path(lp).exists():
				p = Path(lp)
				if p.suffix.lower() == ".pdf":
					text = extract_from_pdf(p) or text
				elif p.suffix.lower() in (".html", ".htm"):
					text = extract_from_html(p) or text
			if not text:
				continue
			doc.text_excerpt = _first_n_chars(text, 600)
			s.add(doc)
			count += 1
		s.commit()
		return count
	finally:
		s.close()


def extract_full_text(db_path: Path, content_dir: Path, limit: int = 50, db_url: Optional[str] = None) -> int:
	"""Extract full text from local_path (PDF/HTML) or fallback to abstract/title.
	Write full content to content_dir as .txt and store content_path + content_chars.
	"""
	content_dir.mkdir(parents=True, exist_ok=True)
	engine, SessionLocal = (create_engine_from_url(db_url) if db_url else create_sqlite_engine(db_path))
	s = SessionLocal()
	try:
		count = 0
		for (doc,) in s.execute(select(Document)):
			if count >= limit:
				break
			if getattr(doc, "content_path", None):
				continue
			text = ""
			lp = getattr(doc, "local_path", None)
			if lp and Path(lp).exists():
				p = Path(lp)
				if p.suffix.lower() == ".pdf":
					text = extract_from_pdf(p) or ""
				elif p.suffix.lower() in (".html", ".htm"):
					text = extract_from_html(p) or ""
			if not text:
				text = (doc.abstract or "") + "\n" + (doc.title or "")
			if not text.strip():
				continue
			name_base = f"doc_{doc.id}"
			outp = content_dir / f"{name_base}.txt"
			outp.write_text(text, encoding="utf-8")
			doc.content_path = str(outp)
			doc.content_chars = len(text)
			s.add(doc)
			count += 1
		s.commit()
		return count
	finally:
		s.close()


def _session_with_retries() -> requests.Session:
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


def scrape_full_content(db_path: Path, content_dir: Path, limit: int = 50, contact_email: Optional[str] = None, overwrite: bool = False, db_url: Optional[str] = None) -> int:
	"""Fetch landing_url/source_url directly and extract full content (HTML or PDF) into content_dir.
	If the URL serves HTML: parse visible text; if PDF: parse bytes with pdfminer. Updates content_path/content_chars.
	"""
	content_dir.mkdir(parents=True, exist_ok=True)
	engine, SessionLocal = (create_engine_from_url(db_url) if db_url else create_sqlite_engine(db_path))
	s = SessionLocal()
	client = _session_with_retries()
	count = 0
	try:
		for (doc,) in s.execute(select(Document)):
			if count >= limit:
				break
			url = getattr(doc, "landing_url", None) or getattr(doc, "source_url", None)
			if not url:
				continue
			if getattr(doc, "content_path", None) and not overwrite:
				continue
			headers = {"User-Agent": f"uwss/0.1 ({contact_email})" if contact_email else "uwss/0.1"}
			try:
				r = client.get(url, headers=headers, timeout=30)
			except Exception:
				continue
			if r.status_code != 200 or not r.content:
				continue
			ctype = r.headers.get("Content-Type", "")
			text = ""
			if "pdf" in ctype.lower() or url.lower().endswith(".pdf"):
				# parse PDF bytes
				try:
					from pdfminer.high_level import extract_text_to_fp
					import io
					buf_in = io.BytesIO(r.content)
					buf_out = io.StringIO()
					extract_text_to_fp(buf_in, buf_out, output_type="text", codec=None)
					text = buf_out.getvalue()
				except Exception:
					text = ""
			else:
				# treat as text/html
				try:
					html = r.text
					soup = BeautifulSoup(html, "html.parser")
					parts = []
					if soup.title:
						parts.append(soup.title.get_text(" ", strip=True))
					for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
						parts.append(tag.get_text(" ", strip=True))
					text = "\n".join([p for p in parts if p])
				except Exception:
					text = ""
			if not text.strip():
				continue
			name_base = f"doc_{doc.id}_url"
			outp = content_dir / f"{name_base}.txt"
			try:
				outp.write_text(text, encoding="utf-8")
			except Exception:
				continue
			doc.content_path = str(outp)
			doc.content_chars = len(text)
			s.add(doc)
			count += 1
		s.commit()
		return count
	finally:
		s.close()
