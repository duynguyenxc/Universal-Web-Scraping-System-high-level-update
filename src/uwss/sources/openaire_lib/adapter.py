"""OpenAIRE Graph API adapter for UWSS."""

from __future__ import annotations

import logging
import os
import time
from typing import Iterator, Optional, List, Dict, Any

import requests

from .mapper import map_openaire_to_document

logger = logging.getLogger(__name__)


def _build_search_query(keywords: List[str]) -> str:
	"""Build a simple search query string from domain keywords."""
	limited = [kw for kw in keywords if kw.strip()][:3]
	return " ".join(limited)


def discover_openaire(
	keywords: List[str],
	max_records: Optional[int] = None,
	year_filter: Optional[int] = None,
	throttle_sec: float = 0.2,
	base_url: str = "https://api.openaire.eu/graph",
	api_version: str = "v2",
	page_size: int = 50,
	user_agent: Optional[str] = None,
	contact_email: Optional[str] = None,
) -> Iterator[Dict[str, Any]]:
	"""Discover publications from OpenAIRE Graph API.

	This function calls the `researchProducts` endpoint and yields mappings
	compatible with the UWSS `Document` model.

	Authentication:
	- Reads a personal access token from the environment variable
	  `OPENAIRE_TOKEN`. If not set, the function will still attempt unauthenticated
	  requests (with lower rate limits), but this is not recommended for larger harvests.

	Configuration:
	- `OPENAIRE_BASE_URL` (optional): override the default base URL.
	- `OPENAIRE_API_VERSION` (optional): override the API version (e.g. ``v1``).
	"""
	if not keywords:
		logger.warning("discover_openaire: no keywords provided; returning without results")
		return

	token = os.getenv("OPENAIRE_TOKEN")
	if not token:
		logger.warning("OPENAIRE_TOKEN is not set; using unauthenticated OpenAIRE requests")

	# Allow runtime overrides via environment variables for easier debugging
	base_url = os.getenv("OPENAIRE_BASE_URL", base_url)
	api_version = os.getenv("OPENAIRE_API_VERSION", api_version)

	search_query = _build_search_query(keywords)
	logger.info("Starting OpenAIRE discovery with query=%r", search_query)

	headers = {
		"accept": "application/json",
	}
	if user_agent:
		headers["User-Agent"] = user_agent
	if contact_email:
		# Some APIs like having a contact email for support / abuse handling
		headers["From"] = contact_email
	if token:
		headers["Authorization"] = f"Bearer {token}"

	endpoint = f"{base_url.rstrip('/')}/{api_version}/researchProducts"
	logger.info("OpenAIRE endpoint=%s", endpoint)

	inserted = 0
	page = 1

	while True:
		if max_records is not None and inserted >= max_records:
			break

		params = {
			"search": search_query,
			"type": "publication",
			"page": page,
			"pageSize": page_size,
			"sortBy": "relevance DESC",
		}

		try:
			resp = requests.get(endpoint, headers=headers, params=params, timeout=30)
		except Exception as e:
			logger.error("OpenAIRE request failed on page %s: %s", page, e)
			break

		if resp.status_code != 200:
			body_preview = (resp.text or "")[:500]
			logger.error(
				"OpenAIRE API returned status %s on page %s. Endpoint=%s params=%r body=%r",
				resp.status_code,
				page,
				endpoint,
				params,
				body_preview,
			)
			if resp.status_code == 403:
				logger.error(
					"OpenAIRE 403 Forbidden: this usually indicates an invalid/expired "
					"OPENAIRE_TOKEN, missing permissions for the Graph API, or a base "
					"URL / API version mismatch. Check OPENAIRE_TOKEN, OPENAIRE_BASE_URL "
					"and OPENAIRE_API_VERSION."
				)
			break

		try:
			data = resp.json()
		except Exception as e:
			logger.error("Failed to decode OpenAIRE JSON on page %s: %s", page, e)
			break

		items = data.get("results") or data.get("hits") or []
		if not items:
			# No more results
			break

		for record in items:
			if max_records is not None and inserted >= max_records:
				break

			# Some deployments wrap the actual metadata under 'metadata' or similar.
			# Our mapper expects the full record and looks for 'metadata' internally.
			mapped = map_openaire_to_document(record, source="openaire")
			if not mapped:
				continue

			# Optional year post-filter
			if year_filter is not None and mapped.get("year") is not None:
				try:
					if int(mapped["year"]) < int(year_filter):
						continue
				except (TypeError, ValueError):
					pass

			yield mapped
			inserted += 1

		logger.info("OpenAIRE: processed page %s, total inserted=%s", page, inserted)
		page += 1

		# Respectful throttling
		if throttle_sec > 0:
			time.sleep(throttle_sec)

	logger.info("OpenAIRE discovery complete: %s records", inserted)


