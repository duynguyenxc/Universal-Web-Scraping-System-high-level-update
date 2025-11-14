"""Simple test to verify paperscraper works."""
import sys
try:
    from paperscraper.server import QUERY_FN_DICT
    print("SUCCESS: Paperscraper imported")
    print(f"Available sources: {list(QUERY_FN_DICT.keys())}")
    
    # Test with small query
    if 'pubmed' in QUERY_FN_DICT:
        print("\nTesting PubMed with query: [['concrete', 'corrosion']]")
        query = [['concrete', 'corrosion']]
        fn = QUERY_FN_DICT['pubmed']
        papers = fn(query, limit=2)
        print(f"Returned {len(papers)} papers")
        if papers:
            print(f"First paper keys: {list(papers[0].keys())}")
            print(f"Sample: title={papers[0].get('title', 'N/A')[:50]}")
            print(f"Sample: abstract={papers[0].get('abstract', 'N/A')[:100] if papers[0].get('abstract') else 'N/A'}")
            print(f"Sample: doi={papers[0].get('doi', 'N/A')}")
            print(f"Sample: year={papers[0].get('year', 'N/A')}")
            print(f"Sample: pdf_url={papers[0].get('pdf_url', 'N/A')}")
            
except ImportError as e:
    print(f"FAILED: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


