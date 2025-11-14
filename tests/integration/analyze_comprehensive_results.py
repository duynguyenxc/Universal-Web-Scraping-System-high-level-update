#!/usr/bin/env python3
"""Analyze comprehensive test results from all sources."""

import sqlite3
import json
from pathlib import Path
from collections import Counter

DB_PATH = Path("data/uwss_clean.sqlite")

if not DB_PATH.exists():
    print(f"ERROR: Database not found: {DB_PATH}")
    exit(1)

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

print("=" * 80)
print("COMPREHENSIVE DATABASE ANALYSIS")
print("=" * 80)
print()

# Get all records grouped by source
cursor.execute("""
    SELECT 
        COALESCE(source, 
            CASE 
                WHEN source_url LIKE 'https://openalex.org%' THEN 'openalex'
                WHEN source_url LIKE 'https://doi.org%' THEN 'crossref'
                WHEN source_url LIKE 'http://arxiv.org%' OR source_url LIKE 'https://arxiv.org%' THEN 'arxiv'
                ELSE 'unknown'
            END
        ) as source_name,
        COUNT(*) as total,
        COUNT(CASE WHEN title IS NOT NULL AND title != '' THEN 1 END) as has_title,
        COUNT(CASE WHEN abstract IS NOT NULL AND abstract != '' THEN 1 END) as has_abstract,
        COUNT(CASE WHEN authors IS NOT NULL AND authors != '' THEN 1 END) as has_authors,
        COUNT(CASE WHEN doi IS NOT NULL AND doi != '' THEN 1 END) as has_doi,
        COUNT(CASE WHEN year IS NOT NULL THEN 1 END) as has_year,
        COUNT(CASE WHEN oa_status = 'fulltext_pdf' OR oa_status = 'open' THEN 1 END) as has_oa,
        COUNT(DISTINCT doi) as unique_doi
    FROM documents
    GROUP BY source_name
""")

print("1. OVERALL STATISTICS BY SOURCE")
print("-" * 80)

sources_stats = {}
for row in cursor.fetchall():
    source_name_raw, total, has_title, has_abstract, has_authors, has_doi, has_year, has_oa, unique_doi = row
    
    # Normalize source name
    source_name = source_name_raw.capitalize() if source_name_raw else 'Unknown'
    
    sources_stats[source_name] = {
        'total': total,
        'has_title': has_title,
        'has_abstract': has_abstract,
        'has_authors': has_authors,
        'has_doi': has_doi,
        'has_year': has_year,
        'has_oa': has_oa,
        'unique_doi': unique_doi,
    }
    
    print(f"\n{source_name}:")
    print(f"  Total records: {total}")
    if total > 0:
        print(f"  Title:       {has_title}/{total} ({has_title/total*100:.1f}%)")
        print(f"  Abstract:    {has_abstract}/{total} ({has_abstract/total*100:.1f}%)")
        print(f"  Authors:     {has_authors}/{total} ({has_authors/total*100:.1f}%)")
        print(f"  DOI:         {has_doi}/{total} ({has_doi/total*100:.1f}%)")
        print(f"  Year:        {has_year}/{total} ({has_year/total*100:.1f}%)")
        print(f"  Open Access: {has_oa}/{total} ({has_oa/total*100:.1f}%)")
        print(f"  Unique DOIs: {unique_doi}")

# Overall stats
cursor.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN title IS NOT NULL AND title != '' THEN 1 END) as has_title,
        COUNT(CASE WHEN abstract IS NOT NULL AND abstract != '' THEN 1 END) as has_abstract,
        COUNT(CASE WHEN authors IS NOT NULL AND authors != '' THEN 1 END) as has_authors,
        COUNT(CASE WHEN doi IS NOT NULL AND doi != '' THEN 1 END) as has_doi,
        COUNT(CASE WHEN year IS NOT NULL THEN 1 END) as has_year,
        COUNT(CASE WHEN oa_status = 'fulltext_pdf' OR oa_status = 'open' THEN 1 END) as has_oa,
        COUNT(DISTINCT doi) as unique_doi
    FROM documents
