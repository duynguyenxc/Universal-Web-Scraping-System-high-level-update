#!/usr/bin/env python3
"""Elsevier API data mapper."""

import logging
import re
from typing import Dict, Any, Optional, List

from ...store.models import Document

logger = logging.getLogger(__name__)

class ElsevierMapper:
    """Map Elsevier API data to UWSS Document schema."""

    @staticmethod
    def map_scopus_entry_to_document(entry: Dict[str, Any]) -> Optional[Document]:
        """
        Map Scopus search entry to UWSS Document.

        Args:
            entry: Scopus API entry data

        Returns:
            UWSS Document object or None if invalid
        """
        try:
            # Required fields
            title = entry.get('dc:title', '').strip()
            if not title:
                return None

            # Optional fields
            abstract = ElsevierMapper._clean_abstract(entry.get('dc:description', ''))

            authors = ElsevierMapper._extract_authors(entry)

            doi = entry.get('prism:doi', '')
            url = ElsevierMapper._extract_url(entry)

            pdf_url = ElsevierMapper._extract_pdf_url(entry)

            year = ElsevierMapper._extract_year(entry)
            venue = entry.get('prism:publicationName', '')

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
                source='elsevier_api',
                source_type='api'
            )

            # Add Elsevier specific metadata
            document.metadata = ElsevierMapper._extract_metadata(entry)

            return document

        except Exception as e:
            logger.warning(f"Failed to map Scopus entry: {e}")
            return None

    @staticmethod
    def _clean_abstract(abstract: str) -> str:
        """Clean and normalize abstract text."""
        if not abstract:
            return ''

        # Remove HTML tags
        abstract = re.sub(r'<[^>]+>', '', abstract)

        # Remove extra whitespace
        abstract = re.sub(r'\s+', ' ', abstract.strip())

        return abstract

    @staticmethod
    def _extract_authors(entry: Dict[str, Any]) -> List[str]:
        """Extract author names from Scopus entry."""
        authors = []

        author_data = entry.get('author', [])
        if isinstance(author_data, dict):
            author_data = [author_data]

        if isinstance(author_data, list):
            for author in author_data:
                if isinstance(author, dict):
                    name = author.get('authname', '').strip()
                    if name:
                        authors.append(name)

        return authors

    @staticmethod
    def _extract_url(entry: Dict[str, Any]) -> str:
        """Extract best available URL from Scopus entry."""
        # Try different link types
        links = entry.get('link', [])
        if isinstance(links, dict):
            links = [links]

        if isinstance(links, list):
            for link in links:
                if isinstance(link, dict):
                    ref = link.get('@ref', '')
                    href = link.get('@href', '')

                    # Prefer DOI link, then Scopus link
                    if ref == 'scopus' or ref == 'doi':
                        return href

        # Fallback to DOI
        doi = entry.get('prism:doi', '')
        if doi:
            return f"https://doi.org/{doi}"

        return ''

    @staticmethod
    def _extract_pdf_url(entry: Dict[str, Any]) -> Optional[str]:
        """Extract PDF URL if available."""
        links = entry.get('link', [])
        if isinstance(links, dict):
            links = [links]

        if isinstance(links, list):
            for link in links:
                if isinstance(link, dict) and link.get('@ref') == 'scidirpdf':
                    return link.get('@href')

        return None

    @staticmethod
    def _extract_year(entry: Dict[str, Any]) -> Optional[int]:
        """Extract publication year."""
        cover_date = entry.get('prism:coverDate', '')
        if cover_date and len(cover_date) >= 4:
            try:
                return int(cover_date[:4])
            except ValueError:
                pass

        # Fallback to cover display date
        cover_display = entry.get('prism:coverDisplayDate', '')
        if cover_display:
            # Extract year from date string
            year_match = re.search(r'\b(20\d{2})\b', cover_display)
            if year_match:
                return int(year_match.group(1))

        return None

    @staticmethod
    def _extract_metadata(entry: Dict[str, Any]) -> Dict[str, Any]:
        """Extract additional metadata."""
        return {
            'scopus_id': entry.get('dc:identifier', '').replace('SCOPUS_ID:', ''),
            'eid': entry.get('eid', ''),
            'pii': entry.get('pii', ''),
            'cited_by_count': ElsevierMapper._parse_citation_count(entry.get('citedby-count', '0')),
            'subtype': entry.get('subtype', ''),
            'subtype_description': entry.get('subtypeDescription', ''),
            'open_access': entry.get('openaccess', '0') == '1',
            'journal_issn': entry.get('prism:issn', ''),
            'publisher': entry.get('dc:publisher', ''),
            'affiliation': entry.get('affiliation', []),
            'api_source': 'elsevier_scopus'
        }

    @staticmethod
    def _parse_citation_count(count_str: str) -> int:
        """Parse citation count string to integer."""
        try:
            return int(count_str)
        except (ValueError, TypeError):
            return 0


