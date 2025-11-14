"""View export data from new sources"""
import json
from pathlib import Path

export_path = Path("data/new_sources_export.jsonl")

if not export_path.exists():
    print("Export file not found. Run export first.")
    exit(1)

with open(export_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total records in export: {len(lines)}\n")

for i, line in enumerate(lines[:5], 1):
    r = json.loads(line)
    print(f"Record {i} ({r.get('source', 'unknown')}):")
    print(f"  Title: {r.get('title', 'N/A')[:70]}...")
    print(f"  Year: {r.get('year', 'N/A')}")
    print(f"  DOI: {r.get('doi', 'N/A')}")
    print(f"  Abstract: {'Yes (' + str(len(r.get('abstract', ''))) + ' chars)' if r.get('abstract') else 'No'}")
    if r.get('abstract'):
        print(f"    Preview: {r.get('abstract', '')[:150]}...")
    print(f"  PDF URL: {'Yes' if r.get('pdf_url') else 'No'}")
    if r.get('pdf_url'):
        print(f"    URL: {r.get('pdf_url')[:80]}...")
    print()

