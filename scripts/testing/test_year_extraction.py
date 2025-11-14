"""Test year extraction from paperscraper date field."""
from paperscraper.pubmed import get_pubmed_papers
from paperscraper.arxiv import get_arxiv_papers_api
import re

print("=" * 80)
print("TESTING YEAR EXTRACTION")
print("=" * 80)

# Test PubMed
print("\n[1] Testing PubMed date field...")
df_pubmed = get_pubmed_papers("concrete", max_results=3)
if not df_pubmed.empty:
    print(f"Sample PubMed records:")
    for idx, row in df_pubmed.head(3).iterrows():
        date_val = row.get('date', None)
        print(f"  Record {idx}: date={date_val} (type: {type(date_val)})")
        
        # Test extraction
        if date_val:
            year_match = re.search(r"\d{4}", str(date_val))
            if year_match:
                year = int(year_match.group(0))
                print(f"    -> Extracted year: {year}")
            else:
                print(f"    -> Could not extract year")

# Test arXiv
print("\n[2] Testing arXiv date field...")
df_arxiv = get_arxiv_papers_api("concrete", max_results=3)
if not df_arxiv.empty:
    print(f"Sample arXiv records:")
    for idx, row in df_arxiv.head(3).iterrows():
        date_val = row.get('date', None)
        print(f"  Record {idx}: date={date_val} (type: {type(date_val)})")
        
        # Test extraction
        if date_val:
            year_match = re.search(r"\d{4}", str(date_val))
            if year_match:
                year = int(year_match.group(0))
                print(f"    -> Extracted year: {year}")
            else:
                print(f"    -> Could not extract year")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("If date field exists but year is None in database, mapper needs to be fixed.")


