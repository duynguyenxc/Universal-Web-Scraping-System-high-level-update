from __future__ import annotations

import json
from typing import List, Optional

from sqlalchemy import select, func, delete

from ..store import create_sqlite_engine, Document


def _score_doc(doc: Document) -> int:
	# Higher is better
	score = 0
	if doc.open_access:
		score += 10
	if doc.abstract and len(doc.abstract) > 100:
		score += 5
	if doc.title:
		score += 2
	if doc.year:
		score += 1
	# Preference by source
	prefer = {"crossref": 5, "openalex": 4, "arxiv": 3, "scrapy": 1}
	score += prefer.get((doc.source or "").lower(), 0)
	return score


def _merge_docs(keep: Document, other: Document) -> None:
	# Fill missing fields on keep from other
	if not keep.title and other.title:
		keep.title = other.title
	if not keep.abstract and other.abstract:
		keep.abstract = other.abstract
	if not keep.venue and other.venue:
		keep.venue = other.venue
	if not keep.year and other.year:
		keep.year = other.year
	if not keep.authors and other.authors:
		keep.authors = other.authors
	if not keep.local_path and other.local_path:
		keep.local_path = other.local_path
	if not keep.file_size and other.file_size:
		keep.file_size = other.file_size
	if not keep.license and other.license:
		keep.license = other.license
	if not keep.oa_status and other.oa_status:
		keep.oa_status = other.oa_status
	if not keep.source and other.source:
		keep.source = other.source
	if other.open_access and not keep.open_access:
		keep.open_access = True


def resolve_duplicates(db_path) -> dict:
	engine, SessionLocal = create_sqlite_engine(db_path)
	s = SessionLocal()
	result = {"merged_by_doi": 0, "merged_by_title": 0, "deleted": 0}
	try:
		# By DOI
		groups = s.execute(
			select(Document.doi, func.count(Document.id))
			.where(Document.doi != None)
			.group_by(Document.doi)
			.having(func.count(Document.id) > 1)
		).all()
		for (doi, _cnt) in groups:
			recs: List[Document] = [d for (d,) in s.execute(select(Document).where(Document.doi == doi)).all()]
			if not recs:
				continue
			keep = max(recs, key=_score_doc)
			for doc in recs:
				if doc.id == keep.id:
					continue
				_merge_docs(keep, doc)
				s.delete(doc)
				result["deleted"] += 1
			s.add(keep)
			s.flush()
			result["merged_by_doi"] += 1

		# By title (lower) - handle all title duplicates regardless of DOI
		groups = s.execute(
			select(func.lower(Document.title), func.count(Document.id))
			.where(Document.title != None)
			.group_by(func.lower(Document.title))
			.having(func.count(Document.id) > 1)
		).all()
		for (ltitle, _cnt) in groups:
			recs: List[Document] = [d for (d,) in s.execute(select(Document).where(func.lower(Document.title) == ltitle)).all()]
			if not recs:
				continue
			keep = max(recs, key=_score_doc)
			for doc in recs:
				if doc.id == keep.id:
					continue
				_merge_docs(keep, doc)
				s.delete(doc)
				result["deleted"] += 1
			s.add(keep)
			s.flush()
			result["merged_by_title"] += 1

		s.commit()
		return result
	finally:
		s.close()


def normalize_metadata(db_path) -> int:
	engine, SessionLocal = create_sqlite_engine(db_path)
	s = SessionLocal()
	try:
		count = 0
		for (doc,) in s.execute(select(Document)).all():
			changed = False
			if doc.doi:
				n = doc.doi.strip().lower()
				if n != doc.doi:
					doc.doi = n
					changed = True
			if doc.title:
				n = " ".join(doc.title.split())
				if n != doc.title:
					doc.title = n
					changed = True
			if doc.venue:
				n = " ".join(doc.venue.split())
				if n != doc.venue:
					doc.venue = n
					changed = True
			if doc.authors:
				try:
					arr = json.loads(doc.authors)
					if isinstance(arr, list):
						narr = [" ".join(str(a).split()) for a in arr]
						doc.authors = json.dumps(narr)
						changed = True
				except Exception:
					pass
			if changed:
				s.add(doc)
				count += 1
		s.commit()
		return count
	finally:
		s.close()


def backfill_source(db_path) -> int:
	"""Fill missing Document.source based on heuristics from URL or venue."""
	engine, SessionLocal = create_sqlite_engine(db_path)
	s = SessionLocal()
	try:
		updated = 0
		for (doc,) in s.execute(select(Document)).all():
			if doc.source:
				continue
			src = None
			url = (doc.source_url or "").lower()
			if "crossref" in url:
				src = "crossref"
			elif "arxiv" in url:
				src = "arxiv"
			elif url.startswith("http"):
				src = "web"
			if src:
				doc.source = src
				s.add(doc)
				updated += 1
		s.commit()
		return updated
	finally:
		s.close()


def resolve_duplicates_fuzzy(db_path, threshold: float = 0.9) -> int:
	"""Merge likely-duplicate titles using fuzzy ratio on lowercase normalized titles.
	A lightweight heuristic without external deps.
	"""
	engine, SessionLocal = create_sqlite_engine(db_path)
	s = SessionLocal()
	try:
		# load all docs with titles
		docs = [(d.id, (d.title or "").lower().strip()) for (d,) in s.execute(select(Document)).all() if (d.title or "").strip()]
		# build buckets by first 20 chars to cut comparisons
		from collections import defaultdict
		buckets = defaultdict(list)
		for _id, t in docs:
			key = t[:20]
			buckets[key].append((_id, t))
		merged = 0
		def ratio(a: str, b: str) -> float:
			# simple token overlap ratio
			sa, sb = set(a.split()), set(b.split())
			if not sa or not sb:
				return 0.0
			inter = len(sa & sb)
			union = len(sa | sb)
			return inter / union
		for key, items in buckets.items():
			items_sorted = items[:]
			while len(items_sorted) > 1:
				base_id, base_t = items_sorted[0]
				keep = s.get(Document, base_id)
				rest = items_sorted[1:]
				to_delete = []
				for cand_id, cand_t in rest:
					if ratio(base_t, cand_t) >= threshold:
						other = s.get(Document, cand_id)
						_merge_docs(keep, other)
						s.delete(other)
						to_delete.append((cand_id, cand_t))
						merged += 1
				items_sorted = [items_sorted[0]] + [x for x in rest if x not in to_delete]
		s.commit()
		return merged
	finally:
		s.close()


