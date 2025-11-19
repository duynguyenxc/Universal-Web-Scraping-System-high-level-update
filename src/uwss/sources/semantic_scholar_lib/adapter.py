"""Semantic Scholar adapter: Main discovery function using semanticscholar library."""

from __future__ import annotations

import logging
import time
from typing import Iterator, Optional

from .mapper import map_semantic_scholar_to_document

logger = logging.getLogger(__name__)

# Try to import semanticscholar, but handle gracefully if not available
try:
    from semanticscholar import SemanticScholar

    SEMANTICSCHOLAR_AVAILABLE = True
except ImportError:
    SEMANTICSCHOLAR_AVAILABLE = False
    SemanticScholar = None
    logger.warning(
        "semanticscholar library not available. Install with: pip install semanticscholar"
    )


def discover_semantic_scholar(
	keywords: list[str],
	max_records: Optional[int] = None,
	year_filter: Optional[int] = None,
	api_key: Optional[str] = None,
	throttle_sec: float = 0.1,
	**kwargs,
) -> Iterator[dict]:
	"""Discover Semantic Scholar papers via semanticscholar library.

	Args:
		keywords: List of keywords to search for.
		max_records: Maximum number of records to discover.
		year_filter: Optional minimum publication year (e.g., 2020).
		api_key: Optional API key for higher rate limits.
		throttle_sec: Delay between requests (seconds).

	Yields:
		Dictionary with fields matching Document model.

	Raises:
		ImportError: If semanticscholar is not installed.
	"""
	if not SEMANTICSCHOLAR_AVAILABLE:
		raise ImportError(
			"semanticscholar library is required. Install with: pip install semanticscholar"
		)

	if not keywords:
		return

	logger.info(
		"Starting Semantic Scholar discovery via semanticscholar with %d keywords",
		len(keywords),
	)

	# Initialize SemanticScholar client
	sch = SemanticScholar(api_key=api_key) if api_key else SemanticScholar()

	# Build search query list
	is_corrosion_search = any(
		term.lower()
		in [
			"corrosion",
			"concrete",
			"steel",
			"reinforced",
			"chloride",
			"civil engineering",
		]
		for term in keywords
	)

	if is_corrosion_search:
		queries = [
			"corrosion reinforced concrete",
			"steel corrosion protection",
			"concrete corrosion chloride",
			"corrosion inhibition civil engineering",
			"corrosion stainless steel concrete",
			"corrosion cracking concrete",
			"corrosion durability concrete",
		]
		logger.info("Using corrosion-specific Semantic Scholar queries: %d", len(queries))
	else:
		# Use first few keywords as one focused query
		queries = [" ".join(keywords[:3])]

	total_limit = max_records or 100
	limit_per_query = max(1, min(50, total_limit // len(queries)))
	count = 0

	for idx, q in enumerate(queries, start=1):
		if max_records is not None and count >= max_records:
			break

		logger.info("Semantic Scholar query %d/%d: %r", idx, len(queries), q)

		if throttle_sec > 0:
			time.sleep(throttle_sec)

		try:
			results = sch.search_paper(query=q, limit=limit_per_query)
		except Exception as e:  # pragma: no cover - network / API errors
			logger.error("Error during Semantic Scholar API call: %s", e)
			if "429" in str(e) or "rate limit" in str(e).lower():
				wait_time = 60
				logger.warning("Rate limited. Waiting %d seconds...", wait_time)
				time.sleep(wait_time)
			continue

		if not results:
			logger.info("No results for query: %r", q)
			continue

		for paper in results:
			if max_records is not None and count >= max_records:
				break

			# Convert Paper object to dict
			if hasattr(paper, "to_dict"):
				paper_dict = paper.to_dict()
			elif hasattr(paper, "__dict__"):
				paper_dict = dict(paper.__dict__)
			else:
				paper_dict = {
					"title": getattr(paper, "title", None),
					"year": getattr(paper, "year", None),
					"abstract": getattr(paper, "abstract", None),
					"authors": getattr(paper, "authors", []),
					"externalIds": getattr(paper, "externalIds", {}),
					"url": getattr(paper, "url", None),
					"venue": getattr(paper, "venue", None),
					"openAccessPdf": getattr(paper, "openAccessPdf", None),
				}

			# Year filter
			if year_filter:
				pub_year = paper_dict.get("year") or getattr(paper, "year", None)
				if pub_year:
					try:
						if int(pub_year) < year_filter:
							continue
					except (ValueError, TypeError):
						pass

			mapped = map_semantic_scholar_to_document(
				paper_dict, source="semantic_scholar", paper_obj=paper
			)
			if mapped:
				yield mapped
				count += 1

	logger.info("Semantic Scholar discovery complete: %d records", count)

