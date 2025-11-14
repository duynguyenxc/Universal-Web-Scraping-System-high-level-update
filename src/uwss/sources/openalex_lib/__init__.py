"""OpenAlex adapter: Integrates pyalex library for OpenAlex API access.

This adapter uses the pyalex library (https://github.com/J535D165/pyalex)
which is a well-tested and maintained Python client for the OpenAlex API.

The adapter follows UWSS's universal architecture:
- discover_openalex function that yields Document-compatible dictionaries
- Proper error handling and logging
- Rate limiting and polite usage
- Mapping to universal Document schema
"""

from .adapter import discover_openalex

__all__ = [
    "discover_openalex",
]

