#!/usr/bin/env python3
"""Semantic Scholar API Adapter for corrosion research papers."""

import logging
import time
from typing import Iterator, Optional, Dict, Any, List
from datetime import datetime

import semanticscholar as sch

from ...store.models import Document
from ...utils.http import session_with_retries

logger = logging.getLogger(__name__)

class SemanticScholarAPIAdapter:
    """
    Adapter for Semantic Scholar API with corrosion-focused search.

    API Key: mi2Gv4dHkE8Zk4gNWItxJ747ijFIKLVX7ZZjMkjT
    Rate Limit: 1 request per second (cumulative across all endpoints)
    """

    def __init__(self, api_key: str = "mi2Gv4dHkE8Zk4gNWItxJ747ijFIKLVX7ZZjMkjT"):
        self.api_key = api_key
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 second between requests

        # Initialize Semantic Scholar API
        self.ss = sch.SemanticScholar(api_key=self.api_key)
        logger.info("Semantic Scholar API adapter initialized")

    def _rate_limit_wait(self):
        """Enforce rate limiting (1 request per second)."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last
            logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)

        self.last_request_time = time.time()

    def discover_corrosion_papers(self, max_records: int = 100, start_year: int = 2015) -> Iterator[Document]:
        """
        Discover corrosion-related papers from Semantic Scholar.

        Args:
            max_records: Maximum number of papers to discover
            start_year: Only papers from this year onwards

        Yields:
            Document objects for corrosion papers
        """
        logger.info(f"Starting Semantic Scholar corrosion paper discovery (max: {max_records})")

        # Corrosion search queries - comprehensive
        corrosion_queries = [
            "corrosion",
            "corrosion resistance",
            "corrosion protection",
            "anti-corrosion",
            "corrosion inhibition",
            "steel corrosion",
            "concrete corrosion",
            "chloride corrosion",
            "pitting corrosion",
            "galvanic corrosion",
            "stress corrosion",
            "corrosion fatigue",
            "cathodic protection",
            "corrosion inhibitors",
            "protective coatings"
        ]

        discovered_count = 0
        seen_paper_ids = set()  # Deduplication

        for query in corrosion_queries:
            if discovered_count >= max_records:
                logger.info(f"Reached max records limit: {max_records}")
                break

            logger.info(f"Searching for: '{query}'")

            try:
                # Rate limiting
                self._rate_limit_wait()

                # Search papers
                results = self.ss.search_paper(query,
                                             limit=min(100, max_records - discovered_count),
                                             year=f"{start_year}-")

                papers_found = 0
                for paper in results:
                    if discovered_count >= max_records:
                        break

                    # Deduplication
                    paper_id = getattr(paper, 'paper_id', None) or getattr(paper, 'external_ids', {}).get('DOI', '')
                    if paper_id and paper_id in seen_paper_ids:
                        continue
                    seen_paper_ids.add(paper_id or f"temp_{len(seen_paper_ids)}")

                    # Convert to UWSS Document
                    try:
                        document = self._paper_to_document(paper)
                        if document:
                            yield document
                            discovered_count += 1
                            papers_found += 1

                            if discovered_count % 10 == 0:
                                logger.info(f"Discovered {discovered_count} papers so far")

                    except Exception as e:
                        logger.warning(f"Failed to convert paper {paper_id}: {e}")
                        continue

                logger.info(f"Query '{query}' yielded {papers_found} new papers")

            except Exception as e:
                logger.error(f"Error searching for '{query}': {e}")
                continue

        logger.info(f"Semantic Scholar discovery completed: {discovered_count} papers found")

    def _paper_to_document(self, paper) -> Optional[Document]:
        """
        Convert Semantic Scholar paper object to UWSS Document.

        Args:
            paper: Semantic Scholar paper object

        Returns:
            UWSS Document or None if invalid
        """
        try:
            # Extract basic metadata
            title = getattr(paper, 'title', '').strip()
            if not title:
                return None

            # Abstract
            abstract = getattr(paper, 'abstract', '') or ''

            # Authors
            authors = []
            if hasattr(paper, 'authors') and paper.authors:
                authors = [getattr(author, 'name', '') for author in paper.authors if hasattr(author, 'name')]

            # DOI and other IDs
            doi = ''
            if hasattr(paper, 'external_ids') and paper.external_ids:
                doi = paper.external_ids.get('DOI', '')

            # Year
            year = None
            if hasattr(paper, 'year') and paper.year:
                year = int(paper.year)

            # Venue/Publication
            venue = getattr(paper, 'venue', '') or ''

            # URL
            url = getattr(paper, 'url', '') or ''
            if not url and doi:
                url = f"https://doi.org/{doi}"

            # PDF URL (if available)
            pdf_url = None
            if hasattr(paper, 'is_open_access') and paper.is_open_access:
                # Try to get PDF URL - Semantic Scholar doesn't always provide direct PDF URLs
                # But we can construct from DOI or use their PDF endpoint
                if doi:
                    pdf_url = f"https://www.semanticscholar.org/reader/{doi}"
                elif url:
                    pdf_url = url.replace('/abs/', '/pdf/') if '/abs/' in url else None

            # Citation count
            citation_count = getattr(paper, 'citation_count', 0)

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
                source='semantic_scholar_api',
                source_type='api'
            )

            # Add Semantic Scholar specific metadata
            document.metadata = {
                'semantic_scholar_id': getattr(paper, 'paper_id', ''),
                'citation_count': citation_count,
                'is_open_access': getattr(paper, 'is_open_access', False),
                'fields_of_study': getattr(paper, 'fields_of_study', []),
                'discovered_at': datetime.now().isoformat(),
                'api_source': 'semantic_scholar'
            }

            return document

        except Exception as e:
            logger.warning(f"Error converting paper to document: {e}")
            return None

    def get_paper_details(self, paper_id: str) -> Optional[Document]:
        """
        Get detailed information for a specific paper.

        Args:
            paper_id: Semantic Scholar paper ID or DOI

        Returns:
            Detailed Document object
        """
        try:
            self._rate_limit_wait()
            paper = self.ss.get_paper(paper_id)
            return self._paper_to_document(paper)
        except Exception as e:
            logger.error(f"Failed to get paper details for {paper_id}: {e}")
            return None
