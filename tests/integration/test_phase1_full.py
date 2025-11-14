"""Phase 1 Full Test: Complete pipeline from discovery to PDF fetching.

Tests:
1. Discovery (all sources)
2. Scoring
3. Export
4. PDF Fetching
5. Analysis
"""

import subprocess
import sys
import time
import json
import sqlite3
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
                for line in lines[-10:]:
                    print(f"  {line}")
            return True, elapsed, result.stdout
        else:
            print(f"[ERROR] {description} failed")
            if result.stderr:
                print(f"Error: {result.stderr[:500]}")
            return False, elapsed, result.stderr
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        return False, time.time() - start_time, str(e)

def main():
    """Run full Phase 1 test."""
    db_path = "data/phase1_full_test.sqlite"
    export_dir = Path("data/phase1_full_export")
    export_dir.mkdir(parents=True, exist_ok=True)
    
    print("="*80)
    print("PHASE 1 FULL TEST: COMPLETE PIPELINE")
    print("="*80)
    print(f"Database: {db_path}")
    print(f"Export dir: {export_dir}")
    print("="*80)
    
    # Clean database
    if Path(db_path).exists():
        Path(db_path).unlink()
        print(f"[INFO] Removed existing database: {db_path}")
    
    results = {}
    total_time = 0
    
    # ============================================================
    # STEP 1: DISCOVERY (All Sources)
    # ============================================================
    print("\n" + "="*80)
    print("STEP 1: DISCOVERY")
    print("="*80)
    
    # 1.1 arXiv harvest
    success, elapsed, output = run_command(
        ["python", "-m", "src.uwss.cli", "arxiv-harvest-oai", 
         "--db", db_path, "--max", "100", "--metrics-out", "data/phase1_full_arxiv_metrics.json"],
        "arXiv OAI-PMH harvest (100 records)"
    )
    results["discovery_arxiv"] = {"success": success, "elapsed": elapsed, "output": output}
    total_time += elapsed
    
    # 1.2 Crossref discover
    success, elapsed, output = run_command(
        ["python", "-m", "src.uwss.cli", "crossref-discover",
         "--db", db_path, "--max", "100", "--throttle", "1.0",
         "--metrics-out", "data/phase1_full_crossref_metrics.json"],
        "Crossref discovery (100 records)"
    )
    results["discovery_crossref"] = {"success": success, "elapsed": elapsed, "output": output}
    total_time += elapsed
    
    # 1.3 OpenAlex discover
    success, elapsed, output = run_command(
        ["python", "-m", "src.uwss.cli", "openalex-discover",
         "--db", db_path, "--max", "100", "--throttle", "0.1",
         "--metrics-out", "data/phase1_full_openalex_metrics.json"],
        "OpenAlex discovery (100 records)"
    )
    results["discovery_openalex"] = {"success": success, "elapsed": elapsed, "output": output}
    total_time += elapsed
    
    # 1.4 DOAJ discover
    success, elapsed, output = run_command(
        ["python", "-m", "src.uwss.cli", "doaj-discover",
         "--db", db_path, "--max", "100", "--articles-only", "--throttle", "1.0",
         "--metrics-out", "data/phase1_full_doaj_metrics.json"],
        "DOAJ discovery (100 articles)"
    )
    results["discovery_doaj"] = {"success": success, "elapsed": elapsed, "output": output}
    total_time += elapsed
    
    # ============================================================
    # STEP 2: SCORING
    # ============================================================
    print("\n" + "="*80)
    print("STEP 2: SCORING")
    print("="*80)
    
    success, elapsed, output = run_command(
        ["python", "-m", "src.uwss.cli", "score-keywords",
         "--db", db_path, "--config", "config/config.yaml"],
        "Score relevance with keywords"
    )
    results["scoring"] = {"success": success, "elapsed": elapsed, "output": output}
    total_time += elapsed
    
    # ============================================================
    # STEP 3: EXPORT
    # ============================================================
    print("\n" + "="*80)
    print("STEP 3: EXPORT")
    print("="*80)
    
    ids_file = export_dir / "filtered_ids.txt"
    export_file = export_dir / "filtered.jsonl"
    
    success, elapsed, output = run_command(
        ["python", "-m", "src.uwss.cli", "export",
         "--db", db_path, "--out", str(export_file),
         "--ids-out", str(ids_file), "--require-match", "--min-score", "0.5"],
        "Export filtered records"
    )
    results["export"] = {"success": success, "elapsed": elapsed, "output": output}
    total_time += elapsed
    
    # ============================================================
    # STEP 4: PDF FETCHING
    # ============================================================
    print("\n" + "="*80)
    print("STEP 4: PDF FETCHING")
    print("="*80)
    
    # Check if IDs file exists and has content
    if ids_file.exists() and ids_file.stat().st_size > 0:
        success, elapsed, output = run_command(
            ["python", "-m", "src.uwss.cli", "download-open",
             "--db", db_path, "--limit", "20", "--outdir", "data/phase1_full_files"],
            "Fetch PDFs (20 records)"
        )
        results["fetch"] = {"success": success, "elapsed": elapsed, "output": output}
        total_time += elapsed
    else:
        print(f"[WARNING] No IDs to fetch (file empty or not found)")
        results["fetch"] = {"success": False, "elapsed": 0, "output": "No IDs to fetch"}
    
    # ============================================================
    # STEP 5: ANALYSIS
    # ============================================================
    print("\n" + "="*80)
    print("STEP 5: ANALYSIS")
    print("="*80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Total records
    cursor.execute("SELECT COUNT(*) FROM documents")
    total_records = cursor.fetchone()[0]
    
    # By source
    cursor.execute("SELECT source, COUNT(*) FROM documents GROUP BY source")
    sources = dict(cursor.fetchall())
    
    # Scored records
    cursor.execute("SELECT COUNT(*) FROM documents WHERE relevance_score IS NOT NULL")
    scored_count = cursor.fetchone()[0]
    
    # Exported records (check IDs file)
    exported_count = 0
    if ids_file.exists():
        with open(ids_file, 'r') as f:
            exported_count = len([line.strip() for line in f if line.strip()])
    
    # PDFs fetched
    cursor.execute("SELECT COUNT(*) FROM documents WHERE local_path IS NOT NULL AND local_path != ''")
    pdfs_fetched = cursor.fetchone()[0]
    
    # PDFs with URL
    cursor.execute("SELECT COUNT(*) FROM documents WHERE pdf_url IS NOT NULL AND pdf_url != ''")
    pdfs_with_url = cursor.fetchone()[0]
    
    # Data quality by source
    quality_by_source = {}
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
                SUM(CASE WHEN year IS NOT NULL THEN 1 ELSE 0 END) as with_year,
                SUM(CASE WHEN pdf_url IS NOT NULL AND pdf_url != '' THEN 1 ELSE 0 END) as with_pdf_url,
                SUM(CASE WHEN local_path IS NOT NULL AND local_path != '' THEN 1 ELSE 0 END) as with_local_pdf,
                AVG(relevance_score) as avg_score
            FROM documents 
            WHERE {source_filter}
        """, params)
        row = cursor.fetchone()
        if row:
            total, title, abstract, doi, authors, year, pdf_url, local_pdf, avg_score = row
            quality_by_source[source or "unknown"] = {
                "total": total,
                "title_pct": (title or 0) / total * 100 if total > 0 else 0,
                "abstract_pct": (abstract or 0) / total * 100 if total > 0 else 0,
                "doi_pct": (doi or 0) / total * 100 if total > 0 else 0,
                "authors_pct": (authors or 0) / total * 100 if total > 0 else 0,
                "year_pct": (year or 0) / total * 100 if total > 0 else 0,
                "pdf_url_pct": (pdf_url or 0) / total * 100 if total > 0 else 0,
                "local_pdf_pct": (local_pdf or 0) / total * 100 if total > 0 else 0,
                "avg_score": avg_score
            }
    
    # Score distribution
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN relevance_score >= 2.0 THEN 1 ELSE 0 END) as high_score,
            SUM(CASE WHEN relevance_score >= 1.0 AND relevance_score < 2.0 THEN 1 ELSE 0 END) as medium_score,
            SUM(CASE WHEN relevance_score < 1.0 THEN 1 ELSE 0 END) as low_score
        FROM documents 
        WHERE relevance_score IS NOT NULL
    """)
    score_dist = cursor.fetchone()
    
    conn.close()
    
    # Print summary
    print("\n" + "="*80)
    print("PHASE 1 FULL TEST SUMMARY")
    print("="*80)
    print(f"Total execution time: {total_time:.1f}s")
    print(f"\nTotal records: {total_records}")
    print(f"Records by source:")
    for source, count in sources.items():
        print(f"  {source or 'unknown'}: {count}")
    
    print(f"\nScoring:")
    print(f"  Scored records: {scored_count}/{total_records} ({scored_count/total_records*100:.1f}%)")
    if score_dist and score_dist[0] and score_dist[0] > 0:
        total_scored, high, medium, low = score_dist
        print(f"  High score (>=2.0): {high}/{total_scored} ({high/total_scored*100:.1f}%)")
        print(f"  Medium score (1.0-2.0): {medium}/{total_scored} ({medium/total_scored*100:.1f}%)")
        print(f"  Low score (<1.0): {low}/{total_scored} ({low/total_scored*100:.1f}%)")
    else:
        print(f"  No scoring data available")
    
    print(f"\nExport:")
    print(f"  Exported IDs: {exported_count}")
    
    print(f"\nPDFs:")
    print(f"  Records with PDF URL: {pdfs_with_url}/{total_records} ({pdfs_with_url/total_records*100:.1f}%)")
    print(f"  PDFs fetched: {pdfs_fetched}/{total_records} ({pdfs_fetched/total_records*100:.1f}%)")
    
    print(f"\nData Quality by Source:")
    for source, quality in quality_by_source.items():
        print(f"\n  {source}:")
        print(f"    Total: {quality['total']}")
        print(f"    Title: {quality['title_pct']:.1f}%")
        print(f"    Abstract: {quality['abstract_pct']:.1f}%")
        print(f"    DOI: {quality['doi_pct']:.1f}%")
        print(f"    Authors: {quality['authors_pct']:.1f}%")
        print(f"    Year: {quality['year_pct']:.1f}%")
        print(f"    PDF URL: {quality['pdf_url_pct']:.1f}%")
        print(f"    Local PDF: {quality['local_pdf_pct']:.1f}%")
        if quality['avg_score']:
            print(f"    Avg Score: {quality['avg_score']:.2f}")
    
    # Save results
    results["summary"] = {
        "total_records": total_records,
        "sources": sources,
        "scored_count": scored_count,
        "exported_count": exported_count,
        "pdfs_with_url": pdfs_with_url,
        "pdfs_fetched": pdfs_fetched,
        "score_distribution": {
            "high": score_dist[1] if score_dist else 0,
            "medium": score_dist[2] if score_dist else 0,
            "low": score_dist[3] if score_dist else 0,
        } if score_dist else None,
        "quality_by_source": quality_by_source,
        "total_time": total_time
    }
    
    with open("data/phase1_full_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to: data/phase1_full_test_results.json")
    
    all_success = all(r["success"] for r in [
        results["discovery_arxiv"],
        results["discovery_crossref"],
        results["discovery_openalex"],
        results["discovery_doaj"],
        results["scoring"],
        results["export"]
    ])
    
    if all_success:
        print("\n[SUCCESS] Phase 1 full test completed successfully!")
        return 0
    else:
        print("\n[WARNING] Some steps failed. Check logs above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

