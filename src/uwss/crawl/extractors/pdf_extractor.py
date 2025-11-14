"""PDF metadata extraction.

Extracts metadata from PDF files using multiple strategies:
1. PDF metadata (title, author, subject)
2. Text analysis (first page, abstract detection)
3. Filename parsing
"""

from __future__ import annotations

import re
from typing import Optional, Dict
from pathlib import Path

try:
    from pdfminer.high_level import extract_text
    PDFMINER_AVAILABLE = True
except ImportError:
    PDFMINER_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False


def extract_pdf_metadata(pdf_path: Path | str) -> Dict[str, any]:
    """Extract metadata from PDF file.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Dictionary with extracted metadata:
        - title: Document title
        - authors: List of authors
        - abstract: Abstract if found
        - year: Publication year
        - keywords: Keywords if found
    """
    result = {
        "title": None,
        "authors": [],
        "abstract": None,
        "year": None,
        "keywords": [],
    }
    
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        return result
    
    # Strategy 1: PDF metadata (PyPDF2)
    if PYPDF2_AVAILABLE:
        try:
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                if pdf_reader.metadata:
                    meta = pdf_reader.metadata
                    if meta.get('/Title'):
                        result["title"] = meta['/Title'].strip()
                    if meta.get('/Author'):
                        authors_str = meta['/Author']
                        # Split by comma, semicolon, or "and"
                        authors = re.split(r'[,;]|\s+and\s+', authors_str)
                        result["authors"] = [a.strip() for a in authors if a.strip()]
                    if meta.get('/Subject'):
                        # Try to extract keywords from subject
                        subject = meta['/Subject']
                        keywords = re.split(r'[,;]', subject)
                        result["keywords"] = [k.strip() for k in keywords if k.strip()]
                    if meta.get('/CreationDate'):
                        # Extract year from date
                        date_str = meta['/CreationDate']
                        year_match = re.search(r'(\d{4})', date_str)
                        if year_match:
                            result["year"] = int(year_match.group(1))
        except Exception:
            pass
    
    # Strategy 2: Text extraction (first page for title/abstract)
    if PDFMINER_AVAILABLE:
        try:
            # Extract first page text
            text = extract_text(str(pdf_path), page_numbers=[0], maxpages=1)
            
            # Extract title (first line or first sentence)
            if not result["title"]:
                lines = text.split('\n')[:5]  # First 5 lines
                for line in lines:
                    line = line.strip()
                    if len(line) > 10 and len(line) < 200:  # Reasonable title length
                        result["title"] = line
                        break
            
            # Try to find abstract (look for "Abstract" keyword)
            if not result["abstract"]:
                abstract_match = re.search(
                    r'(?i)abstract\s*:?\s*(.+?)(?:\n\n|\n\s*(?:introduction|keywords|1\.))',
                    text,
                    re.DOTALL
                )
                if abstract_match:
                    abstract = abstract_match.group(1).strip()
                    if len(abstract) > 50:  # Reasonable abstract length
                        result["abstract"] = abstract[:1000]  # Limit length
            
            # Extract year from text
            if not result["year"]:
                year_match = re.search(r'\b(19|20)\d{2}\b', text[:500])
                if year_match:
                    try:
                        year = int(year_match.group(0))
                        if 1900 <= year <= 2100:
                            result["year"] = year
                    except ValueError:
                        pass
        except Exception:
            pass
    
    # Strategy 3: Filename parsing (fallback)
    if not result["title"]:
        filename = pdf_path.stem
        # Clean filename
        title = filename.replace('_', ' ').replace('-', ' ').replace('.', ' ')
        # Capitalize words
        title = ' '.join(word.capitalize() for word in title.split())
        result["title"] = title
    
    return result


