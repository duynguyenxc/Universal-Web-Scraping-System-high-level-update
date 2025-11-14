"""Show summary by source database."""
import sqlite3
import json
from pathlib import Path

db_path = Path("data/test_paperscraper.sqlite")
export_path = Path("data/paperscraper_export.jsonl")

print("=" * 80)
print("SOURCE DATABASE SUMMARY")
print("=" * 80)

# Database stats
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
    SELECT 
        source,
        COUNT(*) as total,
        SUM(CASE WHEN year IS NOT NULL THEN 1 ELSE 0 END) as with_year,
        SUM(CASE WHEN abstract IS NOT NULL AND abstract != '' THEN 1 ELSE 0 END) as with_abstract,
        SUM(CASE WHEN pdf_url IS NOT NULL AND pdf_url != '' THEN 1 ELSE 0 END) as with_pdf_url,
        SUM(CASE WHEN doi IS NOT NULL AND doi != '' THEN 1 ELSE 0 END) as with_doi
    FROM documents
    GROUP BY source
    ORDER BY source
""")

print("\n[Database Statistics by Source]")
print("-" * 80)
print(f"{'Source':<30} {'Total':>6} {'Year':>6} {'Abstract':>9} {'PDF URL':>8} {'DOI':>6}")
print("-" * 80)

for row in cursor.fetchall():
    source, total, with_year, with_abstract, with_pdf_url, with_doi = row
    # Format source for display
    if source == "paperscraper_pubmed":
        source_display = "[PubMed] via paperscraper"
    elif source == "paperscraper_arxiv":
        source_display = "[arXiv] via paperscraper"
    elif source == "paperscraper_medrxiv":
        source_display = "[medRxiv] via paperscraper"
    elif source == "paperscraper_biorxiv":
        source_display = "[bioRxiv] via paperscraper"
    elif source == "paperscraper_chemrxiv":
        source_display = "[chemRxiv] via paperscraper"
    else:
        source_display = f"[{source}]"
    
    print(f"{source_display:<30} {total:>6} {with_year:>6} {with_abstract:>9} {with_pdf_url:>8} {with_doi:>6}")

conn.close()

# Export file stats
if export_path.exists():
    print("\n[Export File Statistics]")
    print("-" * 80)
    with open(export_path, 'r', encoding='utf-8') as f:
        records = [json.loads(line) for line in f if line.strip()]
    
    sources = {}
    for r in records:
        src = r.get('source', 'unknown')
        if src not in sources:
            sources[src] = {'total': 0, 'with_year': 0}
        sources[src]['total'] += 1
        if r.get('year'):
            sources[src]['with_year'] += 1
    
    print(f"{'Source':<30} {'Total':>6} {'With Year':>10}")
    print("-" * 80)
    for src, stats in sorted(sources.items()):
        if src == "paperscraper_pubmed":
            src_display = "[PubMed] via paperscraper"
        elif src == "paperscraper_arxiv":
            src_display = "[arXiv] via paperscraper"
        else:
            src_display = f"[{src}]"
        print(f"{src_display:<30} {stats['total']:>6} {stats['with_year']:>10}")

print("\n" + "=" * 80)
print("HOW TO IDENTIFY SOURCE")
print("=" * 80)
print("In export file, look for 'source' field:")
print("  - 'paperscraper_pubmed' = PubMed database")
print("  - 'paperscraper_arxiv' = arXiv database")
print("  - 'paperscraper_medrxiv' = medRxiv database")
print("  - 'paperscraper_biorxiv' = bioRxiv database")
print("  - 'paperscraper_chemrxiv' = chemRxiv database")

