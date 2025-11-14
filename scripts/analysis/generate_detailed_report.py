"""Generate detailed report files for user review."""

import json
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data/test_new_sources.sqlite")
OUTPUT_DIR = Path("data/reports")
OUTPUT_DIR.mkdir(exist_ok=True)

def generate_json_report():
    """Generate detailed JSON report."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all records
    cursor.execute("SELECT * FROM documents ORDER BY source, id")
    rows = cursor.fetchall()
    
    records = []
    for row in rows:
        record = dict(row)
        records.append(record)
    
    # Statistics
    cursor.execute("""
        SELECT 
            source,
            COUNT(*) as total,
            SUM(CASE WHEN abstract IS NOT NULL AND abstract != '' THEN 1 ELSE 0 END) as has_abstract,
            SUM(CASE WHEN pdf_url IS NOT NULL AND pdf_url != '' THEN 1 ELSE 0 END) as has_pdf_url,
            SUM(CASE WHEN doi IS NOT NULL AND doi != '' THEN 1 ELSE 0 END) as has_doi,
            SUM(CASE WHEN authors IS NOT NULL AND authors != '' THEN 1 ELSE 0 END) as has_authors,
            SUM(CASE WHEN year IS NOT NULL THEN 1 ELSE 0 END) as has_year,
            SUM(CASE WHEN venue IS NOT NULL AND venue != '' THEN 1 ELSE 0 END) as has_venue,
            SUM(CASE WHEN abstract LIKE '%<%' AND abstract LIKE '%>%' THEN 1 ELSE 0 END) as html_in_abstract,
            SUM(CASE WHEN pdf_url = '' THEN 1 ELSE 0 END) as empty_pdf_url
        FROM documents
        GROUP BY source
    """)
    stats = []
    for row in cursor.fetchall():
        stats.append(dict(row))
    
    report = {
        "generated_at": datetime.now().isoformat(),
        "database": str(DB_PATH),
        "total_records": len(records),
        "statistics_by_source": stats,
        "records": records
    }
    
    output_file = OUTPUT_DIR / "detailed_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"Generated JSON report: {output_file}")
    conn.close()

def generate_markdown_report():
    """Generate Markdown report."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Statistics
    cursor.execute("""
        SELECT 
            source,
            COUNT(*) as total,
            SUM(CASE WHEN abstract IS NOT NULL AND abstract != '' THEN 1 ELSE 0 END) as has_abstract,
            SUM(CASE WHEN pdf_url IS NOT NULL AND pdf_url != '' THEN 1 ELSE 0 END) as has_pdf_url,
            SUM(CASE WHEN doi IS NOT NULL AND doi != '' THEN 1 ELSE 0 END) as has_doi,
            SUM(CASE WHEN authors IS NOT NULL AND authors != '' THEN 1 ELSE 0 END) as has_authors,
            SUM(CASE WHEN year IS NOT NULL THEN 1 ELSE 0 END) as has_year,
            SUM(CASE WHEN venue IS NOT NULL AND venue != '' THEN 1 ELSE 0 END) as has_venue,
            SUM(CASE WHEN abstract LIKE '%<%' AND abstract LIKE '%>%' THEN 1 ELSE 0 END) as html_in_abstract,
            SUM(CASE WHEN pdf_url = '' THEN 1 ELSE 0 END) as empty_pdf_url
        FROM documents
        GROUP BY source
    """)
    stats = [dict(row) for row in cursor.fetchall()]
    
    # Sample records by source
    samples = {}
    for source in ["crossref", "openalex", "semantic_scholar"]:
        cursor.execute("""
            SELECT title, abstract, pdf_url, doi, year, authors, venue
            FROM documents
            WHERE source = ?
            LIMIT 5
        """, (source,))
        samples[source] = [dict(row) for row in cursor.fetchall()]
    
    # Issues
    cursor.execute("""
        SELECT source, title, abstract
        FROM documents
        WHERE abstract LIKE '%<%' AND abstract LIKE '%>%'
        LIMIT 10
    """)
    html_issues = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("""
        SELECT source, title, pdf_url
        FROM documents
        WHERE pdf_url = ''
        LIMIT 10
    """)
    empty_pdf_issues = [dict(row) for row in cursor.fetchall()]
    
    # Generate Markdown
    md = f"""# Scale Test Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Database:** `{DB_PATH}`

## Summary Statistics

| Source | Total | Abstract | PDF URL | DOI | Authors | Year | Venue | HTML Issues | Empty PDF |
|--------|-------|----------|---------|-----|---------|------|-------|-------------|-----------|
"""
    
    for stat in stats:
        total = stat['total']
        md += f"| {stat['source']} | {total} | "
        md += f"{stat['has_abstract']} ({stat['has_abstract']/total*100:.1f}%) | "
        md += f"{stat['has_pdf_url']} ({stat['has_pdf_url']/total*100:.1f}%) | "
        md += f"{stat['has_doi']} ({stat['has_doi']/total*100:.1f}%) | "
        md += f"{stat['has_authors']} ({stat['has_authors']/total*100:.1f}%) | "
        md += f"{stat['has_year']} ({stat['has_year']/total*100:.1f}%) | "
        md += f"{stat['has_venue']} ({stat['has_venue']/total*100:.1f}%) | "
        md += f"{stat['html_in_abstract']} | {stat['empty_pdf_url']} |\n"
    
    md += "\n## Sample Records by Source\n\n"
    
    for source, records in samples.items():
        md += f"### {source.upper()}\n\n"
        for i, rec in enumerate(records, 1):
            md += f"#### Sample {i}\n\n"
            md += f"- **Title:** {rec['title']}\n"
            md += f"- **Year:** {rec['year']}\n"
            md += f"- **DOI:** {rec['doi'] or 'None'}\n"
            md += f"- **PDF URL:** {rec['pdf_url'] or 'None'}\n"
            md += f"- **Venue:** {rec['venue'] or 'None'}\n"
            if rec['abstract']:
                abstract_preview = rec['abstract'][:200] + "..." if len(rec['abstract']) > 200 else rec['abstract']
                md += f"- **Abstract:** {abstract_preview}\n"
            else:
                md += f"- **Abstract:** None\n"
            md += "\n"
    
    if html_issues:
        md += "\n## HTML Tags in Abstracts (Issues)\n\n"
        for issue in html_issues:
            md += f"### {issue['source']}: {issue['title'][:80]}\n\n"
            abstract_preview = issue['abstract'][:300] + "..." if len(issue['abstract']) > 300 else issue['abstract']
            md += f"```\n{abstract_preview}\n```\n\n"
    
    if empty_pdf_issues:
        md += "\n## Empty PDF URLs (Issues)\n\n"
        for issue in empty_pdf_issues:
            md += f"- **{issue['source']}:** {issue['title'][:80]}\n"
            md += f"  - PDF URL: `{repr(issue['pdf_url'])}`\n\n"
    
    output_file = OUTPUT_DIR / "detailed_report.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(md)
    
    print(f"Generated Markdown report: {output_file}")
    conn.close()

def generate_csv_by_source():
    """Generate CSV files by source."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    sources = ["crossref", "openalex", "semantic_scholar"]
    
    for source in sources:
        cursor.execute("""
            SELECT 
                id, source, title, abstract, pdf_url, doi, year, 
                authors, venue, source_url, landing_url, open_access, oa_status
            FROM documents
            WHERE source = ?
            ORDER BY id
        """, (source,))
        
        rows = cursor.fetchall()
        
        if not rows:
            continue
        
        import csv
        output_file = OUTPUT_DIR / f"{source}_records.csv"
        
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))
        
        print(f"Generated CSV for {source}: {output_file} ({len(rows)} records)")
    
    conn.close()

if __name__ == "__main__":
    print("Generating detailed reports...\n")
    generate_json_report()
    generate_markdown_report()
    generate_csv_by_source()
    print(f"\nAll reports generated in: {OUTPUT_DIR}")

