"""Scrapy pipelines for processing crawled items."""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class MetadataExtractionPipeline:
    """Pipeline to clean and validate extracted metadata."""
    
    def process_item(self, item: Dict[str, Any], spider) -> Dict[str, Any]:
        """Process and clean item metadata."""
        # Ensure required fields exist
        if not item.get('title'):
            item['title'] = item.get('source_url', '').split('/')[-1] or 'Untitled'
        
        # Clean abstract
        abstract = item.get('abstract', '')
        if abstract:
            # Remove excessive whitespace
            abstract = ' '.join(abstract.split())
            item['abstract'] = abstract[:2000]  # Limit length
        
        # Validate year
        year = item.get('year')
        if year and (year < 1990 or year > 2025):
            item['year'] = None
        
        # Clean authors list
        authors = item.get('authors', [])
        if isinstance(authors, str):
            authors = [a.strip() for a in authors.split(',')]
        item['authors'] = [a for a in authors if a and len(a) > 2][:20]
        
        # Clean emails
        emails = item.get('emails', [])
        if isinstance(emails, str):
            emails = [e.strip() for e in emails.split(',')]
        item['emails'] = [e for e in emails if '@' in e][:10]  # Limit to 10 emails
        
        return item


class EmailExtractionPipeline:
    """Pipeline to enhance email extraction from contact pages."""
    
    def process_item(self, item: Dict[str, Any], spider) -> Dict[str, Any]:
        """Enhance email extraction if item has contact-related keywords."""
        url = item.get('source_url', '').lower()
        title = item.get('title', '').lower()
        
        # If this is a contact/people page, prioritize email extraction
        if any(kw in url or kw in title for kw in ['contact', 'people', 'team', 'staff', 'members']):
            # Emails should already be extracted, but we can enhance here
            pass
        
        return item


class UWSSDocumentPipeline:
    """Pipeline to convert items to UWSS Document format."""
    
    def __init__(self):
        self.processed_count = 0
    
    def process_item(self, item: Dict[str, Any], spider) -> Dict[str, Any]:
        """Convert to UWSS Document format.

        Note: reverted to the simpler, previous behavior:
        - Only `abstract` is used (no separate `text` field)
        - No de-duplication by URL inside this pipeline
        """
        document = {
            'title': item.get('title', ''),
            'abstract': item.get('abstract', ''),
            'year': item.get('year'),
            'authors': item.get('authors', []),
            'source_url': item.get('source_url', ''),
            'landing_url': item.get('source_url', ''),
            'topic': item.get('topic', 'web-crawl'),
            'status': item.get('status', 'not_fetched'),
            'source': 'web-crawler-scrapy',
            # Additional metadata
            'metadata': {
                'group': item.get('group', ''),
                'emails': item.get('emails', []),
                'depth': item.get('depth', 0),
            }
        }
        
        self.processed_count += 1
        logger.debug(f"Converted item {self.processed_count}: {document.get('title', '')[:50]}")
        
        return document

