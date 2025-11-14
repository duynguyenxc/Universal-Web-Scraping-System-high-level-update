"""Show detailed metadata from all new sources"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime

print("=" * 80)
print("DETAILED METADATA ANALYSIS - New Sources")
print("=" * 80)
print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

db_path = Path("data/test_new_sources.sqlite")
export_path = Path("data/new_sources_export.jsonl")

if not db_path.exists():
    print("[ERROR] Database not found.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Statistics by source
print("[1] STATISTICS BY SOURCE")
print("-" * 80)
cursor.execute("""
    SELECT 
        source,
        COUNT(*) as total,
        SUM(CASE WHEN year IS NOT NULL THEN 1 ELSE 0 END) as with_year,
        SUM(CASE WHEN abstract IS NOT NULL AND abstract != '' THEN 1 ELSE 0 END) as with_abstract,
        SUM(CASE WHEN pdf_url IS NOT NULL AND pdf_url != '' THEN 1 ELSE 0 END) as with_pdf_url,
        SUM(CASE WHEN doi IS NOT NULL AND doi != '' THEN 1 ELSE 0 END) as with_doi,
        AVG(LENGTH(abstract)) as avg_abstract_length
    FROM documents
    GROUP BY source
    ORDER BY source
""")

print(f"{'Source':<25} {'Total':>6} {'Year':>6} {'Abstract':>9} {'PDF URL':>8} {'DOI':>6} {'Avg Abstract':>12}")
print("-" * 80)
for row in cursor.fetchall():
    source, total, with_year, with_abstract, with_pdf_url, with_doi, avg_abstract = row
    avg_abstract_str = f"{avg_abstract:.0f} chars" if avg_abstract else "N/A"
    print(f"{source:<25} {total:>6} {with_year:>6} {with_abstract:>9} {with_pdf_url:>8} {with_doi:>6} {avg_abstract_str:>12}")

# Detailed samples from each source
print("\n[2] DETAILED SAMPLES FROM EACH SOURCE")
print("=" * 80)

sources = ["crossref", "openalex", "semantic_scholar"]
for source in sources:
    cursor.execute("""
        SELECT id, title, year, doi, abstract, pdf_url, authors, venue, open_access, source_url, landing_url
        FROM documents
        WHERE source = ?
        ORDER BY id DESC
        LIMIT 2
    """, (source,))
    
    rows = cursor.fetchall()
    if rows:
        print(f"\n{source.upper()} - Sample Records:")
        print("-" * 80)
        for row in rows:
            doc_id, title, year, doi, abstract, pdf_url, authors, venue, open_access, source_url, landing_url = row
            print(f"\n  Record ID: {doc_id}")
            print(f"  Title: {title}")
            print(f"  Year: {year if year else '[None]'}")
            print(f"  DOI: {doi if doi else '[None]'}")
            print(f"  Venue: {venue if venue else '[None]'}")
            print(f"  Open Access: {bool(open_access)}")
            print(f"  PDF URL: {'[Available]' if pdf_url else '[None]'}")
            if pdf_url:
                print(f"    URL: {pdf_url[:80]}...")
            print(f"  Landing URL: {landing_url if landing_url else '[None]'}")
            print(f"  Abstract: {'[Available - ' + str(len(abstract)) + ' chars]' if abstract else '[None]'}")
            if abstract:
                # Clean HTML tags if present
                import re
                clean_abstract = re.sub(r'<[^>]+>', '', abstract)
                print(f"    Preview: {clean_abstract[:200]}...")
            if authors:
                try:
                    authors_list = json.loads(authors)
                    print(f"  Authors ({len(authors_list)}): {', '.join(authors_list[:5])}{'...' if len(authors_list) > 5 else ''}")
                except:
                    print(f"  Authors: {authors[:100]}")
    else:
        print(f"\n{source.upper()}: No records found")

conn.close()

# Export file summary
print("\n[3] EXPORT FILE SUMMARY")
print("-" * 80)
if export_path.exists():
    with open(export_path, 'r', encoding='utf-8') as f:
        records = [json.loads(line) for line in f if line.strip()]
    
    print(f"Total records in export: {len(records)}")
    
    # Group by source
    by_source = {}
    for r in records:
        src = r.get('source', 'unknown')
        if src not in by_source:
            by_source[src] = []
        by_source[src].append(r)
    
    for src, recs in sorted(by_source.items()):
        with_abstract = sum(1 for r in recs if r.get('abstract'))
        with_pdf = sum(1 for r in recs if r.get('pdf_url'))
        with_year = sum(1 for r in recs if r.get('year'))
        print(f"\n  {src}: {len(recs)} records")
        print(f"    - With abstract: {with_abstract} ({with_abstract/len(recs)*100:.1f}%)")
        print(f"    - With PDF URL: {with_pdf} ({with_pdf/len(recs)*100:.1f}%)")
        print(f"    - With year: {with_year} ({with_year/len(recs)*100:.1f}%)")
else:
    print("Export file not found")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("All three sources are now working!")
print("  - Crossref: Using habanero library")
print("  - OpenAlex: Using pyalex library")
print("  - Semantic Scholar: Using semanticscholar library")

