"""Comprehensive Phase 2 test - Full pipeline from discovery to quality filtering."""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.uwss.store.db import create_sqlite_engine
from src.uwss.store.models import Document
from src.uwss.quality import assess_document_quality, filter_high_quality
from src.uwss.discovery.seed_finder import find_seeds_from_database, find_seeds_from_papers
from sqlalchemy import select, func
import subprocess

def run_command(cmd, description):
    """Run a CLI command and return output."""
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            print(f"[OK] {description} completed")
            if result.stdout:
                print(result.stdout[:500])  # Print first 500 chars
            return True
        else:
            print(f"[ERROR] {description} failed")
            print(result.stderr[:500] if result.stderr else "No error output")
            return False
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        return False

def analyze_database(db_path):
    """Analyze database contents."""
    print(f"\n{'='*60}")
    print("DATABASE ANALYSIS")
    print(f"{'='*60}")
    
    engine, SessionLocal = create_sqlite_engine(Path(db_path))
    session = SessionLocal()
    
    try:
        # Total documents
        total = session.query(Document).count()
        print(f"Total documents: {total}")
        
        if total == 0:
            print("[WARNING] Database is empty!")
            return
        
        # By source
        sources = session.query(Document.source, func.count(Document.id)).group_by(Document.source).all()
        print(f"\nBy source:")
        for source, count in sources:
            print(f"  {source or 'None'}: {count}")
        
        # With relevance scores
        with_scores = session.query(Document).filter(Document.relevance_score.isnot(None)).count()
        print(f"\nDocuments with relevance scores: {with_scores}/{total} ({with_scores*100/total:.1f}%)")
        
        # Score distribution
        if with_scores > 0:
            avg_score = session.query(func.avg(Document.relevance_score)).scalar()
            max_score = session.query(func.max(Document.relevance_score)).scalar()
            min_score = session.query(func.min(Document.relevance_score)).scalar()
            print(f"  Average score: {avg_score:.3f}")
            print(f"  Min score: {min_score:.3f}")
            print(f"  Max score: {max_score:.3f}")
        
        # Quality metrics
        with_abstract = session.query(Document).filter(
            Document.abstract.isnot(None),
            func.length(Document.abstract) > 50
        ).count()
        with_authors = session.query(Document).filter(Document.authors.isnot(None)).count()
        with_doi = session.query(Document).filter(Document.doi.isnot(None)).count()
        with_fulltext = session.query(Document).filter(Document.content_path.isnot(None)).count()
        
        print(f"\nQuality metrics:")
        print(f"  With abstract (>50 chars): {with_abstract}/{total} ({with_abstract*100/total:.1f}%)")
        print(f"  With authors: {with_authors}/{total} ({with_authors*100/total:.1f}%)")
        print(f"  With DOI: {with_doi}/{total} ({with_doi*100/total:.1f}%)")
        print(f"  With full-text: {with_fulltext}/{total} ({with_fulltext*100/total:.1f}%)")
        
        # High-quality documents
        high_quality = filter_high_quality(
            session,
            min_relevance=0.3,
            min_completeness=0.3,
            min_overall=0.3,
            limit=10
        )
        print(f"\nHigh-quality documents (relevance>=0.3, completeness>=0.3): {len(high_quality)}")
        
        # Sample high-quality documents
        if high_quality:
            print(f"\nSample high-quality documents:")
            for doc in high_quality[:5]:
                quality = assess_document_quality(doc)
                print(f"  ID {doc.id}: {doc.title[:60] if doc.title else 'No title'}...")
                print(f"    Relevance: {quality['relevance']:.2f}, "
                      f"Completeness: {quality['completeness']:.2f}, "
                      f"Overall: {quality['overall_quality']:.2f}")
        
        # Top scored documents
        top_docs = session.query(Document).filter(
            Document.relevance_score.isnot(None)
        ).order_by(Document.relevance_score.desc()).limit(5).all()
        
        if top_docs:
            print(f"\nTop 5 scored documents:")
            for doc in top_docs:
                print(f"  ID {doc.id}: score={doc.relevance_score:.3f}, "
                      f"title='{doc.title[:50] if doc.title else 'No title'}...'")
        
    finally:
        session.close()

