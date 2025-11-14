from __future__ import annotations

from pathlib import Path
from typing import Optional, Literal
import os

import boto3
from botocore.config import Config as BotoConfig

from .store import create_sqlite_engine, Document
from sqlalchemy import select


def upload_files_to_s3(
	db_path: Path,
	files_dir: Path,
	bucket: str,
	prefix: str = "uwss/",
	region: Optional[str] = None,
	*,
	include_sidecars: bool = False,
	include_docjson: bool = False,
	include_content: bool = False,
	layout: Literal["flat", "by-id"] = "flat",
) -> int:
	"""
	Upload downloaded files referenced by Document.local_path to S3.
	Skips files that are missing locally. Uses key: prefix + basename(local_path).
	"""
	s3 = boto3.client("s3", region_name=region, config=BotoConfig(retries={"max_attempts": 3, "mode": "standard"}))
	engine, SessionLocal = create_sqlite_engine(db_path)
	s = SessionLocal()
	count = 0
	try:
		q = s.execute(select(Document).where((Document.local_path != None) & (Document.local_path != "")))
		for (doc,) in q:
			p = Path(doc.local_path)
			if not p.is_absolute():
				p = files_dir / p
			if not p.exists():
				continue
			# derive arxiv id (best effort) for metadata
			arxiv_id = None
			try:
				from .fetch.arxiv_pdf import _guess_arxiv_id
				arxiv_id = _guess_arxiv_id(getattr(doc, "landing_url", None), getattr(doc, "pdf_url", None))
			except Exception:
				arxiv_id = None

			# choose key layout
			if layout == "by-id":
				base_dir = prefix.rstrip("/") + f"/by-id/{int(doc.id)}/"
				pdf_key = base_dir + "pdf.pdf"
				meta_key = base_dir + "pdf.meta.json"
				docjson_key = base_dir + "doc.json"
				content_key = None
			else:
				base_dir = prefix.rstrip("/") + "/"
				stem = p.stem
				pdf_key = base_dir + p.name
				meta_key = base_dir + f"{stem}.meta.json"
				docjson_key = base_dir + f"{stem}.doc.json"
				content_key = None

			# core PDF upload with helpful metadata
			extra = {"ContentType": "application/pdf", "Metadata": {
				"document_id": str(int(doc.id)),
				"arxiv_id": arxiv_id or "",
				"doi": doc.doi or "",
				"title": (doc.title or "")[:200],
				"year": str(doc.year or ""),
				"sha256": getattr(doc, "checksum_sha256", "") or "",
			}}
			# S3 metadata must be ASCII only
			try:
				extra["Metadata"] = {k: (str(v).encode("ascii", "ignore").decode("ascii") if v is not None else "") for k, v in extra["Metadata"].items()}
			except Exception:
				pass
			s3.upload_file(str(p), bucket, pdf_key, ExtraArgs=extra)
			# best-effort: backfill s3_key into sidecar meta if present
			try:
				meta_path = p.with_suffix(".meta.json")
				if meta_path.exists():
					import json
					data = {}
					try:
						data = json.loads(meta_path.read_text(encoding="utf-8"))
					except Exception:
						data = {}
					if data.get("s3_key") != pdf_key:
						data["s3_key"] = pdf_key
						meta_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
			except Exception:
				pass
			count += 1

			# optionally upload sidecar
			if include_sidecars:
				try:
					meta_path = p.with_suffix(".meta.json")
					if meta_path.exists():
						s3.upload_file(str(meta_path), bucket, meta_key, ExtraArgs={"ContentType": "application/json"})
				except Exception:
					pass

			# optionally upload per-document identification JSON
			if include_docjson:
				try:
					import json
					authors_val = None
					try:
						import json as _json
						if isinstance(doc.authors, str):
							a = _json.loads(doc.authors)
							if isinstance(a, list):
								authors_val = a
					except Exception:
						authors_val = None
					if authors_val is None and isinstance(doc.authors, str):
						parts = [p.strip() for p in (doc.authors.split(";") if ";" in doc.authors else doc.authors.split(",")) if p.strip()]
						authors_val = parts or None
					row = {
						"document_id": int(doc.id),
						"source": doc.source,
						"arxiv_id": arxiv_id,
						"doi": doc.doi,
						"title": doc.title,
						"authors": authors_val,
						"abstract": doc.abstract,
						"year": int(doc.year) if doc.year is not None else None,
						"topic": doc.topic,
						"local_path": str(p),
						"checksum_sha256": getattr(doc, "checksum_sha256", None),
						"file_size": getattr(doc, "file_size", None),
						"http_status": getattr(doc, "http_status", None),
						"pdf_status": getattr(doc, "pdf_status", None),
						"pdf_fetched_at": str(getattr(doc, "pdf_fetched_at", "")) if getattr(doc, "pdf_fetched_at", None) else None,
						"s3_key": pdf_key,
					}
					import tempfile
					with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", suffix=".json") as tf:
						tf.write(json.dumps(row, ensure_ascii=False, indent=2))
						tmp_path = tf.name
					s3.upload_file(tmp_path, bucket, docjson_key, ExtraArgs={"ContentType": "application/json"})
					try:
						os.remove(tmp_path)
					except Exception:
						pass
				except Exception:
					pass

			# optionally upload extracted content
			if include_content and getattr(doc, "content_path", None):
				cp = Path(doc.content_path)
				if not cp.is_absolute():
					cp = files_dir / cp
				if cp.exists():
					if layout == "by-id":
						content_key = base_dir + ("content.txt" if cp.suffix.lower() not in (".txt", ".json", ".tei", ".xml") else ("content" + cp.suffix))
					else:
						content_key = base_dir + (p.stem + ".content" + cp.suffix)
					ctype = "text/plain"
					suf = cp.suffix.lower()
					if suf in (".json", ".tei", ".xml"):
						ctype = "application/json" if suf == ".json" else "application/xml"
					try:
						s3.upload_file(str(cp), bucket, content_key, ExtraArgs={"ContentType": ctype})
					except Exception:
						pass
		return count
	finally:
		s.close()


