#!/usr/bin/env python3
"""Comprehensive test script to run all adapters and compare results."""

import subprocess
import json
import time
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

DB_PATH = "data/uwss_clean.sqlite"
CONFIG_PATH = "config/config.yaml"

def run_command(cmd, description):
    """Run a CLI command and return success status."""
    console.print(f"[cyan]Running: {description}[/cyan]")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        if result.returncode == 0:
            console.print(f"[green][OK] {description} - SUCCESS[/green]")
            return True
        else:
            console.print(f"[red][FAIL] {description} - FAILED[/red]")
            console.print(f"[yellow]{result.stderr}[/yellow]")
            return False
    except subprocess.TimeoutExpired:
        console.print(f"[red][TIMEOUT] {description} - TIMEOUT[/red]")
        return False
    except Exception as e:
        console.print(f"[red][ERROR] {description} - ERROR: {e}[/red]")
        return False

def analyze_database(db_path, source_name):
    """Analyze database and return statistics."""
    import sqlite3
    
    if not Path(db_path).exists():
        return None
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM documents")
        total = cursor.fetchone()[0]
        
        if total == 0:
            return None
        
        # Get completeness stats
        cursor.execute("""
            SELECT 
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
        
        return {
            "source": source_name,
            "total": total,
            "has_title": row[0],
            "has_abstract": row[1],
            "has_authors": row[2],
            "has_doi": row[3],
            "has_year": row[4],
            "has_oa": row[5],
            "unique_doi": row[6],
        }
    finally:
        conn.close()

def main():
    console.print("[bold blue]=" * 80)
    console.print("[bold blue]COMPREHENSIVE DATABASE TEST - ALL SOURCES[/bold blue]")
    console.print("[bold blue]=" * 80)
    console.print()
    
    # Initialize database
    console.print("[bold]Step 1: Initialize Database[/bold]")
    run_command(
        f'python -m src.uwss.cli db-init --db {DB_PATH}',
        "Initialize database"
    )
    run_command(
        f'python -m src.uwss.cli db-migrate --db {DB_PATH}',
        "Run migrations"
    )
    console.print()
    
    # Test each source
    sources = [
        {
            "name": "OpenAlex",
            "cmd": f'python -m src.uwss.cli openalex-discover --db {DB_PATH} --max 100 --metrics-out data/openalex_metrics.json',
            "description": "OpenAlex discovery (100 records)"
        },
        {
            "name": "Crossref",
            "cmd": f'python -m src.uwss.cli crossref-discover --db {DB_PATH} --max 100 --metrics-out data/crossref_metrics.json',
            "description": "Crossref discovery (100 records)"
        },
    ]
    
    console.print("[bold]Step 2: Run Discovery for Each Source[/bold]")
    results = {}
    
    for source in sources:
        console.print()
        console.print(f"[bold yellow]Testing: {source['name']}[/bold yellow]")
        start_time = time.time()
        
        success = run_command(source["cmd"], source["description"])
        
        elapsed = time.time() - start_time
        
        if success:
            # Analyze results
            stats = analyze_database(DB_PATH, source["name"])
            if stats:
                results[source["name"]] = {
                    **stats,
                    "elapsed_sec": round(elapsed, 2),
                    "status": "SUCCESS"
                }
            else:
                results[source["name"]] = {
                    "status": "NO_DATA",
                    "elapsed_sec": round(elapsed, 2)
                }
        else:
            results[source["name"]] = {
                "status": "FAILED",
                "elapsed_sec": round(elapsed, 2)
            }
        
        time.sleep(2)  # Brief pause between sources
    
    console.print()
    console.print("[bold]Step 3: Analysis & Comparison[/bold]")
    console.print()
    
    # Display comparison table
    if results:
        table = Table(title="Database Comparison Results")
        table.add_column("Source", style="cyan")
        table.add_column("Records", justify="right")
        table.add_column("Title %", justify="right")
        table.add_column("Abstract %", justify="right")
        table.add_column("Authors %", justify="right")
        table.add_column("DOI %", justify="right")
        table.add_column("OA %", justify="right")
        table.add_column("Time (s)", justify="right")
        table.add_column("Status", style="green")
        
        for source_name, stats in results.items():
            if stats.get("status") == "SUCCESS":
                total = stats["total"]
                table.add_row(
                    source_name,
                    str(total),
                    f"{stats['has_title']/total*100:.1f}%" if total > 0 else "0%",
                    f"{stats['has_abstract']/total*100:.1f}%" if total > 0 else "0%",
                    f"{stats['has_authors']/total*100:.1f}%" if total > 0 else "0%",
                    f"{stats['has_doi']/total*100:.1f}%" if total > 0 else "0%",
                    f"{stats['has_oa']/total*100:.1f}%" if total > 0 else "0%",
                    str(stats.get("elapsed_sec", 0)),
                    stats.get("status", "UNKNOWN")
                )
            else:
                table.add_row(
                    source_name,
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    "-",
                    str(stats.get("elapsed_sec", 0)),
                    stats.get("status", "FAILED/NO_DATA")
                )
        
        console.print(table)
        console.print()
        
        # Save results
        output_path = Path("data/comprehensive_test_results.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        console.print(f"[green]Results saved to: {output_path}[/green]")
    
    console.print()
    console.print("[bold green]=" * 80)
    console.print("[bold green]COMPREHENSIVE TEST COMPLETED[/bold green]")
    console.print("[bold green]=" * 80)

if __name__ == "__main__":
    main()

