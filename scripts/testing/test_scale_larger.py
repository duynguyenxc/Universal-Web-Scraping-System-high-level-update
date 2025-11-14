"""Test new sources with larger scale to verify data collection and quality."""

import json
import sqlite3
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()

# Database path
DB_PATH = Path("data/test_new_sources.sqlite")

def analyze_database():
    """Analyze database content and quality."""
    if not DB_PATH.exists():
        console.print(f"[red]Database not found: {DB_PATH}[/red]")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get total counts by source
    cursor.execute("""
        SELECT source, COUNT(*) as count
        FROM documents
        GROUP BY source
        ORDER BY source
    """)
    source_counts = dict(cursor.fetchall())
    
    # Get metadata quality by source
    quality_metrics = {}
    for source in source_counts.keys():
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN abstract IS NOT NULL AND abstract != '' THEN 1 ELSE 0 END) as has_abstract,
                SUM(CASE WHEN pdf_url IS NOT NULL AND pdf_url != '' THEN 1 ELSE 0 END) as has_pdf_url,
                SUM(CASE WHEN doi IS NOT NULL AND doi != '' THEN 1 ELSE 0 END) as has_doi,
                SUM(CASE WHEN authors IS NOT NULL AND authors != '' THEN 1 ELSE 0 END) as has_authors,
                SUM(CASE WHEN year IS NOT NULL THEN 1 ELSE 0 END) as has_year,
                SUM(CASE WHEN venue IS NOT NULL AND venue != '' THEN 1 ELSE 0 END) as has_venue
            FROM documents
            WHERE source = ?
        """, (source,))
        row = cursor.fetchone()
        if row:
            total, has_abstract, has_pdf_url, has_doi, has_authors, has_year, has_venue = row
            quality_metrics[source] = {
                "total": total,
                "abstract_pct": (has_abstract / total * 100) if total > 0 else 0,
                "pdf_url_pct": (has_pdf_url / total * 100) if total > 0 else 0,
                "doi_pct": (has_doi / total * 100) if total > 0 else 0,
                "authors_pct": (has_authors / total * 100) if total > 0 else 0,
                "year_pct": (has_year / total * 100) if total > 0 else 0,
                "venue_pct": (has_venue / total * 100) if total > 0 else 0,
            }
    
    # Check for HTML tags in abstracts (should be cleaned now)
    cursor.execute("""
        SELECT source, COUNT(*) as count
        FROM documents
        WHERE abstract LIKE '%<%' AND abstract LIKE '%>%'
        GROUP BY source
    """)
    html_in_abstracts = dict(cursor.fetchall())
    
    # Check for empty string pdf_url (should be None now)
    cursor.execute("""
        SELECT source, COUNT(*) as count
        FROM documents
        WHERE pdf_url = ''
        GROUP BY source
    """)
    empty_pdf_urls = dict(cursor.fetchall())
    
    # Display results
    console.print("\n[bold cyan]=== DATABASE ANALYSIS ===[/bold cyan]\n")
    
    # Source counts table
    table = Table(title="Records by Source")
    table.add_column("Source", style="cyan")
    table.add_column("Count", style="green", justify="right")
    for source, count in sorted(source_counts.items()):
        table.add_row(source, str(count))
    console.print(table)
    
    # Quality metrics table
    console.print("\n[bold cyan]=== METADATA QUALITY ===[/bold cyan]\n")
    quality_table = Table(title="Metadata Coverage (%)")
    quality_table.add_column("Source", style="cyan")
    quality_table.add_column("Abstract", style="yellow", justify="right")
    quality_table.add_column("PDF URL", style="yellow", justify="right")
    quality_table.add_column("DOI", style="yellow", justify="right")
    quality_table.add_column("Authors", style="yellow", justify="right")
    quality_table.add_column("Year", style="yellow", justify="right")
    quality_table.add_column("Venue", style="yellow", justify="right")
    
    for source in sorted(quality_metrics.keys()):
        metrics = quality_metrics[source]
        quality_table.add_row(
            source,
            f"{metrics['abstract_pct']:.1f}%",
            f"{metrics['pdf_url_pct']:.1f}%",
            f"{metrics['doi_pct']:.1f}%",
            f"{metrics['authors_pct']:.1f}%",
            f"{metrics['year_pct']:.1f}%",
            f"{metrics['venue_pct']:.1f}%",
        )
    console.print(quality_table)
    
    # Issues table
    console.print("\n[bold cyan]=== FIXES VERIFICATION ===[/bold cyan]\n")
    issues_table = Table(title="Remaining Issues")
    issues_table.add_column("Source", style="cyan")
    issues_table.add_column("HTML in Abstracts", style="red", justify="right")
    issues_table.add_column("Empty PDF URLs", style="red", justify="right")
    
    for source in sorted(source_counts.keys()):
        html_count = html_in_abstracts.get(source, 0)
        empty_count = empty_pdf_urls.get(source, 0)
        issues_table.add_row(
            source,
            str(html_count),
            str(empty_count),
        )
    console.print(issues_table)
    
    # Sample records
    console.print("\n[bold cyan]=== SAMPLE RECORDS ===[/bold cyan]\n")
    for source in sorted(source_counts.keys()):
        cursor.execute("""
            SELECT title, abstract, pdf_url, doi, year
            FROM documents
            WHERE source = ?
            LIMIT 2
        """, (source,))
        samples = cursor.fetchall()
        
        console.print(f"\n[bold yellow]{source.upper()}:[/bold yellow]")
        for i, (title, abstract, pdf_url, doi, year) in enumerate(samples, 1):
            console.print(f"  [cyan]Sample {i}:[/cyan]")
            console.print(f"    Title: {title[:80]}..." if len(title) > 80 else f"    Title: {title}")
            console.print(f"    Abstract: {abstract[:100]}..." if abstract and len(abstract) > 100 else f"    Abstract: {abstract or 'None'}")
            console.print(f"    PDF URL: {pdf_url or 'None'}")
            console.print(f"    DOI: {doi or 'None'}")
            console.print(f"    Year: {year or 'None'}")
    
    conn.close()

if __name__ == "__main__":
    analyze_database()

