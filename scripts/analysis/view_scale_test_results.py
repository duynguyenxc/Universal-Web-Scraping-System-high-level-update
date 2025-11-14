"""View scale test results with metadata and PDF information."""

import json
from pathlib import Path

def view_sample_records():
    """View sample records from the complete JSONL file."""
    file_path = Path("data/scale_test_complete.jsonl")

    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    print("=== SAMPLE RECORDS FROM SCALE TEST (COMPLETE PIPELINE) ===\n")

    pdf_count = 0
    total_count = 0

    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= 5:  # Skip first 5, show records 6-10
                try:
                    data = json.loads(line.strip())
                    total_count += 1

                    print(f"Record {i+1}:")
                    print(f"  Title: {data.get('title', 'N/A')[:80]}...")
                    print(f"  Source: {data.get('source', 'N/A')}")
                    print(f"  Relevance Score: {data.get('relevance_score', 'N/A')}")
                    print(f"  Status: {data.get('status', 'N/A')}")

                    pdf_path = data.get('pdf_path')
                    if pdf_path and pdf_path != 'None':
                        pdf_count += 1
                        print(f"  PDF Path: {pdf_path}")
                    else:
                        print("  PDF Path: None")

                    if data.get('abstract'):
                        abstract = data['abstract'][:100].replace('\n', ' ')
                        print(f"  Abstract: {abstract}...")
                    else:
                        print("  Abstract: None")

                    print(f"  Year: {data.get('year', 'N/A')}")
                    print(f"  DOI: {data.get('doi', 'N/A')}")
                    print()

                    if i >= 14:  # Show 10 records total (6-15)
                        break

                except Exception as e:
                    print(f"Error parsing line {i+1}: {e}")
                    break

    print(f"\n=== SUMMARY ===")
    print(f"Total records in file: {total_count + 5}")  # +5 for the ones we skipped
    print(f"Records with PDFs: {pdf_count}")

def view_pdf_files():
    """View information about downloaded PDF files."""
    pdf_dir = Path("data/paperscraper_pdfs")

    if not pdf_dir.exists():
        print(f"PDF directory not found: {pdf_dir}")
        return

    pdf_files = list(pdf_dir.glob("*.pdf"))
    print(f"\n=== DOWNLOADED PDF FILES ({len(pdf_files)} files) ===\n")

    for i, pdf_file in enumerate(sorted(pdf_files)[:10]):  # Show first 10
        print(f"{i+1}. {pdf_file.name}")
        print(f"   Size: {pdf_file.stat().st_size} bytes")
        print(f"   Path: {pdf_file}")
        print()

    if len(pdf_files) > 10:
        print(f"... and {len(pdf_files) - 10} more files")

def view_metadata_quality():
    """View metadata quality statistics."""
    file_path = Path("data/scale_test_complete.jsonl")

    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    stats = {
        'crossref': {'total': 0, 'abstract': 0, 'pdf': 0, 'score': 0},
        'openalex': {'total': 0, 'abstract': 0, 'pdf': 0, 'score': 0},
        'semantic_scholar': {'total': 0, 'abstract': 0, 'pdf': 0, 'score': 0}
    }

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                source = data.get('source', 'unknown')

                if source in stats:
                    stats[source]['total'] += 1

                    if data.get('abstract'):
                        stats[source]['abstract'] += 1

                    if data.get('pdf_path') and data['pdf_path'] != 'None':
                        stats[source]['pdf'] += 1

                    if data.get('relevance_score') is not None:
                        stats[source]['score'] += 1

            except:
                pass

    print("\n=== METADATA QUALITY ===")
    for source, data in stats.items():
        total = data['total']
        if total > 0:
            print(f"\n{source.upper()}:")
            print(f"  Total records: {total}")
            print(".1f")
            print(".1f")
            print(".1f")

if __name__ == "__main__":
    view_sample_records()
    view_pdf_files()
    view_metadata_quality()
