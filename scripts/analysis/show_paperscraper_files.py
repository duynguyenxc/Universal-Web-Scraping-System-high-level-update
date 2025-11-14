"""Show all files created from paperscraper test."""
from pathlib import Path
import json

print("=" * 80)
print("PAPERSCRAPER DATA FILES")
print("=" * 80)

# Database
db_path = Path("data/test_paperscraper.sqlite")
if db_path.exists():
    size_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"\n[1] Database: {db_path}")
    print(f"    Size: {size_mb:.2f} MB")
    print(f"    Location: {db_path.absolute()}")
else:
    print(f"\n[1] Database: NOT FOUND")

# Export file
export_path = Path("data/paperscraper_export.jsonl")
if export_path.exists():
    line_count = sum(1 for _ in export_path.open())
    size_mb = export_path.stat().st_size / (1024 * 1024)
    print(f"\n[2] Export file (JSONL): {export_path}")
    print(f"    Size: {size_mb:.2f} MB")
    print(f"    Records: {line_count}")
    print(f"    Location: {export_path.absolute()}")
    
    # Show first record
    print(f"\n    First record preview:")
    with export_path.open() as f:
        first_line = f.readline()
        if first_line:
            record = json.loads(first_line)
            print(f"      Title: {record.get('title', 'N/A')[:60]}...")
            print(f"      DOI: {record.get('doi', 'N/A')}")
            print(f"      Source: {record.get('source', 'N/A')}")
            print(f"      Abstract: {len(record.get('abstract', '') or '')} chars")
else:
    print(f"\n[2] Export file: NOT FOUND")
    print(f"    To create: python -m src.uwss.cli export --db {db_path} --out {export_path}")

# PDF directory
pdf_dir = Path("data/paperscraper_pdfs")
if pdf_dir.exists():
    pdf_files = list(pdf_dir.glob("*.pdf"))
    total_size = sum(f.stat().st_size for f in pdf_files) / (1024 * 1024)
    print(f"\n[3] PDF files directory: {pdf_dir}")
    print(f"    PDF files: {len(pdf_files)}")
    print(f"    Total size: {total_size:.2f} MB")
    print(f"    Location: {pdf_dir.absolute()}")
    
    if pdf_files:
        print(f"\n    Sample PDFs:")
        for pdf in pdf_files[:5]:
            size_kb = pdf.stat().st_size / 1024
            print(f"      - {pdf.name} ({size_kb:.1f} KB)")
else:
    print(f"\n[3] PDF files directory: NOT FOUND")
    print(f"    To create: python -m src.uwss.cli fetch --db {db_path} --outdir {pdf_dir} --limit 20")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"All data is stored in:")
print(f"  1. Database: {db_path.absolute()}")
print(f"  2. Export file: {export_path.absolute()}")
if pdf_dir.exists():
    print(f"  3. PDF files: {pdf_dir.absolute()}")
print("\nTo view data:")
print(f"  - Open database: sqlite3 {db_path}")
print(f"  - View export: cat {export_path} | head -1 | python -m json.tool")
print(f"  - List PDFs: ls {pdf_dir}")


