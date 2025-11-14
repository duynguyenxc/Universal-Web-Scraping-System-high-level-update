"""Crossref adapter: Integrates habanero library for Crossref API access.

This adapter uses the habanero library (https://github.com/sckott/habanero)
which is a well-tested and maintained Python client for the Crossref API.

The adapter follows UWSS's universal architecture:
- discover_crossref function that yields Document-compatible dictionaries
- Proper error handling and logging
- Rate limiting and polite usage
- Mapping to universal Document schema
"""

from .adapter import discover_crossref

__all__ = [
    "discover_crossref",
]

