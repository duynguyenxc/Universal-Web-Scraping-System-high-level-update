"""Check paperscraper data in database and export to files."""
import sqlite3
import json
from pathlib import Path

db_path = Path("data/test_paperscraper.sqlite")

if not db_path.exists():
    print(f"Database not found: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check total documents
cursor.execute("SELECT COUNT(*) FROM documents")
total = cursor.fetchone()[0]
print(f"Total documents in database: {total}")

# Check by source
cursor.execute("SELECT source, COUNT(*) FROM documents GROUP BY source")
sources = dict(cursor.fetchall())
print(f"\nBy source: {sources}")

# Check metadata quality
cursor.execute("SELECT COUNT(*) FROM documents WHERE abstract IS NOT NULL AND abstract != ''")
with_abstract = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM documents WHERE pdf_url IS NOT NULL AND pdf_url != ''")
with_pdf_url = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM documents WHERE doi IS NOT NULL AND doi != ''")
with_doi = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM documents WHERE local_path IS NOT NULL AND local_path != ''")
with_pdf_file = cursor.fetchone()[0]

print(f"\nMetadata quality:")
print(f"  With abstract: {with_abstract}/{total} ({with_abstract/total*100:.1f}%)")
print(f"  With PDF URL: {with_pdf_url}/{total} ({with_pdf_url/total*100:.1f}%)")
print(f"  With DOI: {with_doi}/{total} ({with_doi/total*100:.1f}%)")
print(f"  With PDF file downloaded: {with_pdf_file}/{total} ({with_pdf_file/total*100:.1f}%)")

# Show sample documents
print("\n" + "="*80)
print("Sample documents:")
print("="*80)
cursor.execute("""
    SELECT id, title, doi, pdf_url, source, abstract
    FROM documents 
    LIMIT 5
""")
for row in cursor.fetchall():
    doc_id, title, doi, pdf_url, source, abstract = row
    print(f"\nID: {doc_id}")
    print(f"  Title: {title[:70]}...")
    print(f"  DOI: {doi}")
    print(f"  Source: {source}")
    print(f"  PDF URL: {pdf_url or 'None'}")
    print(f"  Abstract length: {len(abstract or '')} chars")

conn.close()

print("\n" + "="*80)
print("To export data to files, run:")
print("="*80)
print(f"  python -m src.uwss.cli export --db {db_path} --out data/paperscraper_export.jsonl")
print(f"\nTo fetch PDF files (for arXiv papers), run:")
print(f"  python -m src.uwss.cli arxiv-fetch-pdf --db {db_path} --outdir data/paperscraper_pdfs --limit 50")


