"""Test new sources: Crossref, OpenAlex, Semantic Scholar"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime

print("=" * 80)
print("TESTING NEW SOURCES - Crossref, OpenAlex, Semantic Scholar")
print("=" * 80)
print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

db_path = Path("data/test_new_sources.sqlite")

# Remove old test database
if db_path.exists():
    db_path.unlink()

print("[STEP 1] Testing Crossref (habanero library)")
print("-" * 80)

