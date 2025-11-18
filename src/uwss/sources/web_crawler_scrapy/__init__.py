"""Scrapy-based web crawler for research groups and academic websites."""

from .spider import ResearchGroupSpider
from .pipeline import MetadataExtractionPipeline, EmailExtractionPipeline, UWSSDocumentPipeline
from .adapter import discover_web_crawler_scrapy

__all__ = [
    'ResearchGroupSpider',
    'MetadataExtractionPipeline',
    'EmailExtractionPipeline',
    'UWSSDocumentPipeline',
    'discover_web_crawler_scrapy',
]

