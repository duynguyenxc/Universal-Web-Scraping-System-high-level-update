"""Phase 1.3: Integration Testing - Test all sources together with deduplication.

Tests:
1. All sources (arXiv, Crossref, OpenAlex, DOAJ)
2. Cross-source deduplication (DOI-based)
3. Data quality across sources
4. Performance metrics
"""

import subprocess
import sys
import time
import json
from pathlib import Path

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def run_command(cmd, description):
    """Run a CLI command and return success status."""
    print(f"\n{'='*80}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*80)
    
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            print(f"[OK] {description} completed in {elapsed:.1f}s")
            if result.stdout:
                # Print last few lines of output
                lines = result.stdout.strip().split('\n')
                for line in lines[-5:]:
                    print(f"  {line}")
            return True, elapsed
        else:
            print(f"[ERROR] {description} failed")
            if result.stderr:
                print(f"Error: {result.stderr[:500]}")
            return False, elapsed
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        return False, time.time() - start_time

def main():
    """Run integration test for all sources."""
    db_path = "data/phase1_3_integration.sqlite"
    
    print("="*80)
    print("PHASE 1.3: INTEGRATION TESTING")
    print("="*80)
    print(f"Database: {db_path}")
    print(f"Testing: arXiv, Crossref, OpenAlex, DOAJ")
    print("="*80)
    
    # Clean database
    if Path(db_path).exists():
        Path(db_path).unlink()
        print(f"[INFO] Removed existing database: {db_path}")
    
    results = {}
    total_time = 0
    
    # 1. Initialize database
    success, elapsed = run_command(
        ["python", "-m", "src.uwss.cli", "db-init", "--db", db_path],
        "Initialize database"
    )
    results["db_init"] = {"success": success, "elapsed": elapsed}
    total_time += elapsed
    
    # 2. arXiv harvest (small batch)
    success, elapsed = run_command(
        ["python", "-m", "src.uwss.cli", "arxiv-harvest-oai", 
         "--db", db_path, "--max", "50", "--metrics-out", "data/phase1_3_arxiv_metrics.json"],
        "arXiv OAI-PMH harvest (50 records)"
    )
    results["arxiv"] = {"success": success, "elapsed": elapsed}
    total_time += elapsed
    
    # 3. Crossref discover
    success, elapsed = run_command(
        ["python", "-m", "src.uwss.cli", "crossref-discover",
         "--db", db_path, "--max", "50", "--throttle", "1.0",
         "--metrics-out", "data/phase1_3_crossref_metrics.json"],
        "Crossref discovery (50 records)"
    )
    results["crossref"] = {"success": success, "elapsed": elapsed}
    total_time += elapsed
    
    # 4. OpenAlex discover
    success, elapsed = run_command(
        ["python", "-m", "src.uwss.cli", "openalex-discover",
         "--db", db_path, "--max", "50", "--throttle", "0.1",
         "--metrics-out", "data/phase1_3_openalex_metrics.json"],
        "OpenAlex discovery (50 records)"
    )
    results["openalex"] = {"success": success, "elapsed": elapsed}
    total_time += elapsed
    
    # 5. DOAJ discover (articles only for better quality)
    success, elapsed = run_command(
        ["python", "-m", "src.uwss.cli", "doaj-discover",
         "--db", db_path, "--max", "50", "--articles-only", "--throttle", "1.0",
         "--metrics-out", "data/phase1_3_doaj_metrics.json"],
        "DOAJ discovery (50 articles)"
    )
    results["doaj"] = {"success": success, "elapsed": elapsed}
    total_time += elapsed
    
    # 6. Analyze results
    print("\n" + "="*80)
    print("ANALYZING RESULTS")
    print("="*80)
    
    # Import analysis script
    import sqlite3
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Count by source
    cursor.execute("SELECT source, COUNT(*) FROM documents GROUP BY source")
    sources = dict(cursor.fetchall())
    
    print("\nSources Summary:")
    for source, count in sources.items():
        print(f"  {source}: {count} records")
    
    # Total records
    cursor.execute("SELECT COUNT(*) FROM documents")
    total = cursor.fetchone()[0]
    print(f"\nTotal records: {total}")
    
    # Deduplication analysis
    print("\nDeduplication Analysis:")
    
    # Count duplicates by DOI
    cursor.execute("""
        SELECT doi, COUNT(*) as cnt, GROUP_CONCAT(DISTINCT source) as sources
        FROM documents 
        WHERE doi IS NOT NULL AND doi != ''
        GROUP BY doi 
        HAVING cnt > 1
    """)
    doi_duplicates = cursor.fetchall()
    print(f"  Duplicates by DOI: {len(doi_duplicates)}")
    if doi_duplicates:
        print("  Sample DOI duplicates:")
        for doi, count, sources in doi_duplicates[:5]:
            print(f"    DOI: {doi[:50]}... | Count: {count} | Sources: {sources}")
    
    # Count duplicates by source_url
    cursor.execute("""
        SELECT source_url, COUNT(*) as cnt
        FROM documents 
        WHERE source_url IS NOT NULL AND source_url != ''
        GROUP BY source_url 
        HAVING cnt > 1
    """)
    url_duplicates = cursor.fetchall()
    print(f"  Duplicates by source_url: {len(url_duplicates)}")
    
    # Data quality by source
    print("\nData Quality by Source:")
    for source in sources.keys():
        if source is None:
            source_filter = "source IS NULL"
            params = ()
        else:
            source_filter = "source = ?"
            params = (source,)
        
        cursor.execute(f"""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN title IS NOT NULL AND title != '' THEN 1 ELSE 0 END) as with_title,
                SUM(CASE WHEN abstract IS NOT NULL AND abstract != '' THEN 1 ELSE 0 END) as with_abstract,
                SUM(CASE WHEN doi IS NOT NULL AND doi != '' THEN 1 ELSE 0 END) as with_doi,
                SUM(CASE WHEN authors IS NOT NULL AND authors != '' THEN 1 ELSE 0 END) as with_authors,
                SUM(CASE WHEN year IS NOT NULL THEN 1 ELSE 0 END) as with_year
            FROM documents 
            WHERE {source_filter}
        """, params)
        row = cursor.fetchone()
        if row:
            total, title, abstract, doi, authors, year = row
            source_name = source if source else "unknown"
            print(f"\n  {source_name}:")
            print(f"    Total: {total}")
            if total > 0:
                title_pct = (title or 0) / total * 100
                abstract_pct = (abstract or 0) / total * 100
                doi_pct = (doi or 0) / total * 100
                authors_pct = (authors or 0) / total * 100
                year_pct = (year or 0) / total * 100
                print(f"    Title: {title or 0}/{total} ({title_pct:.1f}%)")
                print(f"    Abstract: {abstract or 0}/{total} ({abstract_pct:.1f}%)")
                print(f"    DOI: {doi or 0}/{total} ({doi_pct:.1f}%)")
                print(f"    Authors: {authors or 0}/{total} ({authors_pct:.1f}%)")
                print(f"    Year: {year or 0}/{total} ({year_pct:.1f}%)")
    
    # Re-count total (fix bug where total was overwritten)
    cursor.execute("SELECT COUNT(*) FROM documents")
    actual_total = cursor.fetchone()[0]
    
    conn.close()
    
    # Summary
    print("\n" + "="*80)
    print("INTEGRATION TEST SUMMARY")
    print("="*80)
    print(f"Total execution time: {total_time:.1f}s")
    print(f"Total records: {actual_total}")
    print(f"DOI duplicates: {len(doi_duplicates)}")
    print(f"URL duplicates: {len(url_duplicates)}")
    
    all_success = all(r["success"] for r in results.values())
    if all_success:
        print("\n[SUCCESS] All sources completed successfully!")
    else:
        print("\n[WARNING] Some sources failed. Check logs above.")
    
    # Save results
    results["summary"] = {
        "total_records": actual_total,
        "doi_duplicates": len(doi_duplicates),
        "url_duplicates": len(url_duplicates),
        "total_time": total_time,
        "all_success": all_success
    }
    
    with open("data/phase1_3_integration_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to: data/phase1_3_integration_results.json")
    
    return 0 if all_success else 1

if __name__ == "__main__":
    sys.exit(main())

