"""Test Phase 2: Web Crawling Expansion

Tests:
1. Seed discovery from database
2. Enhanced scoring with full-text
3. Quality filtering
4. Research spider (basic test)
"""

import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()

def test_seed_discovery():
    """Test seed discovery from database."""
    console.print("\n[cyan]=== Test 1: Seed Discovery ===[/cyan]")
    
    try:
        from src.uwss.discovery.seed_finder import find_seeds_from_database, find_seeds_from_papers
        
        # Find existing database
        db_paths = [
            "data/phase1_large_test.sqlite",
            "data/uwss.sqlite",
            "data/phase1_full_test.sqlite"
        ]
        db_path = None
        for path in db_paths:
            if Path(path).exists():
                db_path = path
                break
        
        if not db_path:
            console.print("[yellow]No database found, skipping seed discovery test[/yellow]")
            return False
        
        console.print(f"[green]Using database: {db_path}[/green]")
        
        # Test database seed discovery
        seeds1 = find_seeds_from_database(db_path, keywords=["concrete", "corrosion"], limit=10)
        console.print(f"[green][OK] Database seed discovery: {len(seeds1)} seeds[/green]")
        if seeds1:
            console.print(f"  Sample: {seeds1[0]}")
        
        # Test paper seed discovery
        seeds2 = find_seeds_from_papers(db_path, limit=10)
        console.print(f"[green][OK] Paper seed discovery: {len(seeds2)} seeds[/green]")
        if seeds2:
            console.print(f"  Sample: {seeds2[0]}")
        
        return len(seeds1) > 0 or len(seeds2) > 0
        
    except Exception as e:
        console.print(f"[red][ERROR] Seed discovery failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_enhanced_scoring():
    """Test enhanced scoring with full-text."""
    console.print("\n[cyan]=== Test 2: Enhanced Scoring ===[/cyan]")
    
    try:
        from src.uwss.score import score_documents
        
        # Find existing database
        db_paths = [
            "data/phase1_large_test.sqlite",
            "data/uwss.sqlite",
            "data/phase1_full_test.sqlite"
        ]
        db_path = None
        for path in db_paths:
            if Path(path).exists():
                db_path = path
                break
        
        if not db_path:
            console.print("[yellow]No database found, skipping scoring test[/yellow]")
            return False
        
        console.print(f"[green]Using database: {db_path}[/green]")
        
        keywords = [
            "reinforced concrete",
            "corrosion",
            "durability",
            "chloride",
            "deterioration"
        ]
        
        # Test scoring with full-text
        updated = score_documents(
            Path(db_path),
            keywords,
            use_fulltext=True
        )
        console.print(f"[green][OK] Enhanced scoring: {updated} documents scored[/green]")
        
        # Check scores
        from sqlalchemy import select
        from src.uwss.store.db import create_sqlite_engine
        from src.uwss.store.models import Document
        
        engine, SessionLocal = create_sqlite_engine(Path(db_path))
        session = SessionLocal()
        try:
            docs = session.query(Document).filter(
                Document.relevance_score.isnot(None)
            ).order_by(Document.relevance_score.desc()).limit(5).all()
            
            if docs:
                console.print(f"[green]Top 5 scores:[/green]")
                for doc in docs:
                    console.print(f"  ID {doc.id}: {doc.relevance_score:.3f} - {doc.title[:50] if doc.title else 'No title'}...")
        finally:
            session.close()
        
        return updated > 0
        
    except Exception as e:
        console.print(f"[red][ERROR] Enhanced scoring failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_quality_filtering():
    """Test quality filtering."""
    console.print("\n[cyan]=== Test 3: Quality Filtering ===[/cyan]")
    
    try:
        from src.uwss.quality import assess_document_quality, filter_high_quality
        from src.uwss.store.db import create_sqlite_engine
        from src.uwss.store.models import Document
        
        # Find existing database
        db_paths = [
            "data/phase1_large_test.sqlite",
            "data/uwss.sqlite",
            "data/phase1_full_test.sqlite"
        ]
        db_path = None
        for path in db_paths:
            if Path(path).exists():
                db_path = path
                break
        
        if not db_path:
            console.print("[yellow]No database found, skipping quality filtering test[/yellow]")
            return False
        
        console.print(f"[green]Using database: {db_path}[/green]")
        
        engine, SessionLocal = create_sqlite_engine(Path(db_path))
        session = SessionLocal()
        try:
            # Test quality assessment
            docs = session.query(Document).limit(10).all()
            if docs:
                console.print(f"[green]Assessing quality for {len(docs)} documents...[/green]")
                for doc in docs[:3]:
                    quality = assess_document_quality(doc)
                    console.print(f"  ID {doc.id}: relevance={quality['relevance']:.2f}, completeness={quality['completeness']:.2f}, overall={quality['overall_quality']:.2f}")
            
            # Test quality filtering
            high_quality = filter_high_quality(
                session,
                min_relevance=0.3,
                min_completeness=0.2,
                min_overall=0.3,
                limit=10
            )
            console.print(f"[green][OK] Quality filtering: {len(high_quality)} high-quality documents[/green]")
            
            if high_quality:
                console.print(f"[green]Sample high-quality documents:[/green]")
                for doc in high_quality[:3]:
                    quality = assess_document_quality(doc)
                    console.print(f"  ID {doc.id}: {doc.title[:50] if doc.title else 'No title'}... (quality: {quality['overall_quality']:.2f})")
            
            return len(high_quality) > 0
            
        finally:
            session.close()
        
    except Exception as e:
        console.print(f"[red][ERROR] Quality filtering failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_extractors():
    """Test metadata extractors."""
    console.print("\n[cyan]=== Test 4: Metadata Extractors ===[/cyan]")
    
    try:
        from src.uwss.crawl.extractors import extract_metadata, extract_pdf_metadata, extract_researcher_info
        
        # Test HTML extractor
        sample_html = """
        <html>
        <head>
            <title>Test Document</title>
            <meta name="citation_title" content="Test Title">
            <meta name="citation_abstract" content="This is a test abstract about concrete corrosion.">
        </head>
        <body>
            <h1>Test Document</h1>
            <p>This is a test document about reinforced concrete durability.</p>
        </body>
        </html>
        """
        
        metadata = extract_metadata(sample_html, "https://example.com/test")
        console.print(f"[green][OK] HTML extractor: title='{metadata.get('title', 'N/A')}', abstract={len(metadata.get('abstract', ''))} chars[/green]")
        
        # Test researcher extractor
        researcher_html = """
        <html>
        <head><title>Dr. John Smith - Research</title></head>
        <body>
            <h1>Dr. John Smith</h1>
            <p>Email: john.smith@university.edu</p>
            <p>Affiliation: University of Engineering</p>
            <p>Research Interests: Concrete durability, Corrosion</p>
        </body>
        </html>
        """
        
        researcher_info = extract_researcher_info(researcher_html, "https://example.com/researcher")
        console.print(f"[green][OK] Researcher extractor: name='{researcher_info.get('name', 'N/A')}', email='{researcher_info.get('email', 'N/A')}'[/green]")
        
        return True
        
    except Exception as e:
        console.print(f"[red][ERROR] Extractor test failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Phase 2 tests."""
    console.print("[bold cyan]Phase 2: Web Crawling Expansion - Test Suite[/bold cyan]")
    console.print("=" * 60)
    
    results = {}
    
    # Test 1: Seed Discovery
    results["Seed Discovery"] = test_seed_discovery()
    
    # Test 2: Enhanced Scoring
    results["Enhanced Scoring"] = test_enhanced_scoring()
    
    # Test 3: Quality Filtering
    results["Quality Filtering"] = test_quality_filtering()
    
    # Test 4: Extractors
    results["Extractors"] = test_extractors()
    
    # Summary
    console.print("\n[bold cyan]=== Test Summary ===[/bold cyan]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Test", style="cyan")
    table.add_column("Status", style="green")
    
    for test_name, passed in results.items():
        status = "[OK] PASS" if passed else "[FAIL]"
        table.add_row(test_name, status)
    
    console.print(table)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    console.print(f"\n[bold]Total: {passed}/{total} tests passed[/bold]")
    
    if passed == total:
        console.print("[bold green][OK] All tests passed![/bold green]")
        return 0
    else:
        console.print("[bold yellow][WARNING] Some tests failed. Check output above.[/bold yellow]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
