"""Test paperscraper discovery with 100 records for arxiv and pubmed."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from uwss.sources.paperscraper import (
    discover_paperscraper_pubmed,
    discover_paperscraper_arxiv,
)

# Test keywords from config
keywords = [
    "reinforced concrete corrosion experiment",
    "long term durability concrete",
    "concrete chloride diffusion test",
]

print("=" * 80)
print("TESTING PAPERSCRAPER DISCOVERY")
print("=" * 80)

# Test PubMed
print("\n[1] Testing PubMed discovery (limit: 100)...")
print("-" * 80)
try:
    count = 0
    sample_papers = []
    for doc in discover_paperscraper_pubmed(keywords=keywords, max_records=100):
        count += 1
        if count <= 3:
            sample_papers.append(doc)
        
        if count % 10 == 0:
            print(f"  Progress: {count} papers discovered...")
    
    print(f"\nPubMed Results: {count} papers discovered")
    if sample_papers:
        print("\nSample papers:")
        for i, paper in enumerate(sample_papers, 1):
            print(f"\n  Paper {i}:")
            print(f"    Title: {paper.get('title', 'N/A')[:80]}")
            print(f"    DOI: {paper.get('doi', 'N/A')}")
            print(f"    Year: {paper.get('year', 'N/A')}")
            print(f"    Abstract: {paper.get('abstract', 'N/A')[:150] if paper.get('abstract') else 'N/A'}")
            print(f"    Source URL: {paper.get('source_url', 'N/A')}")
            print(f"    PDF URL: {paper.get('pdf_url', 'N/A')}")
            print(f"    Authors: {paper.get('authors', 'N/A')}")
            print(f"    Venue: {paper.get('venue', 'N/A')}")
            print(f"    Keywords: {paper.get('keywords', 'N/A')}")
            
except ImportError as e:
    print(f"  ERROR: {e}")
    print("  Install paperscraper: pip install paperscraper")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test arXiv
print("\n\n[2] Testing arXiv discovery (limit: 100)...")
print("-" * 80)
try:
    count = 0
    sample_papers = []
    for doc in discover_paperscraper_arxiv(keywords=keywords, max_records=100):
        count += 1
        if count <= 3:
            sample_papers.append(doc)
        
        if count % 10 == 0:
            print(f"  Progress: {count} papers discovered...")
    
    print(f"\narXiv Results: {count} papers discovered")
    if sample_papers:
        print("\nSample papers:")
        for i, paper in enumerate(sample_papers, 1):
            print(f"\n  Paper {i}:")
            print(f"    Title: {paper.get('title', 'N/A')[:80]}")
            print(f"    DOI: {paper.get('doi', 'N/A')}")
            print(f"    Year: {paper.get('year', 'N/A')}")
            print(f"    Abstract: {paper.get('abstract', 'N/A')[:150] if paper.get('abstract') else 'N/A'}")
            print(f"    Source URL: {paper.get('source_url', 'N/A')}")
            print(f"    PDF URL: {paper.get('pdf_url', 'N/A')}")
            print(f"    Authors: {paper.get('authors', 'N/A')}")
            print(f"    Venue: {paper.get('venue', 'N/A')}")
            print(f"    Keywords: {paper.get('keywords', 'N/A')}")
            
except ImportError as e:
    print(f"  ERROR: {e}")
    print("  Install paperscraper: pip install paperscraper")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)


