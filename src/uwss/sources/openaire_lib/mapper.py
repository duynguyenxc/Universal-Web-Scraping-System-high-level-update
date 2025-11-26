"""Mapping helpers to convert OpenAIRE Graph API records into Document dicts."""

from __future__ import annotations

from typing import Any, Dict, Optional, List
import json


def _safe_get(d: Dict[str, Any], *keys, default=None):
	curr = d
	for k in keys:
		if not isinstance(curr, dict):
			return default
		curr = curr.get(k)
		if curr is None:
			return default
	return curr if curr is not None else default


def map_openaire_to_document(record: Dict[str, Any], source: str = "openaire") -> Optional[Dict[str, Any]]:
	"""Map a single OpenAIRE researchProduct record to UWSS Document schema.
	
	The Graph API `researchProducts` endpoint returns objects with fields such as:
	- mainTitle, descriptions, publicationDate, pids (including DOI), authors, instances, etc.
	Some deployments also wrap these under a top-level ``metadata`` key; we support both.
	"""
	# Some responses embed fields under "metadata", others expose them at top level
	metadata = record.get("metadata") or record
	
	# DOI
	doi = _safe_get(metadata, "doi")
	if not doi:
		for pid in metadata.get("pids", []) or []:
			if isinstance(pid, dict) and pid.get("scheme", "").lower() == "doi":
				doi = pid.get("value")
				break
	
	# Title
	title = (_safe_get(metadata, "title", default="") or metadata.get("mainTitle", "")).strip()
	title = title or None
	
	# Abstract / description
	abstract = _safe_get(metadata, "description")
	if not abstract:
		descs = metadata.get("descriptions") or []
		if isinstance(descs, list) and descs:
			abstract = "\n\n".join(str(d) for d in descs if isinstance(d, str))
	
	if not title and not abstract:
		# Skip completely empty items
		return None
	
	# Authors
	authors_list: List[str] = []
	for author in metadata.get("authors", []) or []:
		if isinstance(author, dict):
			name = author.get("fullName") or author.get("name")
			if isinstance(name, str) and name.strip():
				authors_list.append(name.strip())
	authors_json = json.dumps(authors_list, ensure_ascii=False) if authors_list else None
	
	# Venue and year
	venue = (
		_safe_get(metadata, "journal", "title")
		or _safe_get(metadata, "conference", "title")
		or _safe_get(metadata, "container", "title")
	)
	publication_year = metadata.get("publicationYear")
	if publication_year is None:
		pub_date = metadata.get("publicationDate")
		if isinstance(pub_date, str) and len(pub_date) >= 4 and pub_date[:4].isdigit():
			publication_year = pub_date[:4]
	try:
		year = int(publication_year) if publication_year is not None else None
	except (TypeError, ValueError):
		year = None
	
	# Access / OA status
	best_access_right = _safe_get(metadata, "bestAccessRight", "accessRight")
	open_access = False
	oa_status = None
	if isinstance(best_access_right, str):
		oa_status = best_access_right
		if "open" in best_access_right.lower():
			open_access = True
	# Additional hint
	if not open_access and isinstance(metadata.get("isGreen"), bool):
		open_access = metadata["isGreen"]
	
	# URLs
	source_url = _safe_get(metadata, "urls", "landingPage")
	pdf_url = _safe_get(metadata, "urls", "pdf") or None
	if not source_url:
		instances = metadata.get("instances") or []
		for inst in instances:
			if not isinstance(inst, dict):
				continue
			urls = inst.get("urls") or []
			if urls:
				source_url = urls[0]
				break
	if not source_url and doi:
		source_url = f"https://doi.org/{doi}"
	if not source_url:
		source_url = record.get("id")
	
	doc: Dict[str, Any] = {
		"source_url": source_url or "",
		"landing_url": source_url,
		"pdf_url": pdf_url,
		"doi": doi,
		"title": title,
		"abstract": abstract,
		"authors": authors_json,
		"affiliations": None,
		"keywords": None,
		"venue": venue,
		"year": year,
		"pub_date": None,
		"file_type": None,
		"open_access": open_access,
		"local_path": None,
		"content_path": None,
		"content_chars": None,
		"keywords_found": None,
		"relevance_score": None,
		"status": "not_fetched",
		"pdf_status": None,
		"source": source,
		"topic": None,
		"mime_type": None,
		"text_excerpt": None,
		"fetched_at": None,
		"pdf_fetched_at": None,
		"http_status": None,
		"extractor": None,
		"license": _safe_get(metadata, "license"),
		"file_size": None,
		"oa_status": oa_status,
		"checksum_sha256": None,
		"url_hash_sha1": None,
	}
	
	return doc


