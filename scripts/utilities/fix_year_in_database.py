"""Fix year field in existing database by extracting from date."""
import sqlite3
import re
from pathlib import Path

db_path = Path("data/test_paperscraper.sqlite")

print("=" * 80)
print("FIXING YEAR IN DATABASE")
print("=" * 80)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if we can get date from paperscraper again
# But actually, we don't have date stored in database
# So we need to re-run discovery or update from source

# Alternative: Check if we can extract from existing data
# But we don't have date field in Document model

print("\n[INFO] Year extraction works in mapper, but existing data was inserted before mapper fix.")
print("To fix: Re-run discovery to get year from date field.")
print("\nOr we can try to update from source URLs...")

# Check if we have any way to get date back
cursor.execute("SELECT id, source, doi FROM documents WHERE year IS NULL LIMIT 5")
rows = cursor.fetchall()

print(f"\nSample documents without year:")
for doc_id, source, doi in rows:
    print(f"  ID {doc_id}: source={source}, doi={doi}")

conn.close()

print("\n" + "=" * 80)
print("SOLUTION")
print("=" * 80)
print("Re-run paperscraper discovery to get year from date field:")
print("  python -m src.uwss.cli paperscraper-discover --source pubmed --max 100")
print("  python -m src.uwss.cli paperscraper-discover --source arxiv --max 100")