""")
row = cursor.fetchone()
total, has_title, has_abstract, has_authors, has_doi, has_year, has_oa, unique_doi = row

print()
print("2. OVERALL STATISTICS (ALL SOURCES)")
print("-" * 80)
print(f"Total records: {total}")
if total > 0:
    print(f"Title:       {has_title}/{total} ({has_title/total*100:.1f}%)")
    print(f"Abstract:    {has_abstract}/{total} ({has_abstract/total*100:.1f}%)")
    print(f"Authors:     {has_authors}/{total} ({has_authors/total*100:.1f}%)")
    print(f"DOI:         {has_doi}/{total} ({has_doi/total*100:.1f}%)")
    print(f"Year:        {has_year}/{total} ({has_year/total*100:.1f}%)")
    print(f"Open Access: {has_oa}/{total} ({has_oa/total*100:.1f}%)")
    print(f"Unique DOIs: {unique_doi}")
    print(f"Duplicates:  {total - unique_doi} (by DOI)")

# Year distribution
cursor.execute("""
    SELECT year, COUNT(*) as cnt 
    FROM documents 
    WHERE year IS NOT NULL 
    GROUP BY year 
    ORDER BY year DESC 
    LIMIT 10
""")
print()
print("3. YEAR DISTRIBUTION (Top 10)")
print("-" * 80)
for year, cnt in cursor.fetchall():
    print(f"  {year}: {cnt} records ({cnt/total*100:.1f}%)")

# Sample records
cursor.execute("""
    SELECT title, abstract, authors, doi, year, source_url, oa_status
    FROM documents 
    ORDER BY year DESC
    LIMIT 5
""")
print()
print("4. SAMPLE RECORDS (Most Recent)")
print("-" * 80)
for i, (title, abstract, authors, doi, year, source_url, oa_status) in enumerate(cursor.fetchall(), 1):
    title_short = title[:70] + "..." if title and len(title) > 70 else title
    source = "OpenAlex" if "openalex.org" in source_url else "Crossref" if "doi.org" in source_url else "Unknown"
    has_abstract = "YES" if abstract and len(abstract) > 50 else "NO"
    print(f"{i}. [{source}] {title_short}")
    print(f"   Year: {year}, DOI: {doi or 'N/A'}, OA: {oa_status}, Abstract: {has_abstract}")
    print()

# Comparison
if len(sources_stats) > 1:
    print("5. SOURCE COMPARISON")
    print("-" * 80)
    print(f"{'Metric':<20} {'arXiv':<15} {'Crossref':<15} {'OpenAlex':<15} {'Winner'}")
    print("-" * 80)
    
    for metric in ['total', 'has_title', 'has_abstract', 'has_authors', 'has_doi', 'has_oa']:
        arxiv_val = sources_stats.get('Arxiv', {}).get(metric, 0)
        cr_val = sources_stats.get('Crossref', {}).get(metric, 0)
        oa_val = sources_stats.get('Openalex', {}).get(metric, 0)
        
        arxiv_total = sources_stats.get('Arxiv', {}).get('total', 1)
        cr_total = sources_stats.get('Crossref', {}).get('total', 1)
        oa_total = sources_stats.get('Openalex', {}).get('total', 1)
        
        arxiv_pct = (arxiv_val / arxiv_total * 100) if arxiv_total > 0 else 0
        cr_pct = (cr_val / cr_total * 100) if cr_total > 0 else 0
        oa_pct = (oa_val / oa_total * 100) if oa_total > 0 else 0
        
        if metric == 'total':
            arxiv_str = str(arxiv_val)
            cr_str = str(cr_val)
            oa_str = str(oa_val)
            winner = max([('Arxiv', arxiv_val), ('Crossref', cr_val), ('OpenAlex', oa_val)], key=lambda x: x[1])[0]
        else:
            arxiv_str = f"{arxiv_val}/{arxiv_total} ({arxiv_pct:.1f}%)"
            cr_str = f"{cr_val}/{cr_total} ({cr_pct:.1f}%)"
            oa_str = f"{oa_val}/{oa_total} ({oa_pct:.1f}%)"
            winner = max([('Arxiv', arxiv_pct), ('Crossref', cr_pct), ('OpenAlex', oa_pct)], key=lambda x: x[1])[0]
        
        print(f"{metric:<20} {arxiv_str:<15} {cr_str:<15} {oa_str:<15} {winner}")

print()
print("=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)

conn.close()

