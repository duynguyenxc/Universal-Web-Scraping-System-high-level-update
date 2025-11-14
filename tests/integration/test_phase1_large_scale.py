"""Phase 1 Large-Scale Test: Test with larger volumes to identify issues.

Tests:
1. Discovery (larger volumes: 200-300 per source)
2. Scoring
3. Export
4. PDF Fetching
5. Detailed analysis of issues
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
                lines = result.stdout.strip().split('\n')
                for line in lines[-5:]:
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
    """Run large-scale Phase 1 test."""
    db_path = "data/phase1_large_scale.sqlite"
    export_dir = Path("data/phase1_large_export")
    export_dir.mkdir(parents=True, exist_ok=True)
    files_dir = Path("data/phase1_large_files")
    files_dir.mkdir(parents=True, exist_ok=True)
    
    print("="*80)
    print("PHASE 1 LARGE-SCALE TEST")
    print("="*80)
    print(f"Database: {db_path}")
    print(f"Export dir: {export_dir}")
    print(f"Files dir: {files_dir}")
    print("Target: 200-300 records per source")
    print("="*80)
    
    # Clean database
    if Path(db_path).exists():
        Path(db_path).unlink()
        print(f"[INFO] Removed existing database: {db_path}")
    
    results = {}
    total_time = 0
    
    # ============================================================
    # STEP 1: DISCOVERY (Large Scale)
    # ============================================================
    print("\n" + "="*80)
    print("STEP 1: DISCOVERY (Large Scale)")
    print("="*80)
    
    # 1.1 arXiv harvest (200 records)
    success, elapsed, output = run_command(
        ["python", "-m", "src.uwss.cli", "arxiv-harvest-oai", 
         "--db", db_path, "--max", "200", "--metrics-out", "data/phase1_large_arxiv_metrics.json"],
        "arXiv OAI-PMH harvest (200 records)"
    )
    results["discovery_arxiv"] = {"success": success, "elapsed": elapsed, "output": output}
    total_time += elapsed
    
    # 1.2 Crossref discover (200 records)
    success, elapsed, output = run_command(
        ["python", "-m", "src.uwss.cli", "crossref-discover",
         "--db", db_path, "--max", "200", "--throttle", "1.0",
         "--metrics-out", "data/phase1_large_crossref_metrics.json"],
        "Crossref discovery (200 records)"
    )
    results["discovery_crossref"] = {"success": success, "elapsed": elapsed, "output": output}
    total_time += elapsed
    
    # 1.3 OpenAlex discover (200 records - may return fewer)
    success, elapsed, output = run_command(
        ["python", "-m", "src.uwss.cli", "openalex-discover",
         "--db", db_path, "--max", "200", "--throttle", "0.1",
         "--metrics-out", "data/phase1_large_openalex_metrics.json"],
        "OpenAlex discovery (200 records)"
    )
    results["discovery_openalex"] = {"success": success, "elapsed": elapsed, "output": output}
    total_time += elapsed
    
    # 1.4 DOAJ discover (200 records)
    success, elapsed, output = run_command(
        ["python", "-m", "src.uwss.cli", "doaj-discover",
         "--db", db_path, "--max", "200", "--articles-only", "--throttle", "1.0",
         "--metrics-out", "data/phase1_large_doaj_metrics.json"],
        "DOAJ discovery (200 articles)"
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
    # STEP 4: PDF FETCHING (Larger batch)
    # ============================================================
    print("\n" + "="*80)
    print("STEP 4: PDF FETCHING")
    print("="*80)
    
    # Enrich OA first
    success, elapsed, output = run_command(
        ["python", "-m", "src.uwss.cli", "download-open",
         "--db", db_path, "--limit", "50", "--outdir", str(files_dir)],
        "Fetch PDFs (50 records)"
    )
    results["fetch"] = {"success": success, "elapsed": elapsed, "output": output}
    total_time += elapsed
    
    # ============================================================
    # STEP 5: DETAILED ANALYSIS
    # ============================================================
    print("\n" + "="*80)
    print("STEP 5: DETAILED ANALYSIS")
    print("="*80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Total records
    cursor.execute("SELECT COUNT(*) FROM documents")
    total_records = cursor.fetchone()[0]
    
    # By source
    cursor.execute("SELECT source, COUNT(*) FROM documents GROUP BY source")
    sources = dict(cursor.fetchall())
    
    # Detailed quality analysis by source
    quality_analysis = {}
    issues_by_source = {}
    
    for source in sources.keys():
        if source is None:
            source_filter = "source IS NULL"
            params = ()
            source_name = "unknown"
        else:
            source_filter = "source = ?"
            params = (source,)
            source_name = source
        
        # Basic stats
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
                AVG(relevance_score) as avg_score,
                MIN(relevance_score) as min_score,
                MAX(relevance_score) as max_score
            FROM documents 
            WHERE {source_filter}
        """, params)
        row = cursor.fetchone()
        
        if row:
            total, title, abstract, doi, authors, year, pdf_url, local_pdf, avg_score, min_score, max_score = row
            quality_analysis[source_name] = {
                "total": total,
                "title_pct": (title or 0) / total * 100 if total > 0 else 0,
                "abstract_pct": (abstract or 0) / total * 100 if total > 0 else 0,
                "doi_pct": (doi or 0) / total * 100 if total > 0 else 0,
                "authors_pct": (authors or 0) / total * 100 if total > 0 else 0,
                "year_pct": (year or 0) / total * 100 if total > 0 else 0,
                "pdf_url_pct": (pdf_url or 0) / total * 100 if total > 0 else 0,
                "local_pdf_pct": (local_pdf or 0) / total * 100 if total > 0 else 0,
                "avg_score": avg_score,
                "min_score": min_score,
                "max_score": max_score
            }
            
            # Identify issues
            issues = []
            if (abstract or 0) / total < 0.5 if total > 0 else False:
                issues.append(f"Low abstract coverage: {(abstract or 0)/total*100:.1f}%")
            if (authors or 0) / total < 0.5 if total > 0 else False:
                issues.append(f"Low authors coverage: {(authors or 0)/total*100:.1f}%")
            if (pdf_url or 0) / total < 0.1 if total > 0 else False:
                issues.append(f"Low PDF URL coverage: {(pdf_url or 0)/total*100:.1f}%")
            if avg_score and avg_score < 0.5:
                issues.append(f"Low average relevance score: {avg_score:.2f}")
            if total < 50:
                issues.append(f"Low record count: {total} (expected 200+)")
            
            if issues:
                issues_by_source[source_name] = issues
    
    # Duplicate analysis
    cursor.execute("""
        SELECT doi, COUNT(*) as cnt, GROUP_CONCAT(DISTINCT source) as sources
        FROM documents 
        WHERE doi IS NOT NULL AND doi != ''
        GROUP BY doi 
        HAVING cnt > 1
    """)
    doi_duplicates = cursor.fetchall()
    
    # PDF analysis
    cursor.execute("""
        SELECT source, 
               COUNT(*) as total,
               SUM(CASE WHEN pdf_url IS NOT NULL AND pdf_url != '' THEN 1 ELSE 0 END) as with_url,
               SUM(CASE WHEN local_path IS NOT NULL AND local_path != '' THEN 1 ELSE 0 END) as downloaded
        FROM documents
        GROUP BY source
    """)
    pdf_stats = dict((row[0] or "unknown", {"total": row[1], "with_url": row[2], "downloaded": row[3]}) 
                     for row in cursor.fetchall())
    
    conn.close()
    
    # Print detailed summary
    print("\n" + "="*80)
    print("LARGE-SCALE TEST SUMMARY")
    print("="*80)
    print(f"Total execution time: {total_time:.1f}s")
    print(f"Total records: {total_records}")
    print(f"\nRecords by source:")
    for source, count in sources.items():
        print(f"  {source or 'unknown'}: {count}")
    
    print(f"\n{'='*80}")
    print("DATA QUALITY BY SOURCE")
    print("="*80)
    for source, quality in quality_analysis.items():
        print(f"\n{source}:")
        print(f"  Total: {quality['total']}")
        print(f"  Title: {quality['title_pct']:.1f}%")
        print(f"  Abstract: {quality['abstract_pct']:.1f}%")
        print(f"  DOI: {quality['doi_pct']:.1f}%")
        print(f"  Authors: {quality['authors_pct']:.1f}%")
        print(f"  Year: {quality['year_pct']:.1f}%")
        print(f"  PDF URL: {quality['pdf_url_pct']:.1f}%")
        print(f"  Local PDF: {quality['local_pdf_pct']:.1f}%")
        if quality['avg_score']:
            print(f"  Score: avg={quality['avg_score']:.2f}, min={quality['min_score']:.2f}, max={quality['max_score']:.2f}")
    
    print(f"\n{'='*80}")
    print("ISSUES IDENTIFIED BY SOURCE")
    print("="*80)
    if issues_by_source:
        for source, issues in issues_by_source.items():
            print(f"\n{source}:")
            for issue in issues:
                print(f"  - {issue}")
    else:
        print("No major issues identified.")
    
    print(f"\n{'='*80}")
    print("DUPLICATE ANALYSIS")
    print("="*80)
    print(f"DOI duplicates: {len(doi_duplicates)}")
    if doi_duplicates:
        print("Sample duplicates:")
        for doi, count, sources in doi_duplicates[:5]:
            print(f"  DOI: {doi[:50]}... | Count: {count} | Sources: {sources}")
    
    print(f"\n{'='*80}")
    print("PDF STATUS BY SOURCE")
    print("="*80)
    for source, stats in pdf_stats.items():
        print(f"\n{source}:")
        print(f"  Total: {stats['total']}")
        print(f"  With PDF URL: {stats['with_url']} ({stats['with_url']/stats['total']*100:.1f}%)")
        print(f"  Downloaded: {stats['downloaded']} ({stats['downloaded']/stats['total']*100:.1f}%)")
    
    # Save results
    results["summary"] = {
        "total_records": total_records,
        "sources": sources,
        "quality_analysis": quality_analysis,
        "issues_by_source": issues_by_source,
        "doi_duplicates": len(doi_duplicates),
        "pdf_stats": pdf_stats,
        "total_time": total_time
    }
    
    with open("data/phase1_large_scale_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to: data/phase1_large_scale_results.json")
    
    all_success = all(r["success"] for r in [
        results["discovery_arxiv"],
        results["discovery_crossref"],
        results["discovery_openalex"],
        results["discovery_doaj"],
        results["scoring"],
        results["export"]
    ])
    
    if all_success:
        print("\n[SUCCESS] Large-scale test completed!")
        return 0
    else:
        print("\n[WARNING] Some steps failed. Check logs above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

