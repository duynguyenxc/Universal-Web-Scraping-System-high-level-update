"""Show detailed metadata from new sources: Crossref, OpenAlex, Semantic Scholar"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime

print("=" * 80)
print("NEW SOURCES DATA ANALYSIS")
print("=" * 80)
print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

db_path = Path("data/test_new_sources.sqlite")

if not db_path.exists():
    print("[ERROR] Database not found. Please run discovery first.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get statistics by source
print("[1] DATABASE STATISTICS BY SOURCE")
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

# Show sample records from each source
print("\n[2] SAMPLE RECORDS FROM EACH SOURCE")
print("-" * 80)

sources = ["crossref", "openalex", "semantic_scholar"]
for source in sources:
    cursor.execute("""
        SELECT id, title, year, doi, abstract, pdf_url, authors, venue, open_access
        FROM documents
        WHERE source = ?
        ORDER BY id DESC
        LIMIT 3
    """, (source,))
    
    rows = cursor.fetchall()
    if rows:
        print(f"\n{source.upper()} Samples:")
        print("-" * 80)
        for row in rows:
            doc_id, title, year, doi, abstract, pdf_url, authors, venue, open_access = row
            print(f"\n  ID: {doc_id}")
            print(f"  Title: {title[:70]}..." if title and len(title) > 70 else f"  Title: {title}")
            print(f"  Year: {year if year else '[None]'}")
            print(f"  DOI: {doi if doi else '[None]'}")
            print(f"  Venue: {venue if venue else '[None]'}")
            print(f"  PDF URL: {'[Available]' if pdf_url else '[None]'}")
            print(f"  Open Access: {open_access}")
            print(f"  Abstract: {'[Available - ' + str(len(abstract)) + ' chars]' if abstract else '[None]'}")
            if abstract:
                print(f"    Preview: {abstract[:150]}...")
            if authors:
                try:
                    authors_list = json.loads(authors)
                    print(f"  Authors: {', '.join(authors_list[:3])}{'...' if len(authors_list) > 3 else ''}")
                except:
                    print(f"  Authors: {authors[:100]}")
    else:
        print(f"\n{source.upper()}: No records found")

conn.close()

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("Check the database for complete data:")
print(f"  Database: {db_path.absolute()}")

