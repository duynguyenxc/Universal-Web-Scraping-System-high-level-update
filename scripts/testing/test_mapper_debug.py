"""Debug mapper to see if date field is being processed."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from paperscraper.pubmed import get_pubmed_papers
from uwss.sources.paperscraper.mappers import map_paperscraper_to_document

print("=" * 80)
print("DEBUGGING MAPPER")
print("=" * 80)

# Get a sample paper
df = get_pubmed_papers("concrete", max_results=1)
if not df.empty:
    paper = df.iloc[0].to_dict()
    print("\n[1] Raw paper from paperscraper:")
    print(f"  Keys: {list(paper.keys())}")
    print(f"  date field: {paper.get('date')} (type: {type(paper.get('date'))})")
    print(f"  year field: {paper.get('year')} (type: {type(paper.get('year'))})")
    
    # Test mapper
    print("\n[2] Testing mapper...")
    mapped = map_paperscraper_to_document(paper, source="paperscraper_pubmed")
    if mapped:
        print(f"  Mapped year: {mapped.get('year')}")
        print(f"  Mapped date: {mapped.get('date')}")
        print(f"  All mapped keys: {list(mapped.keys())}")
    else:
        print("  Mapper returned None!")


