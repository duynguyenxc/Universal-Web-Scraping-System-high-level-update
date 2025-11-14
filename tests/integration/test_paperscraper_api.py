"""Test script to verify paperscraper API signatures and output format."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from paperscraper.server import QUERY_FN_DICT
    print("✅ Paperscraper imported successfully")
    print(f"Available sources: {list(QUERY_FN_DICT.keys())}")
    
    # Test query format
    query = [['concrete', 'corrosion']]
    print(f"\n📝 Test query format: {query}")
    
    # Test pubmed
    if 'pubmed' in QUERY_FN_DICT:
        print("\n🔬 Testing PubMed...")
        pubmed_fn = QUERY_FN_DICT['pubmed']
        papers = pubmed_fn(query, limit=3)
        print(f"   Type: {type(papers)}")
        print(f"   Count: {len(papers) if isinstance(papers, list) else 'N/A'}")
        if papers:
            print(f"   First paper keys: {list(papers[0].keys()) if isinstance(papers, list) else 'N/A'}")
            print(f"   Sample paper: {papers[0] if isinstance(papers, list) else 'N/A'}")
    
    # Test arxiv
    if 'arxiv' in QUERY_FN_DICT:
        print("\n📚 Testing arXiv...")
        arxiv_fn = QUERY_FN_DICT['arxiv']
        papers = arxiv_fn(query, limit=3)
        print(f"   Type: {type(papers)}")
        print(f"   Count: {len(papers) if isinstance(papers, list) else 'N/A'}")
        if papers:
            print(f"   First paper keys: {list(papers[0].keys()) if isinstance(papers, list) else 'N/A'}")
            print(f"   Sample paper: {papers[0] if isinstance(papers, list) else 'N/A'}")
            
except ImportError as e:
    print(f"[ERROR] Paperscraper not available: {e}")
    print("Install with: pip install paperscraper")
except Exception as e:
    print(f"[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()

