"""Exports for paperscraper-based discovery adapters."""

from .adapter import (
	discover_paperscraper_pubmed,
	discover_paperscraper_arxiv,
	discover_paperscraper_medrxiv,
	discover_paperscraper_biorxiv,
	discover_paperscraper_chemrxiv,
)

__all__ = [
	"discover_paperscraper_pubmed",
	"discover_paperscraper_arxiv",
	"discover_paperscraper_medrxiv",
	"discover_paperscraper_biorxiv",
	"discover_paperscraper_chemrxiv",
]


