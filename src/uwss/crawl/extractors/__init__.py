"""Metadata extractors for web crawling."""

from .html_extractor import extract_metadata
from .pdf_extractor import extract_pdf_metadata
from .researcher_extractor import extract_researcher_info

__all__ = ["extract_metadata", "extract_pdf_metadata", "extract_researcher_info"]
