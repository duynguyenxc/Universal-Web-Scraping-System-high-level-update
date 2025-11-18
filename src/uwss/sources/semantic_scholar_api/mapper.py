#!/usr/bin/env python3
"""Semantic Scholar API data mapper."""

import logging
import re
from typing import Dict, Any, Optional

from ...store.models import Document

logger = logging.getLogger(__name__)

class SemanticScholarMapper:
    """Map Semantic Scholar API data to UWSS Document schema."""

    @staticmethod
    def map_paper_to_document(paper_data: Dict[str, Any]) -> Optional[Document]:
        """
        Map Semantic Scholar paper data to UWSS Document.

        Args:
            paper_data: Raw paper data from Semantic Scholar API

        Returns:
            UWSS Document object or None if invalid
        """
        try:
            # Required fields
            title = paper_data.get('title', '').strip()
            if not title:
                return None

            # Optional fields
            abstract = SemanticScholarMapper._clean_abstract(paper_data.get('abstract', ''))

            authors = []
            if 'authors' in paper_data:
                authors = [author.get('name', '') for author in paper_data['authors']
                          if author.get('name', '').strip()]

            doi = paper_data.get('doi', '')
            url = paper_data.get('url', '')
            if not url and doi:
                url = f"https://doi.org/{doi}"

            pdf_url = paper_data.get('openAccessPdf', {}).get('url') if paper_data.get('openAccessPdf') else None

            year = paper_data.get('year')
            if year:
                year = int(year)

            venue = paper_data.get('venue', '')

            # Create document
            document = Document(
                title=title,
                abstract=abstract,
                authors=authors,
                doi=doi,
                url=url,
                pdf_url=pdf_url,
                year=year,
                venue=venue,
                source='semantic_scholar_api',
                source_type='api'
            )

            # Add metadata
            document.metadata = {
                'paper_id': paper_data.get('paperId', ''),
                'citation_count': paper_data.get('citationCount', 0),
                'influential_citation_count': paper_data.get('influentialCitationCount', 0),
                'is_open_access': paper_data.get('isOpenAccess', False),
                'fields_of_study': paper_data.get('fieldsOfStudy', []),
                'publication_types': paper_data.get('publicationTypes', []),
                'publication_date': paper_data.get('publicationDate'),
                'journal': paper_data.get('journal', {}),
                'discovered_via': 'semantic_scholar_api'
            }

            return document

        except Exception as e:
            logger.warning(f"Failed to map paper data: {e}")
            return None

    @staticmethod
    def _clean_abstract(abstract: str) -> str:
        """Clean and normalize abstract text."""
        if not abstract:
            return ''

        # Remove extra whitespace
        abstract = re.sub(r'\s+', ' ', abstract.strip())

        # Remove HTML tags if any
        abstract = re.sub(r'<[^>]+>', '', abstract)

        # Remove excessive punctuation
        abstract = re.sub(r'[.]{2,}', '.', abstract)

        return abstract

    @staticmethod
    def validate_document(document: Document) -> bool:
        """Validate that document has required fields."""
        if not document.title or not document.title.strip():
            return False

        # At least one of: DOI, URL, or abstract
        has_identifier = bool(document.doi or document.url or document.abstract)

        return has_identifier