def test_seed_discovery(db_path):
    """Test seed discovery."""
    print(f"\n{'='*60}")
    print("SEED DISCOVERY TEST")
    print(f"{'='*60}")
    
    try:
        seeds1 = find_seeds_from_database(db_path, keywords=["concrete", "corrosion"], limit=10)
        seeds2 = find_seeds_from_papers(db_path, limit=10)
        all_seeds = list(set(seeds1 + seeds2))
        
        print(f"Seeds from database: {len(seeds1)}")
        print(f"Seeds from papers: {len(seeds2)}")
        print(f"Total unique seeds: {len(all_seeds)}")
        
        if all_seeds:
            print(f"\nSample seeds:")
            for seed in all_seeds[:5]:
                print(f"  {seed}")
        
        return all_seeds
    except Exception as e:
        print(f"[ERROR] Seed discovery failed: {e}")
        import traceback
        traceback.print_exc()
        return []

def main():
    """Run comprehensive Phase 2 test."""
    print("="*60)
    print("PHASE 2 COMPREHENSIVE TEST")
    print("="*60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test database (in project root data directory)
    project_root = Path(__file__).parent.parent.parent
    test_db = str(project_root / "data" / "phase2_test.sqlite")
    
    # Step 1: Initialize database
    print(f"\n{'='*60}")
    print("STEP 1: Initialize Database")
    print(f"{'='*60}")
    run_command(
        ["python", "-m", "src.uwss.cli", "db-init", "--db", test_db],
        "Database initialization"
    )
    
    # Step 2: Run discovery (small sample)
    print(f"\n{'='*60}")
    print("STEP 2: Discovery (Small Sample)")
    print(f"{'='*60}")
    
    # arXiv
    run_command(
        ["python", "-m", "src.uwss.cli", "arxiv-harvest-oai", "--db", test_db, "--max", "20"],
        "arXiv discovery"
    )
    
    # Crossref
    run_command(
        ["python", "-m", "src.uwss.cli", "crossref-discover", "--db", test_db, "--max", "20"],
        "Crossref discovery"
    )
    
    # Step 3: Score documents
    print(f"\n{'='*60}")
    print("STEP 3: Score Documents (with full-text)")
    print(f"{'='*60}")
    run_command(
        ["python", "-m", "src.uwss.cli", "score-keywords", "--db", test_db, "--use-fulltext"],
        "Scoring with full-text support"
    )
    
    # Step 4: Analyze database
    analyze_database(test_db)
    
    # Step 5: Test seed discovery
    seeds = test_seed_discovery(test_db)
    
    # Step 6: Export high-quality data
    print(f"\n{'='*60}")
    print("STEP 6: Export High-Quality Data")
    print(f"{'='*60}")
    project_root = Path(__file__).parent.parent.parent
    export_file = str(project_root / "data" / "phase2_test_export.jsonl")
    run_command(
        ["python", "-m", "src.uwss.cli", "export",
         "--db", test_db,
         "--out", export_file,
         "--require-match",
         "--require-abstract",
         "--min-abstract-length", "50",
         "--min-score", "0.3"],
        "Export high-quality data"
    )
    
    # Analyze export
    if Path(export_file).exists():
        print(f"\nExport analysis:")
        with open(export_file, 'r', encoding='utf-8') as f:
            exported = [json.loads(line) for line in f if line.strip()]
        print(f"  Total exported: {len(exported)}")
        if exported:
            avg_score = sum(d.get("relevance_score", 0) for d in exported) / len(exported)
            print(f"  Average relevance score: {avg_score:.3f}")
            print(f"  With abstract: {sum(1 for d in exported if d.get('abstract'))}")
            print(f"  With DOI: {sum(1 for d in exported if d.get('doi'))}")
            print(f"\n  Sample exported documents:")
            for doc in exported[:3]:
                print(f"    - {doc.get('title', 'No title')[:60]}...")
                print(f"      Score: {doc.get('relevance_score', 0):.3f}, "
                      f"Source: {doc.get('source', 'Unknown')}")
    
    # Step 7: Test quality filter
    print(f"\n{'='*60}")
    print("STEP 7: Quality Filter Test")
    print(f"{'='*60}")
    project_root = Path(__file__).parent.parent.parent
    quality_ids_file = str(project_root / "data" / "phase2_quality_ids.txt")
    run_command(
        ["python", "-m", "src.uwss.cli", "quality-filter",
         "--db", test_db,
         "--min-relevance", "0.4",
         "--min-completeness", "0.3",
         "--require-abstract",
         "--out", quality_ids_file],
        "Quality filtering"
    )
    
    # Final summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nDatabase: {test_db}")
    print(f"Export file: {export_file}")
    print(f"Quality IDs file: {quality_ids_file}")
    print(f"\nPhase 2 test completed!")
    print(f"\nNext steps:")
    print(f"  1. Review exported data: {export_file}")
    print(f"  2. Use seeds for web crawling: {len(seeds)} seeds discovered")
    print(f"  3. Test web crawling with: crawl-research --seeds <URL>")

if __name__ == "__main__":
    main()

