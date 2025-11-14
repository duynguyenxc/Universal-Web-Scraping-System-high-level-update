"""Check for issues in export file vs database."""
import json
import sqlite3
from pathlib import Path

db_path = Path("data/test_paperscraper.sqlite")
export_path = Path("data/paperscraper_export.jsonl")

print("=" * 80)
print("CHECKING FOR ISSUES")
print("=" * 80)

# Check database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check abstract in database
cursor.execute("SELECT COUNT(*) FROM documents WHERE abstract IS NOT NULL AND abstract != ''")
db_with_abstract = cursor.fetchone()[0]

cursor.execute("SELECT id, title, abstract FROM documents WHERE abstract IS NOT NULL AND abstract != '' LIMIT 3")
db_samples = cursor.fetchall()

print(f"\n[Database] Documents with abstract: {db_with_abstract}/200")
print("Sample from database:")
for doc_id, title, abstract in db_samples:
    print(f"  ID {doc_id}: {title[:50]}... | Abstract: {len(abstract)} chars")

# Check export file
export_lines = []
with open(export_path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            try:
                export_lines.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"  ERROR: Invalid JSON on line: {e}")

print(f"\n[Export File] Total records: {len(export_lines)}")

# Check abstract in export
export_with_abstract = sum(1 for r in export_lines if r.get('abstract') and r.get('abstract').strip())
print(f"  Records with abstract: {export_with_abstract}/{len(export_lines)}")

# Check for missing fields
issues = []
for i, record in enumerate(export_lines[:10], 1):
    if not record.get('abstract'):
        issues.append(f"Record {i} (ID {record.get('id')}): Missing abstract")
    if not record.get('source_url') and not record.get('landing_url'):
        issues.append(f"Record {i} (ID {record.get('id')}): Missing URLs")
    if record.get('year') is None and record.get('date') is None:
        issues.append(f"Record {i} (ID {record.get('id')}): Missing year/date")

if issues:
    print("\n[ISSUES FOUND]:")
    for issue in issues[:10]:
        print(f"  - {issue}")
else:
    print("\n[No major issues found in first 10 records]")

# Compare database vs export
print("\n[Comparison] Database vs Export:")
print(f"  Database abstracts: {db_with_abstract}")
print(f"  Export abstracts: {export_with_abstract}")
if db_with_abstract > export_with_abstract:
    print(f"  ⚠️  WARNING: Export missing {db_with_abstract - export_with_abstract} abstracts!")

# Check PDF URLs
cursor.execute("SELECT COUNT(*) FROM documents WHERE pdf_url IS NOT NULL AND pdf_url != ''")
db_with_pdf_url = cursor.fetchone()[0]

export_with_pdf_url = sum(1 for r in export_lines if r.get('pdf_url'))
print(f"\n  Database PDF URLs: {db_with_pdf_url}")
print(f"  Export PDF URLs: {export_with_pdf_url}")

conn.close()

print("\n" + "=" * 80)
print("RECOMMENDATION")
print("=" * 80)
if db_with_abstract > export_with_abstract:
    print("⚠️  Export file is missing abstract data!")
    print("   Re-run export command to get latest data:")
    print(f"   python -m src.uwss.cli export --db {db_path} --out {export_path}")


