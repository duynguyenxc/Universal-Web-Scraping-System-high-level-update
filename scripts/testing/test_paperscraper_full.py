"""Full test of paperscraper integration: discovery, database, metadata quality."""
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy.orm import Session
from uwss.store import create_sqlite_engine, Document, Base
from uwss.sources.paperscraper import (
    discover_paperscraper_pubmed,
    discover_paperscraper_arxiv,
)

# Test keywords
keywords = [
    "reinforced concrete corrosion experiment",
    "long term durability concrete",
    "concrete chloride diffusion test",
]

# Setup test database
db_path = Path("data/test_paperscraper.sqlite")
db_path.parent.mkdir(parents=True, exist_ok=True)
if db_path.exists():
    db_path.unlink()

engine, SessionLocal = create_sqlite_engine(db_path)
Base.metadata.create_all(engine)
session = SessionLocal()

print("=" * 80)
print("FULL PAPERSCRAPER INTEGRATION TEST")
print("=" * 80)

# Test PubMed
print("\n[1] Testing PubMed discovery and database insertion (limit: 100)...")
print("-" * 80)
try:
    inserted = 0
    duplicates = 0
    sample_papers = []
    
    for doc_dict in discover_paperscraper_pubmed(keywords=keywords, max_records=100):
        # Check for duplicates
        existing = None
        if doc_dict.get("doi"):
            existing = session.query(Document).filter(Document.doi == doc_dict["doi"]).first()
        if not existing and doc_dict.get("source_url"):
            existing = session.query(Document).filter(Document.source_url == doc_dict["source_url"]).first()
        if not existing and doc_dict.get("title"):
            existing = session.query(Document).filter(Document.title == doc_dict["title"]).first()
        
        if existing:
            duplicates += 1
            continue
        
        # Insert
        doc = Document(**doc_dict)
        session.add(doc)
        session.commit()
        inserted += 1
        
        if inserted <= 3:
            sample_papers.append(doc_dict)
        
        if inserted % 10 == 0:
            print(f"  Progress: {inserted} papers inserted...")
    
    print(f"\nPubMed Results:")
    print(f"  Inserted: {inserted}")
    print(f"  Duplicates: {duplicates}")
    
    if sample_papers:
        print("\n  Sample papers:")
        for i, paper in enumerate(sample_papers, 1):
            print(f"\n    Paper {i}:")
            print(f"      Title: {paper.get('title', 'N/A')[:70]}")
            print(f"      DOI: {paper.get('doi', 'N/A')}")
            print(f"      Year: {paper.get('year', 'N/A')}")
            print(f"      Abstract length: {len(paper.get('abstract', '') or '')} chars")
            print(f"      Abstract preview: {paper.get('abstract', 'N/A')[:100] if paper.get('abstract') else 'N/A'}")
            print(f"      Source URL: {paper.get('source_url', 'N/A')}")
            print(f"      PDF URL: {paper.get('pdf_url', 'N/A')}")
            print(f"      Authors: {paper.get('authors', 'N/A')}")
            print(f"      Venue: {paper.get('venue', 'N/A')}")
            
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test arXiv
print("\n\n[2] Testing arXiv discovery and database insertion (limit: 100)...")
print("-" * 80)
try:
    inserted = 0
    duplicates = 0
    sample_papers = []
    
    for doc_dict in discover_paperscraper_arxiv(keywords=keywords, max_records=100):
        # Check for duplicates
        existing = None
        if doc_dict.get("doi"):
            existing = session.query(Document).filter(Document.doi == doc_dict["doi"]).first()
        if not existing and doc_dict.get("source_url"):
            existing = session.query(Document).filter(Document.source_url == doc_dict["source_url"]).first()
        if not existing and doc_dict.get("title"):
            existing = session.query(Document).filter(Document.title == doc_dict["title"]).first()
        
        if existing:
            duplicates += 1
            continue
        
        # Insert
        doc = Document(**doc_dict)
        session.add(doc)
        session.commit()
        inserted += 1
        
        if inserted <= 3:
            sample_papers.append(doc_dict)
        
        if inserted % 10 == 0:
            print(f"  Progress: {inserted} papers inserted...")
    
    print(f"\narXiv Results:")
    print(f"  Inserted: {inserted}")
    print(f"  Duplicates: {duplicates}")
    
    if sample_papers:
        print("\n  Sample papers:")
        for i, paper in enumerate(sample_papers, 1):
            print(f"\n    Paper {i}:")
            print(f"      Title: {paper.get('title', 'N/A')[:70]}")
            print(f"      DOI: {paper.get('doi', 'N/A')}")
            print(f"      Year: {paper.get('year', 'N/A')}")
            print(f"      Abstract length: {len(paper.get('abstract', '') or '')} chars")
            print(f"      Abstract preview: {paper.get('abstract', 'N/A')[:100] if paper.get('abstract') else 'N/A'}")
            print(f"      Source URL: {paper.get('source_url', 'N/A')}")
            print(f"      PDF URL: {paper.get('pdf_url', 'N/A')}")
            print(f"      Authors: {paper.get('authors', 'N/A')}")
            print(f"      Venue: {paper.get('venue', 'N/A')}")
            
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Database statistics
print("\n\n[3] Database Statistics...")
print("-" * 80)
try:
    total = session.query(Document).count()
    with_abstract = session.query(Document).filter(Document.abstract.isnot(None)).filter(Document.abstract != "").count()
    with_pdf_url = session.query(Document).filter(Document.pdf_url.isnot(None)).filter(Document.pdf_url != "").count()
    with_doi = session.query(Document).filter(Document.doi.isnot(None)).filter(Document.doi != "").count()
    with_year = session.query(Document).filter(Document.year.isnot(None)).count()
    pubmed_count = session.query(Document).filter(Document.source.like("%pubmed%")).count()
    arxiv_count = session.query(Document).filter(Document.source.like("%arxiv%")).count()
    
    print(f"  Total documents: {total}")
    print(f"  With abstract: {with_abstract} ({with_abstract/total*100:.1f}%)")
    print(f"  With PDF URL: {with_pdf_url} ({with_pdf_url/total*100:.1f}%)")
    print(f"  With DOI: {with_doi} ({with_doi/total*100:.1f}%)")
    print(f"  With year: {with_year} ({with_year/total*100:.1f}%)")
    print(f"  PubMed papers: {pubmed_count}")
    print(f"  arXiv papers: {arxiv_count}")
    
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

session.close()

print("\n" + "=" * 80)
print("TEST COMPLETE")
print(f"Database saved to: {db_path}")
print("=" * 80)


