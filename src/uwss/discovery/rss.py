from __future__ import annotations

from typing import Dict, Iterator, Optional, List
from datetime import datetime
import feedparser


def iter_rss(url: str, max_records: Optional[int] = None) -> Iterator[Dict]:
	"""Iterate an RSS/Atom feed and yield normalized dicts for documents.

	Yields fields: title, authors (list[str]), affiliations (list[str]|empty), keywords (list[str]|from tags),
	abstract, doi (None), source_url, pdf_url (if enclosure/links provide), year.
	"""
	feed = feedparser.parse(url)
	count = 0
	for entry in feed.entries:
		title = entry.get("title")
		summary = entry.get("summary") or entry.get("description")
		link = entry.get("link") or entry.get("id")
		# authors may vary by feed
		auths: List[str] = []
		for a in entry.get("authors", []) or []:
			name = a.get("name") if isinstance(a, dict) else a
			if name:
				auths.append(name)
		# affiliations rarely present in RSS; default empty
		affils: List[str] = []
		# keywords via tags/categories when present
		kws: List[str] = []
		for t in entry.get("tags", []) or []:
			term = t.get("term") if isinstance(t, dict) else None
			if term:
				kws.append(term)
		# find pdf link from enclosures/links if provided
		pdf_url = None
		for l in entry.get("links", []) or []:
			if isinstance(l, dict):
				lt = (l.get("type") or "").lower()
				href = l.get("href")
				if lt == "application/pdf" and href:
					pdf_url = href
					break
		published = entry.get("published") or entry.get("updated") or entry.get("issued")
		year = None
		if published:
			try:
				year = int(str(published)[:4])
			except Exception:
				year = None
		yield {
			"title": title,
			"authors": auths,
			"affiliations": affils,
			"keywords": kws,
			"abstract": summary,
			"doi": None,
			"source_url": link,
			"pdf_url": pdf_url,
			"year": year,
		}
		count += 1
		if max_records and count >= max_records:
			break


