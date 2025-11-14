"""Semantic Scholar adapter: Integrates semanticscholar library for Semantic Scholar API access.

This adapter uses the semanticscholar library (https://github.com/danielnsilva/semanticscholar)
which is a well-tested and maintained Python client for the Semantic Scholar API.

The adapter follows UWSS's universal architecture:
- discover_semantic_scholar function that yields Document-compatible dictionaries
- Proper error handling and logging
- Rate limiting and polite usage
- Mapping to universal Document schema
"""

from .adapter import discover_semantic_scholar

__all__ = [
    "discover_semantic_scholar",
]

