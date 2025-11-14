"""Full pipeline test: Discovery → Export → Fetch PDFs → Show Results"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime

print("=" * 80)
print("FULL PIPELINE TEST - Paperscraper Integration")
print("=" * 80)
print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

db_path = Path("data/test_paperscraper.sqlite")
export_path = Path("data/paperscraper_export.jsonl")
pdf_dir = Path("data/paperscraper_pdfs")

# Step 1: Check database
print("[STEP 1] Database Statistics")
print("-" * 80)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
    SELECT 
        source,
        COUNT(*) as total,
        SUM(CASE WHEN year IS NOT NULL THEN 1 ELSE 0 END) as with_year,
        SUM(CASE WHEN abstract IS NOT NULL AND abstract != '' THEN 1 ELSE 0 END) as with_abstract,
        SUM(CASE WHEN pdf_url IS NOT NULL AND pdf_url != '' THEN 1 ELSE 0 END) as with_pdf_url,
        SUM(CASE WHEN doi IS NOT NULL AND doi != '' THEN 1 ELSE 0 END) as with_doi,
        SUM(CASE WHEN local_path IS NOT NULL THEN 1 ELSE 0 END) as pdf_downloaded
    FROM documents
    GROUP BY source
    ORDER BY source
""")

print(f"{'Source':<30} {'Total':>6} {'Year':>6} {'Abstract':>9} {'PDF URL':>8} {'DOI':>6} {'PDF Downloaded':>15}")
print("-" * 80)
for row in cursor.fetchall():
    source, total, with_year, with_abstract, with_pdf_url, with_doi, pdf_downloaded = row
    if source == "paperscraper_pubmed":
        source_display = "[PubMed] via paperscraper"
    elif source == "paperscraper_arxiv":
        source_display = "[arXiv] via paperscraper"
    else:
        source_display = f"[{source}]"
    print(f"{source_display:<30} {total:>6} {with_year:>6} {with_abstract:>9} {with_pdf_url:>8} {with_doi:>6} {pdf_downloaded:>15}")

conn.close()

# Step 2: Sample metadata
print("\n[STEP 2] Sample Metadata (5 records per source)")
print("-" * 80)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

for source in ["paperscraper_pubmed", "paperscraper_arxiv"]:
    cursor.execute("""
        SELECT id, title, year, doi, pdf_url, abstract, source
        FROM documents
        WHERE source = ?
        ORDER BY id DESC
        LIMIT 5
    """, (source,))
    
    source_display = "PubMed" if source == "paperscraper_pubmed" else "arXiv"
    print(f"\n{source_display} Samples:")
    print("-" * 80)
    
    for row in cursor.fetchall():
        doc_id, title, year, doi, pdf_url, abstract, src = row
        print(f"\n  ID: {doc_id}")
        print(f"  Title: {title[:70]}..." if title and len(title) > 70 else f"  Title: {title}")
        print(f"  Year: {year if year else '[None]'}")
        print(f"  DOI: {doi if doi else '[None]'}")
        print(f"  PDF URL: {'[Available]' if pdf_url else '[None]'}")
        print(f"  Abstract: {'[Available (' + str(len(abstract)) + ' chars)]' if abstract else '[None]'}")

conn.close()

# Step 3: PDF files
print("\n[STEP 3] PDF Files Downloaded")
print("-" * 80)
if pdf_dir.exists():
    pdf_files = list(pdf_dir.glob("*.pdf"))
    print(f"Total PDF files: {len(pdf_files)}")
    
    if pdf_files:
        print("\nSample PDF files (first 10):")
        for i, pdf_file in enumerate(pdf_files[:10], 1):
            size_mb = pdf_file.stat().st_size / (1024 * 1024)
            print(f"  {i}. {pdf_file.name} ({size_mb:.2f} MB)")
        
        if len(pdf_files) > 10:
            print(f"  ... and {len(pdf_files) - 10} more files")
        
        # Check database for PDF paths
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT source, COUNT(*) 
            FROM documents 
            WHERE local_path IS NOT NULL 
            GROUP BY source
        """)
        print("\nPDFs in database by source:")
        for source, count in cursor.fetchall():
            source_display = "PubMed" if source == "paperscraper_pubmed" else "arXiv"
            print(f"  {source_display}: {count} PDFs")
        conn.close()
    else:
        print("  [No PDF files found]")
else:
    print(f"  [PDF directory not found: {pdf_dir}]")

# Step 4: Export file check
print("\n[STEP 4] Export File Analysis")
print("-" * 80)
if export_path.exists():
    with open(export_path, 'r', encoding='utf-8') as f:
        records = [json.loads(line) for line in f if line.strip()]
    
    print(f"Total records in export: {len(records)}")
    
    # Check year field
    with_year = sum(1 for r in records if r.get('year'))
    print(f"Records with year: {with_year} ({with_year/len(records)*100:.1f}%)")
    
    # Check abstract field
    with_abstract = sum(1 for r in records if r.get('abstract'))
    print(f"Records with abstract: {with_abstract} ({with_abstract/len(records)*100:.1f}%)")
    
    # Check PDF URL
    with_pdf_url = sum(1 for r in records if r.get('pdf_url'))
    print(f"Records with PDF URL: {with_pdf_url} ({with_pdf_url/len(records)*100:.1f}%)")
    
    # Sample record
    if records:
        print("\nSample export record:")
        sample = records[0]
        print(f"  Source: {sample.get('source')}")
        print(f"  Year: {sample.get('year', 'None')}")
        print(f"  Title: {sample.get('title', '')[:60]}...")
        print(f"  Abstract: {'[Yes]' if sample.get('abstract') else '[No]'}")
        print(f"  PDF URL: {'[Yes]' if sample.get('pdf_url') else '[No]'}")
else:
    print("  [Export file not found]")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)

