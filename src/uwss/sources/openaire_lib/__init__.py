"""OpenAIRE Graph API adapter.

This package provides the `discover_openaire` generator that yields
dicts compatible with the `Document` SQLAlchemy model.
"""

from .adapter import discover_openaire

__all__ = [
    "discover_openaire",
]





