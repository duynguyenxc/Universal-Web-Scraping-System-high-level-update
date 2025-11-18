#!/usr/bin/env python3
"""Elsevier API Adapter for corrosion research papers."""

import logging
import time
import requests
from typing import Iterator, Optional, Dict, Any, List
from datetime import datetime

from ...store.models import Document
from ...utils.http import session_with_retries

logger = logging.getLogger(__name__)

class ElsevierAPIAdapter:
    """
    Adapter for Elsevier APIs (Scopus, ScienceDirect) with corrosion-focused search.

    API Key: b2348f7fe711df80e68432559d8da23f
    """

    def __init__(self, api_key: str = "b2348f7fe711df80e68432559d8da23f"):
        self.api_key = api_key
        self.base_url = "https://api.elsevier.com"
        self.session = session_with_retries()

        # Rate limiting (Elsevier allows reasonable rates, but be respectful)
        self.last_request_time = 0
        self.min_request_interval = 0.5  # 2 requests per second max

        logger.info("Elsevier API adapter initialized")

    def _rate_limit_wait(self):
        """Enforce rate limiting."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last
            time.sleep(wait_time)

        self.last_request_time = time.time()

    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Make authenticated request to Elsevier API.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            JSON response or None if error
        """
        self._rate_limit_wait()

        url = f"{self.base_url}{endpoint}"
        headers = {
            'X-ELS-APIKey': self.api_key,
            'Accept': 'application/json'
        }

        try:
            response = self.session.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                logger.warning("Rate limit exceeded, waiting longer...")
                time.sleep(5)
                return self._make_request(endpoint, params)
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None

    def discover_corrosion_papers(self, max_records: int = 100, start_year: int = 2015) -> Iterator[Document]:
        """
        Discover corrosion-related papers from Elsevier APIs.

        Uses Scopus Search API for comprehensive corrosion literature search.

        Args:
            max_records: Maximum number of papers to discover
            start_year: Only papers from this year onwards

        Yields:
            Document objects for corrosion papers
        """
        logger.info(f"Starting Elsevier corrosion paper discovery (max: {max_records})")

        # Corrosion search queries for Scopus
        corrosion_queries = [
            'TITLE-ABS-KEY(corrosion)',
            'TITLE-ABS-KEY("corrosion resistance")',
            'TITLE-ABS-KEY("corrosion protection")',
            'TITLE-ABS-KEY("anti-corrosion")',
            'TITLE-ABS-KEY("corrosion inhibition")',
            'TITLE-ABS-KEY("steel corrosion")',
            'TITLE-ABS-KEY("concrete corrosion")',
            'TITLE-ABS-KEY("chloride corrosion")',
            'TITLE-ABS-KEY("pitting corrosion")',
            'TITLE-ABS-KEY("galvanic corrosion")',
            'TITLE-ABS-KEY("stress corrosion")',
            'TITLE-ABS-KEY("corrosion fatigue")',
            'TITLE-ABS-KEY("cathodic protection")'
        ]

        discovered_count = 0
        seen_dois = set()  # Deduplication

        for query in corrosion_queries:
            if discovered_count >= max_records:
                logger.info(f"Reached max records limit: {max_records}")
                break

            logger.info(f"Searching Scopus for: {query}")

            try:
                papers_found = 0

                # Scopus Search API
                for start in range(0, min(200, max_records - discovered_count), 25):  # Max 200 results per query
                    params = {
                        'query': query,
                        'date': f'{start_year}-',
                        'sort': 'relevancy',
                        'start': start,
                        'count': min(25, max_records - discovered_count),
                        'view': 'COMPLETE'
                    }

                    response = self._make_request('/content/search/scopus', params)

                    if not response or 'search-results' not in response:
                        logger.warning(f"No results for query: {query}")
                        break

                    entries = response['search-results'].get('entry', [])
                    if not entries:
                        break

                    for entry in entries:
                        if discovered_count >= max_records:
                            break

                        # Deduplication by DOI
                        doi = entry.get('prism:doi', '')
                        if doi and doi in seen_dois:
                            continue
                        seen_dois.add(doi)

                        # Convert to UWSS Document
                        try:
                            document = self._entry_to_document(entry)
                            if document:
                                yield document
                                discovered_count += 1
                                papers_found += 1

                                if discovered_count % 10 == 0:
                                    logger.info(f"Discovered {discovered_count} papers so far")

                        except Exception as e:
                            logger.warning(f"Failed to convert entry {doi}: {e}")
                            continue

                    # If we got less than requested, no more results
                    if len(entries) < params['count']:
                        break

                logger.info(f"Query '{query}' yielded {papers_found} new papers")

            except Exception as e:
                logger.error(f"Error searching for '{query}': {e}")
                continue

        logger.info(f"Elsevier discovery completed: {discovered_count} papers found")

    def _entry_to_document(self, entry: Dict[str, Any]) -> Optional[Document]:
        """
        Convert Scopus entry to UWSS Document.

        Args:
            entry: Scopus search result entry

        Returns:
            UWSS Document or None if invalid
        """
        try:
            # Extract basic metadata
            title = entry.get('dc:title', '').strip()
            if not title:
                return None

            # Abstract (may not be available in search results)
            abstract = entry.get('dc:description', '') or ''

            # Authors
            authors = []
            if 'author' in entry:
                author_list = entry['author']
                if isinstance(author_list, list):
                    authors = [author.get('authname', '') for author in author_list]
                elif isinstance(author_list, dict):
                    authors = [author_list.get('authname', '')]

            # DOI
            doi = entry.get('prism:doi', '')

            # URLs
            url = entry.get('link', [{}])[0].get('@href', '') if entry.get('link') else ''
            if not url and doi:
                url = f"https://doi.org/{doi}"

            # PDF URL - Elsevier may provide direct PDF access
            pdf_url = None
            if entry.get('link'):
                for link in entry['link']:
                    if isinstance(link, dict) and link.get('@ref') == 'scidirpdf':
                        pdf_url = link.get('@href')
                        break

            # Year
            year = None
            cover_date = entry.get('prism:coverDate', '')
            if cover_date:
                try:
                    year = int(cover_date[:4])
                except:
                    pass

            # Venue/Publication
            venue = entry.get('prism:publicationName', '')

            # Citation count (if available)
            citation_count = entry.get('citedby-count', '0')
            citation_count = int(citation_count) if citation_count.isdigit() else 0

            # Create UWSS Document
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
            document.metadata = {
                'scopus_id': entry.get('dc:identifier', '').replace('SCOPUS_ID:', ''),
                'eid': entry.get('eid', ''),
                'pii': entry.get('pii', ''),
                'cited_by_count': citation_count,
                'subtype': entry.get('subtype', ''),
                'subtypeDescription': entry.get('subtypeDescription', ''),
                'open_access': entry.get('openaccess', '0') == '1',
                'journal_issn': entry.get('prism:issn', ''),
                'publisher': entry.get('dc:publisher', ''),
                'affiliation': entry.get('affiliation', []),
                'discovered_at': datetime.now().isoformat(),
                'api_source': 'elsevier_scopus'
            }

            return document

        except Exception as e:
            logger.warning(f"Error converting Scopus entry to document: {e}")
            return None

    def get_paper_details(self, doi: str) -> Optional[Document]:
        """
        Get detailed information for a specific paper by DOI.

        Uses ScienceDirect API for full text access if available.

        Args:
            doi: Paper DOI

        Returns:
            Detailed Document object
        """
        try:
            # Try ScienceDirect API first
            endpoint = f"/content/article/doi/{doi}"
            params = {'view': 'FULL'}

            response = self._make_request(endpoint, params)
            if response:
                return self._parse_sciencedirect_response(response)

            # Fallback to Scopus lookup
            params = {'query': f'doi({doi})', 'view': 'COMPLETE'}
            response = self._make_request('/content/search/scopus', params)

            if response and response.get('search-results', {}).get('entry'):
                entry = response['search-results']['entry'][0]
                return self._entry_to_document(entry)

        except Exception as e:
            logger.error(f"Failed to get paper details for DOI {doi}: {e}")

        return None

    def _parse_sciencedirect_response(self, response: Dict[str, Any]) -> Optional[Document]:
        """
        Parse ScienceDirect API response to Document.

        Args:
            response: ScienceDirect API response

        Returns:
            Document object
        """
        try:
            # Extract from ScienceDirect format
            # This is a simplified implementation - ScienceDirect has complex response structure
            article = response.get('full-text-retrieval-response', {})

            title = article.get('coredata', {}).get('dc:title', '')
            if not title:
                return None

            # For now, return basic document - can be expanded for full text extraction
            document = Document(
                title=title,
                source='elsevier_api',
                source_type='api'
            )

            document.metadata = {
                'full_text_available': True,
                'api_source': 'elsevier_sciencedirect'
            }

            return document

        except Exception as e:
            logger.warning(f"Failed to parse ScienceDirect response: {e}")
            return None


