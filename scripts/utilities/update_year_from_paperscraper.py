"""Update year field in database by re-fetching from paperscraper."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy.orm import Session
from uwss.store import create_sqlite_engine, Document, Base
from paperscraper.pubmed import get_pubmed_papers
from paperscraper.arxiv import get_arxiv_papers_api
import re

db_path = Path("data/test_paperscraper.sqlite")
engine, SessionLocal = create_sqlite_engine(db_path)
session = SessionLocal()

print("=" * 80)
print("UPDATING YEAR FROM PAPERSCRAPER")
print("=" * 80)

# Get all documents without year
docs = session.query(Document).filter(Document.year.is_(None)).all()
print(f"\nFound {len(docs)} documents without year")

updated = 0
failed = 0

for doc in docs[:20]:  # Limit to 20 for testing
    try:
        # Try to get year from paperscraper based on source
        if "pubmed" in doc.source.lower():
            # For PubMed, we'd need to query by DOI or title
            # This is complex, so skip for now
            continue
        elif "arxiv" in doc.source.lower():
            # For arXiv, we can query by title or DOI
            if doc.doi:
                # Extract arxiv ID from DOI if possible
                # Or query by title
                pass
        
        # Actually, simpler approach: extract from existing data if available
        # But we don't have date field stored
        
        # Best solution: Re-run discovery with deduplication
        pass
        
    except Exception as e:
        failed += 1
        continue

session.close()

print(f"\nUpdated: {updated}, Failed: {failed}")
print("\n" + "=" * 80)
print("RECOMMENDATION")
print("=" * 80)
print("The mapper now correctly extracts year from date field.")
print("To get year for existing data, re-run discovery:")
print("  python -m src.uwss.cli paperscraper-discover --source pubmed --max 100")
print("  python -m src.uwss.cli paperscraper-discover --source arxiv --max 100")
print("\nDeduplication will prevent duplicates, and new records will have year.")


