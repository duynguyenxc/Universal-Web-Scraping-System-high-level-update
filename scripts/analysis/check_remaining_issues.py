"""Check remaining issues after fixes."""

import sqlite3
from pathlib import Path

DB_PATH = Path("data/test_new_sources.sqlite")

if not DB_PATH.exists():
    print(f"Database not found: {DB_PATH}")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Check HTML tags
print("=== HTML TAGS IN ABSTRACTS ===\n")
cursor.execute("""
    SELECT source, abstract
    FROM documents
    WHERE abstract LIKE '%<%' AND abstract LIKE '%>%'
    LIMIT 5
""")
rows = cursor.fetchall()
if rows:
    for source, abstract in rows:
        print(f"Source: {source}")
        print(f"Abstract (first 300 chars): {abstract[:300]}")
        print("-" * 60)
else:
    print("No HTML tags found!")

# Check empty PDF URLs
print("\n=== EMPTY PDF URLS ===\n")
cursor.execute("""
    SELECT source, pdf_url, title
    FROM documents
    WHERE pdf_url = ''
    LIMIT 5
""")
rows = cursor.fetchall()
if rows:
    for source, pdf_url, title in rows:
        print(f"Source: {source}")
        print(f"PDF URL: {repr(pdf_url)}")
        print(f"Title: {title[:80]}")
        print("-" * 60)
else:
    print("No empty PDF URLs found!")

conn.close()

