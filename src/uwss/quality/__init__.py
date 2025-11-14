"""Data quality assessment and filtering utilities.

Focuses on ensuring high-quality, relevant data collection rather than just
metadata extraction or PDF discovery.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..store.models import Document


def assess_document_quality(doc: Document) -> Dict[str, any]:
    """Assess the quality of a document for data collection purposes.
    
    Returns quality metrics:
    - completeness: How complete is the metadata (0-1)
    - relevance: Relevance score (0-1)
    - data_richness: How much useful information (0-1)
    - overall_quality: Combined quality score (0-1)
    
    Args:
        doc: Document object
        
    Returns:
        Dictionary with quality metrics
    """
    metrics = {
        "completeness": 0.0,
        "relevance": doc.relevance_score or 0.0,
        "data_richness": 0.0,
        "overall_quality": 0.0,
    }
    
    # Completeness: How many fields are filled
    fields = {
        "title": bool(doc.title),
        "abstract": bool(doc.abstract and len(doc.abstract) > 50),
        "authors": bool(doc.authors),
        "year": bool(doc.year),
        "doi": bool(doc.doi),
        "affiliations": bool(doc.affiliations),
        "keywords": bool(doc.keywords),
    }
    metrics["completeness"] = sum(fields.values()) / len(fields)
    
    # Data richness: How much useful information
    richness = 0.0
    if doc.abstract:
        # Longer abstracts = richer data
        richness += min(1.0, len(doc.abstract) / 500.0) * 0.4
    if doc.content_path:
        # Full-text content = very rich
        richness += 0.4
    if doc.authors:
        richness += 0.1
    if doc.affiliations:
        richness += 0.1
    metrics["data_richness"] = min(1.0, richness)
    
    # Overall quality: Weighted combination
    metrics["overall_quality"] = (
        0.4 * metrics["relevance"] +  # Relevance is most important
        0.3 * metrics["completeness"] +
        0.3 * metrics["data_richness"]
    )
    
    return metrics


def filter_high_quality(
    session: Session,
    min_relevance: float = 0.5,
    min_completeness: float = 0.3,
    min_overall: float = 0.4,
    limit: Optional[int] = None
) -> List[Document]:
    """Filter documents by quality criteria.
    
    Focuses on getting HIGH-QUALITY, RELEVANT data.
    
    Args:
        session: Database session
        min_relevance: Minimum relevance score
        min_completeness: Minimum completeness score
        min_overall: Minimum overall quality score
        limit: Optional limit on results
        
    Returns:
        List of high-quality documents
    """
    query = session.query(Document)
    
    # Filter by relevance
    if min_relevance > 0:
        query = query.filter(Document.relevance_score >= min_relevance)
    
    # Filter by require-match (must have matched keywords)
    query = query.filter(Document.keywords_found.isnot(None))
    query = query.filter(Document.keywords_found != "[]")
    query = query.filter(Document.keywords_found != "")
    
    # Filter by completeness (must have title and abstract)
    query = query.filter(Document.title.isnot(None))
    query = query.filter(Document.title != "")
    query = query.filter(Document.abstract.isnot(None))
    query = query.filter(Document.abstract != "")
    query = query.filter(func.length(Document.abstract) > 50)  # Substantial abstract
    
    # Sort by relevance (highest first)
    query = query.order_by(Document.relevance_score.desc())
    
    if limit:
        query = query.limit(limit)
    
    results = query.all()
    
    # Further filter by quality assessment
    high_quality = []
    for doc in results:
        quality = assess_document_quality(doc)
        if (quality["completeness"] >= min_completeness and
            quality["overall_quality"] >= min_overall):
            high_quality.append(doc)
    
    return high_quality

