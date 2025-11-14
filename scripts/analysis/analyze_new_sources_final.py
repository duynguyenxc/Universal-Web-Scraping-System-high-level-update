"""Analyze final results from new sources (Crossref, OpenAlex, Semantic Scholar)."""

import json
import sqlite3
from pathlib import Path
from collections import defaultdict

def analyze_final_results():
    """Analyze the final JSONL export with metadata and PDFs."""

    # Check JSONL file
    jsonl_path = Path("data/new_sources_final.jsonl")
    if not jsonl_path.exists():
        print(f"❌ JSONL file not found: {jsonl_path}")
        return

    print("=== FINAL ANALYSIS: NEW SOURCES (CROSSREF, OPENALEX, SEMANTIC SCHOLAR) ===\n")

    # Statistics
    stats = {
        'crossref': defaultdict(int),
        'openalex': defaultdict(int),
        'semantic_scholar': defaultdict(int)
    }

    total_records = 0
    records_with_pdf = 0
    records_with_abstract = 0

    # Read JSONL
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                source = data.get('source', 'unknown')
                total_records += 1

                if source in stats:
                    stats[source]['total'] += 1

                    # Check metadata quality
                    if data.get('abstract'):
                        stats[source]['abstract'] += 1
                        records_with_abstract += 1

                    if data.get('pdf_path') and data['pdf_path'] != 'None':
                        stats[source]['pdf_downloaded'] += 1
                        records_with_pdf += 1

                    if data.get('pdf_url') and data['pdf_url'] != 'None':
                        stats[source]['pdf_url'] += 1

                    if data.get('doi'):
                        stats[source]['doi'] += 1

                    if data.get('year'):
                        stats[source]['year'] += 1

                    if data.get('authors'):
                        stats[source]['authors'] += 1

                    if data.get('venue'):
                        stats[source]['venue'] += 1

                    # Check for HTML tags in abstracts
                    if data.get('abstract') and ('<jats:' in data['abstract'] or '<' in data['abstract']):
                        stats[source]['html_tags'] += 1

                    # Check for empty PDF URLs (our fix)
                    if data.get('pdf_url') == '':
                        stats[source]['empty_pdf_url'] += 1

            except Exception as e:
                print(f"Error parsing line {line_num}: {e}")
                continue

    # Display results
    print("📊 METADATA QUALITY SUMMARY:"    print(f"   Total records: {total_records}")
    print(f"   Records with abstracts: {records_with_abstract}")
    print(f"   Records with downloaded PDFs: {records_with_pdf}")
    print()

    print("📈 BY SOURCE:")
    for source in ['crossref', 'openalex', 'semantic_scholar']:
        if stats[source]['total'] > 0:
            print(f"\n🔹 {source.upper()}:")
            total = stats[source]['total']
            print(f"   Records: {total}")
            print(".1f")
            print(".1f")
            print(".1f")
            print(".1f")
            print(".1f")
            print(".1f")
            print(".1f")

            if stats[source]['html_tags'] > 0:
                print(f"   ⚠️  HTML tags in abstracts: {stats[source]['html_tags']}")

            if stats[source]['empty_pdf_url'] > 0:
                print(f"   ⚠️  Empty PDF URLs: {stats[source]['empty_pdf_url']}")

    # Sample records
    print("\n" + "="*80)
    print("📋 SAMPLE RECORDS (5 per source):")
    print("="*80)

    samples_shown = {'crossref': 0, 'openalex': 0, 'semantic_scholar': 0}

    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                source = data.get('source', 'unknown')

                if source in samples_shown and samples_shown[source] < 5:
                    samples_shown[source] += 1

                    print(f"\n📄 {source.upper()} SAMPLE #{samples_shown[source]}:")
                    print(f"   Title: {data.get('title', 'N/A')[:80]}...")
                    print(f"   Year: {data.get('year', 'N/A')}")
                    print(f"   DOI: {data.get('doi', 'N/A')}")

                    abstract = data.get('abstract', '')
                    if abstract:
                        # Clean and truncate abstract
                        clean_abstract = abstract.replace('<jats:title>', '').replace('</jats:title>', '').replace('<jats:p>', '').replace('</jats:p>', '')
                        clean_abstract = clean_abstract[:150] + "..." if len(clean_abstract) > 150 else clean_abstract
                        print(f"   Abstract: {clean_abstract}")
                    else:
                        print("   Abstract: None"

                    pdf_path = data.get('pdf_path')
                    if pdf_path and pdf_path != 'None':
                        print(f"   PDF Downloaded: ✅ {pdf_path}")
                    else:
                        print("   PDF Downloaded: ❌ None"

                    status = data.get('status', 'unknown')
                    print(f"   Status: {status}")

                    # Stop when we have 5 samples from each
                    if all(count >= 5 for count in samples_shown.values()):
                        break

            except:
                continue

    # Check for new PDF files
    pdf_dirs = [
        Path("data/crossref_pdfs"),
        Path("data/openalex_pdfs"),
        Path("data/semantic_scholar_pdfs")
    ]

    print("\n" + "="*80)
    print("📁 PDF FILES DOWNLOADED:")
    print("="*80)

    total_new_pdfs = 0
    for pdf_dir in pdf_dirs:
        if pdf_dir.exists():
            pdf_files = list(pdf_dir.glob("*.pdf"))
            if pdf_files:
                print(f"\n📂 {pdf_dir.name}: {len(pdf_files)} files")
                total_new_pdfs += len(pdf_files)
                for pdf_file in sorted(pdf_files)[:3]:  # Show first 3
                    size_mb = pdf_file.stat().st_size / (1024 * 1024)
                    print(".1f")
                if len(pdf_files) > 3:
                    print(f"   ... and {len(pdf_files) - 3} more files")
        else:
            print(f"\n📂 {pdf_dir.name}: No directory found")

    if total_new_pdfs == 0:
        print("\n❌ No new PDF files were downloaded from the 3 new sources.")

        # Check if PDFs are in paperscraper_pdfs
        paperscraper_pdf_dir = Path("data/paperscraper_pdfs")
        if paperscraper_pdf_dir.exists():
            existing_pdfs = list(paperscraper_pdf_dir.glob("*.pdf"))
            print(f"\nℹ️  Existing PDFs from previous tests: {len(existing_pdfs)} files in paperscraper_pdfs/")

    print("\n" + "="*80)
    print("✅ ANALYSIS COMPLETE")
    print("="*80)

if __name__ == "__main__":
    analyze_final_results()
