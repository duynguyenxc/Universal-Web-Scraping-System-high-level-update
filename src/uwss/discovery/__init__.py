"""Discovery iterators for academic data sources.

Each iterator encapsulates paging, retries, and minimal normalization for a
specific public API (Semantic Scholar, Europe PMC, Crossref, arXiv, PMC, DOAJ).

Design:
- Stateless generators that yield raw-ish records; CLI layer handles DB writes
  and deduplication (DOI/title/url_hash) plus ingestion checkpoints.
- Built-in throttling via shared HTTP utils (cache, backoff handled in callers).
- Resume capability via `IngestionState` in CLI commands, not here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Iterator

import requests
import feedparser


OPENALEX_BASE = "https://api.openalex.org/works"


def build_openalex_query(keywords: Iterable[str], year_filter: Optional[int] = None, per_page: int = 25, contact_email: Optional[str] = None) -> Dict[str, str]:
	search = " ".join(keywords)
	params: Dict[str, str] = {
		"search": search,
		"per_page": str(per_page),
		"sort": "relevance_score:desc",
	}
	if year_filter:
		params["from_publication_date"] = f"{year_filter}-01-01"
	if contact_email:
		params["mailto"] = contact_email
	return params


def fetch_openalex_page(params: Dict[str, str], cursor: Optional[str] = None, contact_email: Optional[str] = None, user_agent: Optional[str] = None) -> Dict:
	p = dict(params)
	if cursor:
		p["cursor"] = cursor
	headers = {}
	if contact_email:
		headers["User-Agent"] = user_agent or f"uwss/0.1 (+{contact_email})"
	resp = requests.get(OPENALEX_BASE, params=p, headers=headers, timeout=30)
	resp.raise_for_status()
	return resp.json()


def iter_openalex_results(keywords: Iterable[str], year_filter: Optional[int] = None, max_records: int = 100, contact_email: Optional[str] = None, user_agent: Optional[str] = None) -> Iterable[Dict]:
    # Safer strategy: iterate per keyword with small pages and cursors, stop early
    per_kw = max(10, min(25, max_records // max(1, len(list(keywords)))))
    for kw in keywords:
        params = build_openalex_query([kw], year_filter, per_page=per_kw, contact_email=contact_email)
        cursor = "*"
        got = 0
        while True:
            try:
                data = fetch_openalex_page(params, cursor, contact_email=contact_email, user_agent=user_agent)
            except Exception:
                break
            results = data.get("results", [])
            for item in results:
                yield item
                got += 1
                if got >= per_kw:
                    break
            if got >= per_kw:
                break
            cursor = data.get("meta", {}).get("next_cursor")
            if not cursor:
                break


# ------------------------ Crossref ------------------------
CROSSREF_BASE = "https://api.crossref.org/works"


def build_crossref_params(keywords: Iterable[str], year_filter: Optional[int], rows: int, offset: int, contact_email: Optional[str]) -> Dict[str, str]:
	query = " ".join(keywords)
	params: Dict[str, str] = {
		"query": query,
		"rows": str(rows),
		"offset": str(offset),
	}
	if year_filter:
		params["filter"] = f"from-pub-date:{year_filter}-01-01"
	return params


def fetch_crossref_page(params: Dict[str, str], contact_email: Optional[str], cache_ttl_sec: Optional[int] = None) -> Dict:
	headers = {
		"User-Agent": f"uwss/0.1 ({contact_email})" if contact_email else "uwss/0.1",
		"Accept": "application/json",
	}
	if cache_ttl_sec:
		from ..utils.cache import fetch_json_with_cache
		return fetch_json_with_cache(CROSSREF_BASE, params=params, headers=headers, ttl_sec=cache_ttl_sec)
	resp = requests.get(CROSSREF_BASE, params=params, headers=headers, timeout=30)
	resp.raise_for_status()
	return resp.json()


def iter_crossref_results(keywords: Iterable[str], year_filter: Optional[int] = None, max_records: int = 100, contact_email: Optional[str] = None, cache_ttl_sec: Optional[int] = None, start_offset: int = 0) -> Iterator[Dict]:
	rows = 20
	offset = int(start_offset or 0)
	count = 0
	while count < max_records:
		params = build_crossref_params(keywords, year_filter, rows, offset, contact_email)
		data = fetch_crossref_page(params, contact_email, cache_ttl_sec=cache_ttl_sec)
		items = (data.get("message") or {}).get("items", [])
		if not items:
			break
		for item in items:
			yield item
			count += 1
			if count >= max_records:
				break
		offset += rows


# ------------------------ arXiv ------------------------
ARXIV_API = "http://export.arxiv.org/api/query"


def iter_arxiv_results(keywords: Iterable[str], max_records: int = 50, start: int = 0) -> Iterator[Dict]:
	# arXiv query uses + for spaces; limit simple OR across keywords
	query_terms = [kw.replace(" ", "+") for kw in keywords]
	query = "+OR+".join(f"all:{q}" for q in query_terms)
	params = {
		"search_query": query,
		"start": int(start or 0),
		"max_results": max_records,
	}
	url = ARXIV_API + "?" + "&".join(f"{k}={v}" for k, v in params.items())
	feed = feedparser.parse(url)
	for entry in feed.entries:
		links = entry.get("links", [])
		pdf_link = None
		for l in links:
			if l.get("type") == "application/pdf":
				pdf_link = l.get("href")
				break
		yield {
			"id": entry.get("id"),
			"title": entry.get("title"),
			"summary": entry.get("summary"),
			"published": entry.get("published"),
			"authors": [a.get("name") for a in entry.get("authors", [])],
			"pdf_link": pdf_link,
		}


# ------------------------ Semantic Scholar ------------------------
S2_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"


def build_s2_params(query: str, limit: int, offset: int) -> Dict[str, str]:
	fields = [
		"title",
		"year",
		"abstract",
		"venue",
		"journal",
		"externalIds",
		"openAccessPdf",
		"url",
		"authors.name",
	]
	return {
		"query": query,
		"limit": str(limit),
		"offset": str(offset),
		"fields": ",".join(fields),
	}


def fetch_s2_page(params: Dict[str, str], api_key: Optional[str] = None, cache_ttl_sec: Optional[int] = None) -> Dict:
	headers = {}
	if api_key:
		headers["x-api-key"] = api_key
	if cache_ttl_sec:
		from ..utils.cache import fetch_json_with_cache
		return fetch_json_with_cache(S2_BASE, params=params, headers=headers, ttl_sec=cache_ttl_sec)
	resp = requests.get(S2_BASE, params=params, headers=headers, timeout=30)
	resp.raise_for_status()
	return resp.json()


def iter_semanticscholar_results(keywords: Iterable[str], max_records: int = 100, api_key: Optional[str] = None, cache_ttl_sec: Optional[int] = None, start_offset: int = 0) -> Iterator[Dict]:
	"""Iterate Semantic Scholar results keyword-by-keyword in small batches to avoid 400 errors.
	- Uses limit<=10 per call; resumes from start_offset only for the first keyword.
	"""
	kw_list = [k for k in keywords if str(k).strip()]
	count = 0
	first = True
	for kw in kw_list:
		if count >= max_records:
			break
		query = kw.strip()
		limit = min(10, max_records - count)
		offset = int(start_offset or 0) if first else 0
		first = False
		while count < max_records:
			params = build_s2_params(query, limit=limit, offset=offset)
			try:
				data = fetch_s2_page(params, api_key=api_key, cache_ttl_sec=cache_ttl_sec)
			except Exception:
				# skip problematic keyword/page (e.g., 400 Bad Request)
				break
			items = data.get("data") or []
			if not items:
				break
			for item in items:
				yield item
				count += 1
				if count >= max_records:
					break
			offset += limit


# ------------------------ PMC (NCBI E-utilities) ------------------------
EUTILS_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EUTILS_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


def _pmc_esearch(term: str, retstart: int, retmax: int, cache_ttl_sec: Optional[int] = None) -> Dict:
	params = {
		"db": "pmc",
		"term": term,
		"retmode": "json",
		"retstart": str(retstart),
		"retmax": str(retmax),
	}
	if cache_ttl_sec:
		from ..utils.cache import fetch_json_with_cache
		return fetch_json_with_cache(EUTILS_ESEARCH, params=params, ttl_sec=cache_ttl_sec)
	resp = requests.get(EUTILS_ESEARCH, params=params, timeout=30)
	resp.raise_for_status()
	return resp.json()


def _pmc_esummary(id_list: str, cache_ttl_sec: Optional[int] = None) -> Dict:
	params = {
		"db": "pmc",
		"id": id_list,
		"retmode": "json",
	}
	if cache_ttl_sec:
		from ..utils.cache import fetch_json_with_cache
		return fetch_json_with_cache(EUTILS_ESUMMARY, params=params, ttl_sec=cache_ttl_sec)
	resp = requests.get(EUTILS_ESUMMARY, params=params, timeout=30)
	resp.raise_for_status()
	return resp.json()


def iter_pmc_results(keywords: Iterable[str], max_records: int = 100, cache_ttl_sec: Optional[int] = None, start_retstart: int = 0) -> Iterator[Dict]:
	query = " OR ".join([f"{kw}" for kw in keywords])
	retmax = min(20, max_records)
	retstart = int(start_retstart or 0)
	count = 0
	while count < max_records:
		data = _pmc_esearch(query, retstart=retstart, retmax=retmax, cache_ttl_sec=cache_ttl_sec)
		ids = (data.get("esearchresult") or {}).get("idlist") or []
		if not ids:
			break
		sumjs = _pmc_esummary(",".join(ids), cache_ttl_sec=cache_ttl_sec)
		docsum = (sumjs.get("result") or {})
		for id_ in ids:
			item = docsum.get(str(id_)) or {}
			if not item or str(id_) == "uids":
				continue
			yield item
			count += 1
			if count >= max_records:
				break
		retstart += retmax


# ------------------------ DOAJ ------------------------
DOAJ_SEARCH = "https://doaj.org/api/v2/search/articles/"


def fetch_doaj_page(query: str, page: int, page_size: int, cache_ttl_sec: Optional[int] = None) -> Dict:
	params = {
		"page": str(page),
		"pageSize": str(page_size),
	}
	url = DOAJ_SEARCH + requests.utils.quote(query, safe="")
	if cache_ttl_sec:
		from ..utils.cache import fetch_json_with_cache
		return fetch_json_with_cache(url, params=params, ttl_sec=cache_ttl_sec)
	resp = requests.get(url, params=params, timeout=30)
	resp.raise_for_status()
	return resp.json()


def iter_doaj_results(keywords: Iterable[str], max_records: int = 100, cache_ttl_sec: Optional[int] = None, start_page: int = 1) -> Iterator[Dict]:
	# DOAJ Lucene-like query: join keywords with OR
	q = " OR ".join([f'"{k}"' for k in keywords])
	page_size = min(20, max_records)
	page = int(start_page or 1)
	count = 0
	while count < max_records:
		js = fetch_doaj_page(q, page=page, page_size=page_size, cache_ttl_sec=cache_ttl_sec)
		results = js.get("results") or []
		if not results:
			break
		for item in results:
			yield item
			count += 1
			if count >= max_records:
				break
		page += 1

# ------------------------ Europe PMC ------------------------
EUPMC_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def build_eupmc_query(keywords: Iterable[str], year_filter: Optional[int] = None, page_size: int = 25) -> Dict[str, str]:
	query = " OR ".join([f'ALL:"{kw}"' for kw in keywords])
	if year_filter:
		query = f"({query}) AND PUB_YEAR:[{year_filter} TO 3000]"
	return {
		"query": query,
		"format": "json",
		"pageSize": str(page_size),
	}


def fetch_eupmc_page(params: Dict[str, str], cursor_mark: Optional[str] = None, cache_ttl_sec: Optional[int] = None) -> Dict:
	p = dict(params)
	if cursor_mark:
		p["cursorMark"] = cursor_mark
	if cache_ttl_sec:
		from ..utils.cache import fetch_json_with_cache
		return fetch_json_with_cache(EUPMC_BASE, params=p, ttl_sec=cache_ttl_sec)
	resp = requests.get(EUPMC_BASE, params=p, timeout=30)
	resp.raise_for_status()
	return resp.json()


def iter_eupmc_results(keywords: Iterable[str], year_filter: Optional[int] = None, max_records: int = 100, cache_ttl_sec: Optional[int] = None, start_cursor: Optional[str] = "*") -> Iterator[Dict]:
	params = build_eupmc_query(list(keywords), year_filter, page_size=min(25, max_records))
	cursor = start_cursor or "*"
	count = 0
	while count < max_records:
		data = fetch_eupmc_page(params, cursor_mark=cursor, cache_ttl_sec=cache_ttl_sec)
		hits = (data.get("resultList") or {}).get("result", [])
		if not hits:
			break
		for item in hits:
			yield item
			count += 1
			if count >= max_records:
				break
		cursor = data.get("nextCursorMark")
		if not cursor:
			break
