"""Check PDF status in database."""
import sqlite3
from pathlib import Path

db_path = "data/phase1_full_test.sqlite"

if not Path(db_path).exists():
    print(f"Database not found: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Count records with PDF URL
cursor.execute('SELECT COUNT(*) FROM documents WHERE pdf_url IS NOT NULL AND pdf_url != ""')
pdf_url_count = cursor.fetchone()[0]

# Count records with local PDF
cursor.execute('SELECT COUNT(*) FROM documents WHERE local_path IS NOT NULL AND local_path != ""')
local_pdf_count = cursor.fetchone()[0]

# Count by source
cursor.execute("""
    SELECT source, 
           COUNT(*) as total,
           SUM(CASE WHEN pdf_url IS NOT NULL AND pdf_url != '' THEN 1 ELSE 0 END) as with_pdf_url,
           SUM(CASE WHEN local_path IS NOT NULL AND local_path != '' THEN 1 ELSE 0 END) as with_local_pdf
    FROM documents 
    GROUP BY source
""")
sources = cursor.fetchall()

print("="*80)
print("PDF STATUS CHECK")
print("="*80)
print(f"\nTotal records with PDF URL: {pdf_url_count}")
print(f"Total records with local PDF: {local_pdf_count}")

print("\nBy Source:")
for source, total, with_pdf_url, with_local_pdf in sources:
    source_name = source if source else "unknown"
    print(f"\n  {source_name}:")
    print(f"    Total: {total}")
    print(f"    With PDF URL: {with_pdf_url}/{total} ({with_pdf_url/total*100:.1f}%)")
    print(f"    With Local PDF: {with_local_pdf}/{total} ({with_local_pdf/total*100:.1f}%)")

# Sample records with PDF URL
cursor.execute("""
    SELECT source, title, pdf_url, local_path 
    FROM documents 
    WHERE pdf_url IS NOT NULL AND pdf_url != ''
    LIMIT 5
""")
samples = cursor.fetchall()

if samples:
    print("\n\nSample records with PDF URL:")
    for source, title, pdf_url, local_path in samples:
        print(f"\n  Source: {source}")
        print(f"  Title: {title[:60]}..." if title and len(title) > 60 else f"  Title: {title}")
        print(f"  PDF URL: {pdf_url[:60]}...")
        print(f"  Local PDF: {local_path if local_path else 'NOT DOWNLOADED'}")

conn.close()

