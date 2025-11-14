"""Create additional viewer files for easy inspection."""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path("data/test_new_sources.sqlite")
OUTPUT_DIR = Path("data/reports")
OUTPUT_DIR.mkdir(exist_ok=True)

def create_sample_viewer():
    """Create a simple text file with sample records for quick viewing."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    output = []
    output.append("=" * 80)
    output.append("SAMPLE RECORDS - QUICK VIEW")
    output.append("=" * 80)
    output.append("")
    
    sources = ["crossref", "openalex", "semantic_scholar"]
    
    for source in sources:
        output.append(f"\n{'=' * 80}")
        output.append(f"SOURCE: {source.upper()}")
        output.append(f"{'=' * 80}\n")
        
        cursor.execute("""
            SELECT title, abstract, pdf_url, doi, year, authors, venue, source_url
            FROM documents
            WHERE source = ?
            LIMIT 10
        """, (source,))
        
        records = cursor.fetchall()
        output.append(f"Total samples shown: {len(records)}\n")
        
        for i, rec in enumerate(records, 1):
            output.append(f"\n--- Record {i} ---")
            output.append(f"Title: {rec['title']}")
            output.append(f"Year: {rec['year']}")
            output.append(f"DOI: {rec['doi'] or 'None'}")
            output.append(f"PDF URL: {rec['pdf_url'] or 'None'}")
            output.append(f"Venue: {rec['venue'] or 'None'}")
            if rec['authors']:
                try:
                    authors = json.loads(rec['authors'])
                    output.append(f"Authors: {', '.join(authors[:3])}{'...' if len(authors) > 3 else ''}")
                except:
                    output.append(f"Authors: {rec['authors'][:100]}")
            else:
                output.append("Authors: None")
            if rec['abstract']:
                abstract = rec['abstract'][:300] + "..." if len(rec['abstract']) > 300 else rec['abstract']
                output.append(f"Abstract: {abstract}")
            else:
                output.append("Abstract: None")
            output.append("")
    
    output_file = OUTPUT_DIR / "sample_records_view.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    
    print(f"Created sample viewer: {output_file}")
    conn.close()

def create_issues_report():
    """Create a report specifically for issues."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    output = []
    output.append("=" * 80)
    output.append("ISSUES REPORT")
    output.append("=" * 80)
    output.append("")
    
    # HTML tags in abstracts
    output.append("\n1. HTML TAGS IN ABSTRACTS")
    output.append("-" * 80)
    cursor.execute("""
        SELECT source, title, abstract
        FROM documents
        WHERE abstract LIKE '%<%' AND abstract LIKE '%>%'
        ORDER BY source
    """)
    html_issues = cursor.fetchall()
    
    if html_issues:
        output.append(f"Found {len(html_issues)} records with HTML tags:\n")
        for rec in html_issues:
            output.append(f"Source: {rec['source']}")
            output.append(f"Title: {rec['title'][:80]}")
            abstract_preview = rec['abstract'][:200].replace('\n', ' ')
            output.append(f"Abstract preview: {abstract_preview}...")
            output.append("")
    else:
        output.append("No HTML tags found!\n")
    
    # Empty PDF URLs
    output.append("\n2. EMPTY PDF URLS")
    output.append("-" * 80)
    cursor.execute("""
        SELECT source, title, pdf_url
        FROM documents
        WHERE pdf_url = ''
        ORDER BY source
    """)
    empty_pdf = cursor.fetchall()
    
    if empty_pdf:
        output.append(f"Found {len(empty_pdf)} records with empty PDF URLs:\n")
        for rec in empty_pdf:
            output.append(f"Source: {rec['source']}")
            output.append(f"Title: {rec['title'][:80]}")
            output.append(f"PDF URL value: {repr(rec['pdf_url'])}")
            output.append("")
    else:
        output.append("No empty PDF URLs found!\n")
    
    # Missing abstracts
    output.append("\n3. MISSING ABSTRACTS")
    output.append("-" * 80)
    cursor.execute("""
        SELECT source, COUNT(*) as count
        FROM documents
        WHERE abstract IS NULL OR abstract = ''
        GROUP BY source
    """)
    missing_abstracts = cursor.fetchall()
    
    if missing_abstracts:
        for rec in missing_abstracts:
            output.append(f"{rec['source']}: {rec['count']} records without abstract")
    else:
        output.append("All records have abstracts!")
    
    output_file = OUTPUT_DIR / "issues_report.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    
    print(f"Created issues report: {output_file}")
    conn.close()

def create_statistics_summary():
    """Create a statistics summary file."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            source,
            COUNT(*) as total,
            SUM(CASE WHEN abstract IS NOT NULL AND abstract != '' THEN 1 ELSE 0 END) as has_abstract,
            SUM(CASE WHEN pdf_url IS NOT NULL AND pdf_url != '' THEN 1 ELSE 0 END) as has_pdf_url,
            SUM(CASE WHEN doi IS NOT NULL AND doi != '' THEN 1 ELSE 0 END) as has_doi,
            SUM(CASE WHEN authors IS NOT NULL AND authors != '' THEN 1 ELSE 0 END) as has_authors,
            SUM(CASE WHEN year IS NOT NULL THEN 1 ELSE 0 END) as has_year,
            SUM(CASE WHEN venue IS NOT NULL AND venue != '' THEN 1 ELSE 0 END) as has_venue
        FROM documents
        GROUP BY source
    """)
    
    output = []
    output.append("=" * 80)
    output.append("STATISTICS SUMMARY")
    output.append("=" * 80)
    output.append("")
    
    for row in cursor.fetchall():
        source, total, has_abstract, has_pdf_url, has_doi, has_authors, has_year, has_venue = row
        output.append(f"\n{source.upper()}")
        output.append("-" * 80)
        output.append(f"Total records: {total}")
        output.append(f"  - Abstract: {has_abstract} ({has_abstract/total*100:.1f}%)")
        output.append(f"  - PDF URL: {has_pdf_url} ({has_pdf_url/total*100:.1f}%)")
        output.append(f"  - DOI: {has_doi} ({has_doi/total*100:.1f}%)")
        output.append(f"  - Authors: {has_authors} ({has_authors/total*100:.1f}%)")
        output.append(f"  - Year: {has_year} ({has_year/total*100:.1f}%)")
        output.append(f"  - Venue: {has_venue} ({has_venue/total*100:.1f}%)")
    
    output_file = OUTPUT_DIR / "statistics_summary.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    
    print(f"Created statistics summary: {output_file}")
    conn.close()

if __name__ == "__main__":
    print("Creating viewer files...\n")
    create_sample_viewer()
    create_issues_report()
    create_statistics_summary()
    print(f"\nAll viewer files created in: {OUTPUT_DIR}")

