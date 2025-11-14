"""OpenAlex adapter for discovering academic papers.

OpenAlex provides a free, open catalog of the world's scholarly papers.
This adapter uses the REST API with proper cursor-based pagination.
"""

from .adapter import discover_openalex

__all__ = ["discover_openalex"]

