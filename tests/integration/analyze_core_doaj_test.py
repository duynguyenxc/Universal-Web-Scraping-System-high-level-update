"""Analyze CORE and DOAJ test results."""

import sqlite3
import json
import sys
from pathlib import Path

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

db_path = Path("data/test_core_doaj.sqlite")

if not db_path.exists():
    print(f"Database not found: {db_path}")
    exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Count by source
cursor.execute("SELECT source, COUNT(*) FROM documents GROUP BY source")
sources = dict(cursor.fetchall())
print("=" * 80)
print("SOURCES SUMMARY")
print("=" * 80)
for source, count in sources.items():
    print(f"  {source}: {count} records")

# Sample records
print("\n" + "=" * 80)
print("SAMPLE RECORDS (first 10)")
print("=" * 80)
cursor.execute("""
    SELECT title, source, doi, year, abstract, authors 
    FROM documents 
    ORDER BY id 
    LIMIT 10
""")
for row in cursor.fetchall():
    title, source, doi, year, abstract, authors = row
    print(f"\nSource: {source}")
    title_str = (title[:80] + "...") if title and len(title) > 80 else (title or "N/A")
    print(f"  Title: {title_str}")
    print(f"  DOI: {doi or 'N/A'}")
    print(f"  Year: {year or 'N/A'}")
    print(f"  Abstract: {'Yes' if abstract else 'No'}")
    print(f"  Authors: {'Yes' if authors else 'No'}")

# Data quality metrics
print("\n" + "=" * 80)
print("DATA QUALITY METRICS")
print("=" * 80)
cursor.execute("SELECT COUNT(*) FROM documents")
total = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM documents WHERE title IS NOT NULL AND title != ''")
title_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM documents WHERE abstract IS NOT NULL AND abstract != ''")
abstract_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM documents WHERE doi IS NOT NULL AND doi != ''")
doi_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM documents WHERE year IS NOT NULL")
year_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM documents WHERE authors IS NOT NULL AND authors != ''")
authors_count = cursor.fetchone()[0]

print(f"Total records: {total}")
print(f"  Title coverage: {title_count}/{total} ({title_count/total*100:.1f}%)")
print(f"  Abstract coverage: {abstract_count}/{total} ({abstract_count/total*100:.1f}%)")
print(f"  DOI coverage: {doi_count}/{total} ({doi_count/total*100:.1f}%)")
print(f"  Year coverage: {year_count}/{total} ({year_count/total*100:.1f}%)")
print(f"  Authors coverage: {authors_count}/{total} ({authors_count/total*100:.1f}%)")

# Year distribution
print("\n" + "=" * 80)
print("YEAR DISTRIBUTION")
print("=" * 80)
cursor.execute("""
    SELECT year, COUNT(*) 
    FROM documents 
    WHERE year IS NOT NULL 
    GROUP BY year 
    ORDER BY year DESC 
    LIMIT 10
""")
for year, count in cursor.fetchall():
    print(f"  {year}: {count} records")

# Check for duplicates (by DOI)
print("\n" + "=" * 80)
print("DUPLICATE CHECK (by DOI)")
print("=" * 80)
cursor.execute("""
    SELECT doi, COUNT(*) as cnt, GROUP_CONCAT(DISTINCT source) as sources
    FROM documents 
    WHERE doi IS NOT NULL AND doi != ''
    GROUP BY doi 
    HAVING cnt > 1
""")
duplicates = cursor.fetchall()
if duplicates:
    print(f"Found {len(duplicates)} duplicate DOIs:")
    for doi, count, sources in duplicates[:5]:
        print(f"  DOI: {doi} | Count: {count} | Sources: {sources}")
else:
    print("  No duplicates found by DOI")

conn.close()

