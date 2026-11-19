"""Catalogue iterators that `cli.py` imports but that were missing from the repository.

WHY THIS FILE EXISTS
--------------------
`uwss discover-doaj` has always raised `ModuleNotFoundError: No module named
'src.uwss.discovery'`: the command is wired up, parses its arguments, and imports a
module that is not here. `discover-semanticscholar` imports the same module for
`iter_semanticscholar_results`.

This supplies both, in the shape `cli.py` already expects — DOAJ items are yielded as
the API returns them (a `bibjson` envelope), because that is what the command reads.

ON SILENT FAILURE
-----------------
Both iterators check the response **content type**, not just the status code, and raise
rather than yielding nothing when a service answers with something that is not JSON.
That is deliberate and is the lesson of 2026-11-17: NCBI answers a blocked request with
HTTP 200 and an HTML page, so a client that trusts the status line and catches the parse
error reports "0 records" — and a literature review writes that number into its flow
diagram as a fact about the literature. An empty result and a refused request must not
look the same to the caller.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Iterator, Optional

DOAJ_API = "https://doaj.org/api/search/articles/"
S2_API = "https://api.semanticscholar.org/graph/v1/paper/search"

USER_AGENT = "uwss-res/0.1 (academic research)"


class CatalogueUnavailable(RuntimeError):
    """The service answered, but not with the data it promises.

    Raised instead of returning an empty iterator so that "the catalogue refused us"
    can never be mistaken for "the catalogue holds nothing on this topic".
    """


def _get_json(url: str, *, timeout: int = 30, attempts: int = 3,
              api_key: Optional[str] = None) -> dict:
    last: Exception | None = None
    for attempt in range(attempts):
        if attempt:
            time.sleep(2 ** attempt)
        try:
            headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
            if api_key:
                headers["x-api-key"] = api_key
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                ctype = (resp.headers.get("Content-Type") or "").lower()
                body = resp.read()
                if "json" not in ctype:
                    # The NCBI case: HTTP 200 carrying an HTML block page.
                    raise CatalogueUnavailable(
                        f"{urllib.parse.urlsplit(url).netloc} answered HTTP "
                        f"{resp.status} with Content-Type {ctype!r}, not JSON — the "
                        f"request was refused, not answered with an empty result")
                return json.loads(body)
        except CatalogueUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001 - the open web
            last = exc
    raise CatalogueUnavailable(f"{url}: {last}") from last


def iter_doaj_results(keywords: list[str], max_records: int = 50,
                      cache_ttl_sec: Optional[int] = None,
                      start_page: int = 1) -> Iterator[dict]:
    """Yield DOAJ article records for each keyword phrase, newest first.

    DOAJ indexes only fully open-access, peer-reviewed journals, which makes it the one
    added catalogue whose hits are both in scope for this review and obtainable as full
    text. `cache_ttl_sec` is accepted for signature compatibility with the CLI and not
    used: a literature search that is being reported under a protocol should re-ask the
    service rather than answer from a cache of unknown age.
    """
    seen: set[str] = set()
    emitted = 0
    for phrase in keywords:
        if emitted >= max_records:
            return
        page = max(1, start_page)
        while emitted < max_records:
            q = urllib.parse.quote(phrase, safe="")
            # NO explicit sort. DOAJ's default is relevance; asking for
            # `created_date:desc` returns the newest records matching the phrase
            # rather than the best-matching ones, which skews the sample hard
            # towards the current year and makes any comparison against a
            # relevance-ranked corpus meaningless. Measured 2026-11-18: with the
            # date sort, 135 of 370 DOAJ hits were published in the current year
            # and almost none overlapped a relevance-ranked corpus of the same
            # topic. Crossref's cursor paging drops relevance ranking the same
            # silent way — nothing in either response says the sort was ignored.
            url = f"{DOAJ_API}{q}?page={page}&pageSize=50"
            data = _get_json(url)
            results = data.get("results") or []
            if not results:
                break
            for item in results:
                title = ((item.get("bibjson") or {}).get("title") or "").strip().lower()
                if title and title in seen:
                    continue
                if title:
                    seen.add(title)
                yield item
                emitted += 1
                if emitted >= max_records:
                    return
            if len(results) < 50:
                break
            page += 1
            time.sleep(1.0)


def iter_semanticscholar_results(keywords: list[str], max_records: int = 50,
                                 cache_ttl_sec: Optional[int] = None,
                                 api_key: Optional[str] = None,
                                 start_offset: int = 0) -> Iterator[dict]:
    """Yield Semantic Scholar papers for each keyword phrase.

    Without a key the public endpoint rate-limits hard, so this sleeps a full second
    between pages and backs off on 429 rather than hammering a free service.
    """
    seen: set[str] = set()
    emitted = 0
    for phrase in keywords:
        if emitted >= max_records:
            return
        offset = max(0, start_offset)
        while emitted < max_records:
            params = urllib.parse.urlencode({
                "query": phrase, "offset": offset, "limit": 50,
                "fields": "title,abstract,year,externalIds,openAccessPdf,venue,authors"})
            data = _get_json(f"{S2_API}?{params}", api_key=api_key)
            papers = data.get("data") or []
            if not papers:
                break
            for p in papers:
                key = (p.get("paperId") or p.get("title") or "").strip().lower()
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                yield p
                emitted += 1
                if emitted >= max_records:
                    return
            offset += len(papers)
            if offset >= (data.get("total") or 0):
                break
            time.sleep(1.0)
