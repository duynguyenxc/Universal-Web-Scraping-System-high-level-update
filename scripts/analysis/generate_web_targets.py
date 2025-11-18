#!/usr/bin/env python3
"""
Generate Web Targets Configuration from Database Analysis

This script analyzes existing documents in the database to identify academic domains
that are likely to contain more relevant content for web crawling.

Usage:
    python scripts/analysis/generate_web_targets.py --output config/web_domain_crawler.yaml
"""

import os
import sys
from urllib.parse import urlparse
from collections import Counter, defaultdict
import yaml
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from uwss.store.models import Document, Base
from uwss.store.db import create_sqlite_engine, create_engine_from_url


def extract_domain(url: str) -> str | None:
    """Extract clean domain from URL."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return None


def is_academic_domain(domain: str) -> bool:
    """Check if domain appears to be academic."""
    if not domain:
        return False

    # Academic institution indicators
    academic_indicators = [
        '.edu', '.ac.uk', '.ac.nz', '.ac.au', '.ac.ca', '.ac.jp',
        'univ-', '-university', 'college', 'institute', 'research',
        'science', 'engineering', 'medicine'
    ]

    # Publisher domains
    publishers = [
        'springer.com', 'elsevier.com', 'wiley.com', 'tandfonline.com',
        'sagepub.com', 'oxfordjournals.org', 'cambridge.org', 'nature.com',
        'science.org', 'mdpi.com', 'plos.org', 'frontiersin.org',
        'hindawi.com', 'peerj.com', 'bmc.com', 'europepmc.org'
    ]

    # Repository domains
    repositories = [
        'arxiv.org', 'biorxiv.org', 'medrxiv.org', 'zenodo.org',
        'figshare.com', 'osf.io', 'psyarxiv.com', 'socarxiv.org'
    ]

    # Check academic indicators
    for indicator in academic_indicators:
        if indicator in domain:
            return True

    # Check known publishers/repositories
    if domain in publishers or domain in repositories:
        return True

    return False


def generate_web_targets(
    output_file: str | None = None,
    min_relevance: float = 0.5,
    min_papers: int = 3,
    max_domains: int = 50,
    db_path: str = "data/uwss.sqlite",
    db_url: str | None = None
) -> dict:
    """
    Generate web targets configuration from database analysis.

    Args:
        output_file: Path to output YAML file
        min_relevance: Minimum relevance score threshold
        min_papers: Minimum papers per domain
        max_domains: Maximum domains to include

    Returns:
        Configuration dictionary
    """
    print("Analyzing database for web crawl targets...")
    print(f"   Min relevance: {min_relevance}")
    print(f"   Min papers per domain: {min_papers}")
    print(f"   Max domains: {max_domains}")

    # Create database session
    if db_url:
        engine, SessionLocal = create_engine_from_url(db_url)
    else:
        engine, SessionLocal = create_sqlite_engine(Path(db_path))

    Base.metadata.create_all(engine)
    session = SessionLocal()

    try:
        # Query relevant documents
        query = session.query(Document).filter(
            Document.relevance_score >= min_relevance
        )

        total_docs = query.count()
        print(f"   Found {total_docs} relevant documents")

        if total_docs == 0:
            print("❌ No relevant documents found in database")
            print("   Run discovery and scoring first:")
            print("   uwss paperscraper-discover --max 100")
            print("   uwss score-keywords --config config/config.yaml")
            return {}

        # Analyze domains
        domain_stats = defaultdict(lambda: {
            'count': 0,
            'total_relevance': 0.0,
            'sources': Counter(),
            'has_pdf': 0,
            'avg_year': [],
            'sample_urls': []
        })

        processed = 0
        for doc in query.yield_per(1000):
            # Extract domains from all URL fields
            urls = []
            if doc.source_url:
                urls.append(doc.source_url)
            if doc.landing_url:
                urls.append(doc.landing_url)
            if doc.pdf_url:
                urls.append(doc.pdf_url)

            for url in urls:
                domain = extract_domain(url)
                if domain and is_academic_domain(domain):
                    stats = domain_stats[domain]
                    stats['count'] += 1
                    stats['total_relevance'] += doc.relevance_score or 0
                    stats['sources'][doc.source or 'unknown'] += 1
                    if doc.pdf_url:
                        stats['has_pdf'] += 1
                    if doc.year:
                        stats['avg_year'].append(doc.year)
                    if len(stats['sample_urls']) < 3 and url not in stats['sample_urls']:
                        stats['sample_urls'].append(url)

            processed += 1
            if processed % 5000 == 0:
                print(f"   Processed {processed}/{total_docs} documents")

        # Generate targets
        web_targets = []

        for domain, stats in domain_stats.items():
            if stats['count'] >= min_papers:
                avg_relevance = stats['total_relevance'] / stats['count']
                pdf_ratio = stats['has_pdf'] / stats['count']
                avg_year = (
                    sum(stats['avg_year']) / len(stats['avg_year'])
                    if stats['avg_year'] else None
                )

                target = {
                    'domain': domain,
                    'max_pages': min(500, stats['count'] * 2),
                    'allow_pdf_only': pdf_ratio > 0.7,
                    'quality_score': round(avg_relevance, 3),
                    'estimated_papers': stats['count'],
                    'pdf_ratio': round(pdf_ratio, 3),
                    'primary_sources': dict(stats['sources'].most_common(3)),
                    'avg_publication_year': int(avg_year) if avg_year else None,
                    'sample_urls': stats['sample_urls'],
                    'crawl_status': 'active'
                }

                web_targets.append(target)

        # Sort by quality and paper count
        web_targets.sort(key=lambda x: (x['quality_score'], x['estimated_papers']), reverse=True)
        web_targets = web_targets[:max_domains]

        # Create full config
        config = {
            'web_domain_crawler': {
                'max_records': 1000,
                'delay_between_requests': 1.0,
                'max_crawl_depth': 2,
                'quality_check_interval': 50,
                'min_relevance_ratio': 0.2,
                'url_patterns': [
                    '.pdf', '/paper/', '/article/', '/publication/',
                    '/research/', '/proceedings/'
                ],
                'web_targets': web_targets
            },
            'generation': {
                'min_relevance_threshold': min_relevance,
                'min_papers_per_domain': min_papers,
                'max_domains': max_domains,
                'total_domains_analyzed': len(domain_stats),
                'academic_domains_selected': len(web_targets),
                'generated_at': datetime.now().isoformat(),
                'source': 'database_analysis'
            }
        }

        # Save or print
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

            print(f"Saved {len(web_targets)} web targets to {output_file}")
        else:
            print(yaml.dump(config, default_flow_style=False, sort_keys=False))

        # Print summary
        print(f"\nAnalysis Summary:")
        print(f"   Domains analyzed: {len(domain_stats)}")
        print(f"   Academic domains selected: {len(web_targets)}")

        if web_targets:
            avg_quality = sum(t['quality_score'] for t in web_targets) / len(web_targets)
            total_estimated = sum(t['estimated_papers'] for t in web_targets)
            print(".3f")
            print(f"   Total estimated papers: {total_estimated}")

            print("\nTop domains:")
            for i, target in enumerate(web_targets[:5], 1):
                print(f"   {i}. {target['domain']} (score: {target['quality_score']}, papers: {target['estimated_papers']})")
        return config

    finally:
        session.close()


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate web crawl targets from database analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate config for web crawler
  python scripts/analysis/generate_web_targets.py --output config/web_domain_crawler.yaml

  # Analyze with different thresholds
  python scripts/analysis/generate_web_targets.py --min-relevance 0.7 --max-domains 20

  # Preview without saving
  python scripts/analysis/generate_web_targets.py
        """
    )

    parser.add_argument(
        '--output', '-o',
        help='Output YAML configuration file'
    )

    parser.add_argument(
        '--min-relevance', '-r',
        type=float,
        default=0.5,
        help='Minimum relevance score (default: 0.5)'
    )

    parser.add_argument(
        '--min-papers', '-p',
        type=int,
        default=3,
        help='Minimum papers per domain (default: 3)'
    )

    parser.add_argument(
        '--max-domains', '-m',
        type=int,
        default=50,
        help='Maximum domains to include (default: 50)'
    )

    parser.add_argument(
        '--db',
        default='data/uwss.sqlite',
        help='Path to SQLite database file'
    )

    args = parser.parse_args()

    generate_web_targets(
        output_file=args.output,
        min_relevance=args.min_relevance,
        min_papers=args.min_papers,
        max_domains=args.max_domains,
        db_path=args.db
    )


if __name__ == '__main__':
    main()
