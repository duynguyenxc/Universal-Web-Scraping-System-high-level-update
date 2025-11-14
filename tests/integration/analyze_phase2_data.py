"""Analyze Phase 2 test data in detail."""

import json
import sys
from pathlib import Path
from collections import Counter

# Fix encoding for Windows
sys.stdout.reconfigure(encoding='utf-8')

# Get project root
project_root = Path(__file__).parent.parent.parent

# Read exported data
export_file = project_root / "data" / "phase2_test_export.jsonl"
if export_file.exists():
    with open(export_file, 'r', encoding='utf-8') as f:
        exported = [json.loads(line) for line in f if line.strip()]
else:
    exported = []

print("="*80)
print("PHASE 2 TEST DATA ANALYSIS")
print("="*80)

if exported:
    print(f"\n📊 EXPORTED DATA SUMMARY")
    print(f"{'='*80}")
    print(f"Total documents exported: {len(exported)}")
    print(f"Average relevance score: {sum(d.get('relevance_score', 0) for d in exported)/len(exported):.3f}")
    print(f"Documents with DOI: {sum(1 for d in exported if d.get('doi'))}/{len(exported)} ({sum(1 for d in exported if d.get('doi'))*100/len(exported):.0f}%)")
    print(f"Documents with authors: {sum(1 for d in exported if d.get('authors'))}/{len(exported)} ({sum(1 for d in exported if d.get('authors'))*100/len(exported):.0f}%)")
    print(f"Documents with abstract: {sum(1 for d in exported if d.get('abstract'))}/{len(exported)} ({sum(1 for d in exported if d.get('abstract'))*100/len(exported):.0f}%)")
    
    # Year distribution
    years = [d.get('year') for d in exported if d.get('year')]
    if years:
        print(f"\nYear distribution:")
        year_counts = Counter(years)
        for year, count in sorted(year_counts.items()):
            print(f"  {year}: {count} documents")
    
    # Source distribution
    sources = [d.get('source', 'Unknown') for d in exported]
    source_counts = Counter(sources)
    print(f"\nSource distribution:")
    for source, count in source_counts.items():
        print(f"  {source}: {count} documents")
    
    print(f"\n{'='*80}")
    print("📄 DETAILED DOCUMENTS")
    print(f"{'='*80}")
    
    for i, doc in enumerate(exported, 1):
        print(f"\n{i}. {doc.get('title', 'No title')}")
        print(f"   └─ Relevance Score: {doc.get('relevance_score', 0):.3f}")
        print(f"   └─ Year: {doc.get('year', 'N/A')}")
        print(f"   └─ DOI: {doc.get('doi', 'N/A')}")
        print(f"   └─ Source: {doc.get('source', 'Unknown')}")
        print(f"   └─ Authors: {doc.get('authors', 'N/A')}")
        if doc.get('abstract'):
            abstract = doc.get('abstract', '')
            print(f"   └─ Abstract: {abstract[:100]}..." if len(abstract) > 100 else f"   └─ Abstract: {abstract}")
        print(f"   └─ URL: {doc.get('source_url', 'N/A')}")
else:
    print("\n⚠️  No exported data found!")

# Analyze full database
print(f"\n{'='*80}")
print("📊 FULL DATABASE ANALYSIS")
print(f"{'='*80}")

try:
    from src.uwss.store.db import create_sqlite_engine
    from src.uwss.store.models import Document
    
    engine, SessionLocal = create_sqlite_engine(project_root / "data" / "phase2_test.sqlite")
    session = SessionLocal()
    
    all_docs = session.query(Document).all()
    print(f"\nTotal documents in database: {len(all_docs)}")
    
    if all_docs:
        # By source
        sources = Counter(d.source for d in all_docs)
        print(f"\nBy source:")
        for source, count in sources.items():
            print(f"  {source or 'None'}: {count} documents")
        
        # Score distribution
        scored = [d.relevance_score for d in all_docs if d.relevance_score is not None]
        if scored:
            print(f"\nScore distribution:")
            print(f"  Average: {sum(scored)/len(scored):.3f}")
            print(f"  Min: {min(scored):.3f}")
            print(f"  Max: {max(scored):.3f}")
            print(f"  Perfect scores (1.0): {sum(1 for s in scored if s == 1.0)} ({sum(1 for s in scored if s == 1.0)*100/len(scored):.0f}%)")
            print(f"  High scores (>=0.8): {sum(1 for s in scored if s >= 0.8)} ({sum(1 for s in scored if s >= 0.8)*100/len(scored):.0f}%)")
            print(f"  Medium scores (0.5-0.8): {sum(1 for s in scored if 0.5 <= s < 0.8)} ({sum(1 for s in scored if 0.5 <= s < 0.8)*100/len(scored):.0f}%)")
            print(f"  Low scores (<0.5): {sum(1 for s in scored if s < 0.5)} ({sum(1 for s in scored if s < 0.5)*100/len(scored):.0f}%)")
        
        # Quality metrics
        with_abstract = sum(1 for d in all_docs if d.abstract and len(d.abstract) > 50)
        with_authors = sum(1 for d in all_docs if d.authors)
        with_doi = sum(1 for d in all_docs if d.doi)
        with_fulltext = sum(1 for d in all_docs if d.content_path)
        
        print(f"\nQuality metrics:")
        print(f"  With abstract (>50 chars): {with_abstract}/{len(all_docs)} ({with_abstract*100/len(all_docs):.1f}%)")
        print(f"  With authors: {with_authors}/{len(all_docs)} ({with_authors*100/len(all_docs):.1f}%)")
        print(f"  With DOI: {with_doi}/{len(all_docs)} ({with_doi*100/len(all_docs):.1f}%)")
        print(f"  With full-text: {with_fulltext}/{len(all_docs)} ({with_fulltext*100/len(all_docs):.1f}%)")
        
        # Top documents
        top_docs = sorted([d for d in all_docs if d.relevance_score], 
                         key=lambda x: x.relevance_score, reverse=True)[:5]
        if top_docs:
            print(f"\n🏆 Top 5 documents by relevance score:")
            for i, doc in enumerate(top_docs, 1):
                print(f"  {i}. Score {doc.relevance_score:.3f}: {doc.title[:70] if doc.title else 'No title'}...")
                print(f"     Year: {doc.year or 'N/A'}, DOI: {doc.doi or 'N/A'}")
    
    session.close()
    
except Exception as e:
    print(f"\n⚠️  Error analyzing database: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*80}")
print("✅ ANALYSIS COMPLETE")
print(f"{'='*80}")

