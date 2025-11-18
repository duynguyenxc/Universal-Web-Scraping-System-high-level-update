#!/usr/bin/env python3
"""CLI command for Semantic Scholar API discovery."""

import click
from pathlib import Path

from ...sources.semantic_scholar_api import SemanticScholarAPIAdapter


@click.command()
@click.option(
    '--max',
    default=50,
    help='Maximum number of papers to discover'
)
@click.option(
    '--start-year',
    default=2015,
    help='Only papers from this year onwards'
)
@click.option(
    '--output',
    default='data/semantic_scholar_api_corrosion.jsonl',
    help='Output file for discovered papers'
)
@click.option(
    '--api-key',
    default='mi2Gv4dHkE8Zk4gNWItxJ747ijFIKLVX7ZZjMkjT',
    help='Semantic Scholar API key'
)
def semantic_scholar_api_discover(max, start_year, output, api_key):
    """
    Discover corrosion-related papers from Semantic Scholar API.

    This command searches Semantic Scholar for corrosion research papers
    using comprehensive search queries and rate-limited API calls.
    """
    import json
    from datetime import datetime

    click.echo("Starting Semantic Scholar API corrosion discovery")
    click.echo(f"   API Key: {api_key[:10]}...")
    click.echo(f"   Max papers: {max}")
    click.echo(f"   Start year: {start_year}")
    click.echo(f"   Output: {output}")
    click.echo("   Rate limit: 1 request/second")
    click.echo()

    # Initialize adapter
    adapter = SemanticScholarAPIAdapter(api_key=api_key)

    # Ensure output directory exists
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Discover papers
    discovered_count = 0

    with open(output_path, 'w', encoding='utf-8') as f:
        try:
            for document in adapter.discover_corrosion_papers(
                max_records=max,
                start_year=start_year
            ):
                # Convert Document to dict for JSON serialization
                doc_dict = {
                    'title': document.title,
                    'abstract': document.abstract,
                    'authors': document.authors,
                    'doi': document.doi,
                    'url': document.url,
                    'pdf_url': document.pdf_url,
                    'year': document.year,
                    'venue': document.venue,
                    'source': document.source,
                    'source_type': document.source_type,
                    'metadata': document.metadata or {},
                    'discovered_at': datetime.now().isoformat()
                }

                # Write to file
                json.dump(doc_dict, f, ensure_ascii=False)
                f.write('\n')

                discovered_count += 1

                # Progress indicator
                if discovered_count % 5 == 0:
                    click.echo(f"   Progress: {discovered_count} papers discovered")

        except KeyboardInterrupt:
            click.echo("\nInterrupted by user")
        except Exception as e:
            click.echo(f"Error during discovery: {e}", err=True)
            return

    click.echo(f"Discovery completed: {discovered_count} papers")
    click.echo(f"   Saved to: {output_path}")

    if discovered_count > 0:
        click.echo("\nAnalysis:")

        # Quick analysis
        corrosion_related = 0
        with open(output_path, 'r', encoding='utf-8') as f:
            for line in f:
                doc = json.loads(line)
                text = (doc.get('title', '') + ' ' + doc.get('abstract', '')).lower()
                if any(kw in text for kw in ['corrosion', 'corrosive', 'corroded', 'oxidation', 'rust', 'pitting']):
                    corrosion_related += 1

        click.echo(f"   - Corrosion-related: {corrosion_related}/{discovered_count} ({corrosion_related/discovered_count*100:.1f}%)")

        click.echo("\nNext steps:")
        click.echo("   1. Review discovered papers")
        click.echo("   2. Run scoring: uwss score-keywords")
        click.echo("   3. Export: uwss export")
        click.echo("   4. Fetch PDFs: uwss fetch-pdfs")


if __name__ == '__main__':
    semantic_scholar_api_discover()
