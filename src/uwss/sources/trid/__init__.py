"""TRB/TRID (Transportation Research Board) adapter.

TRID is accessed via sitemap crawling:
1. Parse sitemap.xml to get list of record URLs
2. Crawl each HTML page to extract metadata
3. Map to universal Document schema
"""

from .adapter import discover_trid

__all__ = ["discover_trid"]

