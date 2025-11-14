"""Test semanticscholar directly to understand API"""
from semanticscholar import SemanticScholar

sch = SemanticScholar()

# Test search
try:
    results = sch.search_paper(query="reinforced concrete", limit=5)
    print(f"Type of results: {type(results)}")
    print(f"Length: {len(results) if results else 0}")
    
    if results:
        for i, paper in enumerate(results[:3], 1):
            print(f"Paper {i}: {paper.get('title', 'N/A')[:60]}")
    else:
        print("No results")
except Exception as e:
    print(f"Error: {e}")
    print(f"Error type: {type(e)}")

