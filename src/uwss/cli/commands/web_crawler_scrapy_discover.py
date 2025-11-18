#!/usr/bin/env python3
"""CLI command for Scrapy-based web crawler discovery."""

import json
import logging
import sys
from pathlib import Path
from typing import Iterator, Dict, Any, List

import click
import yaml
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from uwss.sources.web_crawler_scrapy import ResearchGroupSpider
from uwss.sources.web_crawler_scrapy.pipeline import (
    MetadataExtractionPipeline,
    EmailExtractionPipeline,
    UWSSDocumentPipeline,
)

logger = logging.getLogger(__name__)


def load_config(config_file: str) -> Dict[str, Any]:
    """Load crawler configuration from YAML file."""
    config_path = Path(config_file)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


def setup_scrapy_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    """Setup Scrapy settings from config."""
    crawl_settings = config.get('crawl_settings', {})
    
    settings = {
        'ROBOTSTXT_OBEY': crawl_settings.get('respect_robots_txt', True),
        'DOWNLOAD_DELAY': crawl_settings.get('download_delay', 1.0),
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS_PER_DOMAIN': crawl_settings.get('concurrent_requests_per_domain', 2),
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 1,
        'AUTOTHROTTLE_MAX_DELAY': 10,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 2.0,
        'ITEM_PIPELINES': {
            'uwss.sources.web_crawler_scrapy.pipeline.MetadataExtractionPipeline': 300,
            'uwss.sources.web_crawler_scrapy.pipeline.EmailExtractionPipeline': 400,
            'uwss.sources.web_crawler_scrapy.pipeline.UWSSDocumentPipeline': 500,
        },
        'LOG_LEVEL': 'INFO',
    }
    
    return settings


# Global item collector
_items_collected = []

class CollectingPipeline:
    """Pipeline to collect items in memory."""
    def process_item(self, item, spider):
        _items_collected.append(dict(item))
        return item

def crawl_seed_url(
    seed_config: Dict[str, Any],
    global_keywords: List[str],
    output_file: str = None,
    output_items: List[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Crawl a single seed URL and return results."""
    global _items_collected
    _items_collected = []  # Reset for each crawl
    
    seed_url = seed_config.get('url')
    if not seed_url:
        logger.warning(f"Invalid seed config: missing URL")
        return []
    
    # Get keywords (seed-specific or global)
    keywords = seed_config.get('keywords', global_keywords)
    allowed_domains = seed_config.get('allowed_domains', [])
    max_depth = seed_config.get('max_depth', 2)
    max_pages = seed_config.get('max_pages', 100)
    
    # Setup Scrapy settings
    settings = setup_scrapy_settings({'crawl_settings': {}})
    settings['ITEM_PIPELINES'] = {
        'uwss.sources.web_crawler_scrapy.pipeline.MetadataExtractionPipeline': 300,
        'uwss.sources.web_crawler_scrapy.pipeline.EmailExtractionPipeline': 400,
        'uwss.sources.web_crawler_scrapy.pipeline.UWSSDocumentPipeline': 500,
        '__main__.CollectingPipeline': 600,
    }
    
    # Setup Scrapy process
    process = CrawlerProcess(settings)
    
    # Create spider
    process.crawl(
        ResearchGroupSpider,
        seed_url=seed_url,
        allowed_domains=allowed_domains,
        keywords=keywords,
        max_depth=max_depth,
        max_pages=max_pages,
    )
    
    # Run crawler (blocking)
    process.start()
    
    return _items_collected


@click.command()
@click.option(
    '--config',
    default='config/web_crawler_scrapy.yaml',
    help='Path to crawler configuration file',
    type=click.Path(exists=True)
)
@click.option(
    '--seed-url',
    help='Single seed URL to crawl (overrides config)',
    type=str
)
@click.option(
    '--keywords',
    help='Comma-separated keywords (overrides config)',
    type=str
)
@click.option(
    '--max-depth',
    help='Maximum crawl depth (overrides config)',
    type=int
)
@click.option(
    '--max-pages',
    help='Maximum pages to crawl (overrides config)',
    type=int
)
@click.option(
    '--output',
    help='Output JSONL file path',
    type=click.Path(),
    default='data/web_crawler_scrapy_results.jsonl'
)
@click.option(
    '--max-records',
    help='Maximum records to collect',
    type=int,
    default=100
)
def discover(
    config: str,
    seed_url: str,
    keywords: str,
    max_depth: int,
    max_pages: int,
    output: str,
    max_records: int
):
    """Crawl research group websites using Scrapy to find relevant content.
    
    This command starts from seed URLs (research group homepages) and follows
    links to discover relevant pages based on keywords. It extracts metadata
    including title, abstract, year, authors, group name, and contact emails.
    """
    click.echo("Starting Scrapy web crawler...")
    
    # Load config
    try:
        config_data = load_config(config)
    except Exception as e:
        click.echo(f"Error loading config: {e}", err=True)
        return
    
    # Get global keywords
    global_keywords = config_data.get('global_keywords', [])
    
    # Collect all items
    all_items = []
    
    # If single seed URL provided, use it
    if seed_url:
        seed_config = {
            'url': seed_url,
            'keywords': keywords.split(',') if keywords else global_keywords,
            'max_depth': max_depth or 2,
            'max_pages': max_pages or 100,
        }
        click.echo(f"Crawling seed URL: {seed_url}")
        items = crawl_seed_url(seed_config, global_keywords)
        all_items.extend(items)
    else:
        # Use seed URLs from config
        seed_urls = config_data.get('seed_urls', [])
        if not seed_urls:
            click.echo("No seed URLs found in config. Use --seed-url to specify one.", err=True)
            return
        
        for seed_config in seed_urls:
            seed_name = seed_config.get('name', seed_config.get('url', 'Unknown'))
            click.echo(f"Crawling: {seed_name}")
            
            items = crawl_seed_url(seed_config, global_keywords)
            all_items.extend(items)
            
            if len(all_items) >= max_records:
                break
    
    # Limit to max_records
    all_items = all_items[:max_records]
    
    # Save to file
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in all_items:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    click.echo(f"\nCrawl completed!")
    click.echo(f"Total pages crawled: {len(all_items)}")
    click.echo(f"Results saved to: {output}")
    
    # Show summary
    if all_items:
        click.echo("\nSample results:")
        for i, item in enumerate(all_items[:5], 1):
            title = item.get('title', 'No title')[:60]
            url = item.get('source_url', '')[:60]
            emails = len(item.get('emails', []))
            click.echo(f"  {i}. {title}...")
            click.echo(f"     URL: {url}...")
            click.echo(f"     Emails found: {emails}")

