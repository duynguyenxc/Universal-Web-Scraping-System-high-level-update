"""Quick analysis of new sources test results."""

import json
import sqlite3
from pathlib import Path

def quick_stats():
    """Get quick statistics from the database."""
    db_path = Path("data/test_new_sources.sqlite")

    if not db_path.exists():
        print("Database not found!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get counts by source
    cursor.execute("SELECT source, COUNT(*) as count FROM documents GROUP BY source ORDER BY source")
    sources = cursor.fetchall()

    print("=== DATABASE STATISTICS ===")
    total = 0
    for source, count in sources:
        print(f"{source}: {count} records")
        total += count
    print(f"Total: {total} records\n")

    # Get metadata quality
    print("=== METADATA QUALITY ===")
    for source, _ in sources:
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN abstract IS NOT NULL AND abstract != '' THEN 1 ELSE 0 END) as has_abstract,
                SUM(CASE WHEN pdf_url IS NOT NULL AND pdf_url != '' THEN 1 ELSE 0 END) as has_pdf_url,
                SUM(CASE WHEN doi IS NOT NULL AND doi != '' THEN 1 ELSE 0 END) as has_doi,
                SUM(CASE WHEN authors IS NOT NULL AND authors != '' THEN 1 ELSE 0 END) as has_authors,
                SUM(CASE WHEN year IS NOT NULL THEN 1 ELSE 0 END) as has_year
            FROM documents WHERE source = ?
        """, (source,))

        row = cursor.fetchone()
        if row:
            total, has_abstract, has_pdf_url, has_doi, has_authors, has_year = row
            if total > 0:
                print(f"\n{source.upper()}:")
                print(".1f")
                print(".1f")
                print(".1f")
                print(".1f")
                print(".1f")

    # Check for issues
    print("\n=== ISSUES CHECK ===")

    # HTML tags in abstracts
    cursor.execute("""
        SELECT source, COUNT(*) as count
        FROM documents
        WHERE abstract LIKE '%<%' AND abstract LIKE '%>%'
        GROUP BY source
    """)
    html_issues = cursor.fetchall()
    if html_issues:
        print("HTML tags in abstracts:")
        for source, count in html_issues:
            print(f"  {source}: {count} records")
    else:
        print("No HTML tags found in abstracts")

    # Empty PDF URLs
    cursor.execute("""
        SELECT source, COUNT(*) as count
        FROM documents
        WHERE pdf_url = ''
        GROUP BY source
    """)
    empty_pdf_issues = cursor.fetchall()
    if empty_pdf_issues:
        print("Empty PDF URLs:")
        for source, count in empty_pdf_issues:
            print(f"  {source}: {count} records")
    else:
        print("No empty PDF URLs found")

    conn.close()

def check_pdf_files():
    """Check downloaded PDF files."""
    print("\n=== PDF FILES DOWNLOADED ===")

    # Check new source directories
    pdf_dirs = [
        Path("data/crossref_pdfs"),
        Path("data/openalex_pdfs"),
        Path("data/semantic_scholar_pdfs")
    ]

    total_new_pdfs = 0
    for pdf_dir in pdf_dirs:
        if pdf_dir.exists():
            pdf_files = list(pdf_dir.glob("*.pdf"))
            if pdf_files:
                print(f"{pdf_dir.name}: {len(pdf_files)} files")
                total_new_pdfs += len(pdf_files)
            else:
                print(f"{pdf_dir.name}: No PDF files")
        else:
            print(f"{pdf_dir.name}: Directory not found")

    if total_new_pdfs == 0:
        print("No new PDFs downloaded from the 3 new sources")

    # Check existing PDFs
    paperscraper_dir = Path("data/paperscraper_pdfs")
    if paperscraper_dir.exists():
        existing_pdfs = list(paperscraper_dir.glob("*.pdf"))
        print(f"\nExisting PDFs (from previous tests): {len(existing_pdfs)} files")

def sample_records():
    """Show sample records from JSONL."""
    jsonl_path = Path("data/new_sources_final.jsonl")

    if not jsonl_path.exists():
        print("JSONL file not found!")
        return

    print("\n=== SAMPLE RECORDS FROM JSONL ===")

    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= 10:  # Show records 11-15
                try:
                    data = json.loads(line.strip())
                    print(f"\nRecord {i+1}:")
                    print(f"  Source: {data.get('source')}")
                    print(f"  Title: {data.get('title', 'N/A')[:80]}...")
                    print(f"  Year: {data.get('year', 'N/A')}")
                    print(f"  DOI: {data.get('doi', 'N/A')}")
                    print(f"  Relevance Score: {data.get('relevance_score', 'N/A')}")

                    if data.get('abstract'):
                        abstract = data['abstract'][:100].replace('<jats:p>', '').replace('</jats:p>', '').replace('<jats:title>', '').replace('</jats:title>', '')
                        print(f"  Abstract: {abstract}...")
                    else:
                        print("  Abstract: None")

                    pdf_path = data.get('pdf_path')
                    if pdf_path and pdf_path != 'None':
                        print(f"  PDF Downloaded: Yes ({pdf_path})")
                    else:
                        print("  PDF Downloaded: No")

                    if i >= 14:  # Show 5 records
                        break

                except Exception as e:
                    print(f"Error parsing record {i+1}: {e}")
                    break

if __name__ == "__main__":
    quick_stats()
    check_pdf_files()
    sample_records()
