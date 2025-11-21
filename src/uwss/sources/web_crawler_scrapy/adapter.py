"""Adapter to integrate Scrapy web crawler with UWSS database."""

import logging
from typing import Iterator, Dict, Any, List
from pathlib import Path
from scrapy import signals

logger = logging.getLogger(__name__)

# Global item collector (for Scrapy pipeline)
_items_collected = []


class CollectingPipeline:
    """Pipeline to collect items in memory and to temp file."""
    def __init__(self):
        import tempfile
        import json
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl', encoding='utf-8')
        self.temp_file_path = self.temp_file.name
        self.item_count = 0
    
    def process_item(self, item, spider):
        import json
        item_dict = dict(item)
        # Write to temp file
        self.temp_file.write(json.dumps(item_dict, ensure_ascii=False) + '\n')
        self.temp_file.flush()
        self.item_count += 1
        # Also add to global for backward compatibility
        global _items_collected
        _items_collected.append(item_dict)
        logger.debug(f"Pipeline collected item {self.item_count}: {item_dict.get('title', 'No title')[:50]}")
        return item
    
    def close_spider(self, spider):
        if hasattr(self, 'temp_file'):
            self.temp_file.close()
        logger.info(f"Pipeline closed. Collected {self.item_count} items to {self.temp_file_path}")


class ItemCollectorExtension:
    """Scrapy extension to collect items via signals."""
    def __init__(self):
        self.items = []
    
    @classmethod
    def from_crawler(cls, crawler):
        ext = cls()
        crawler.signals.connect(ext.item_scraped, signal=signals.item_scraped)
        return ext
    
    def item_scraped(self, item, response, spider):
        item_dict = dict(item)
        self.items.append(item_dict)
        global _items_collected
        _items_collected.append(item_dict)
        logger.debug(f"Extension collected item: {item_dict.get('title', 'No title')[:50]}")


def discover_web_crawler_scrapy(
    seed_url: str,
    keywords: List[str] = None,
    allowed_domains: List[str] = None,
    max_depth: int = 2,
    max_pages: int = 100,
    config_file: str = None
) -> Iterator[Dict[str, Any]]:
    """Discover documents from research group websites using Scrapy.
    
    Args:
        seed_url: Starting URL (research group homepage)
        keywords: Keywords to filter relevant content
        allowed_domains: List of allowed domains to crawl
        max_depth: Maximum crawl depth from seed URL
        max_pages: Maximum number of pages to crawl
        config_file: Optional path to config file
    
    Yields:
        Document dictionaries with metadata
    """
    global _items_collected
    _items_collected = []  # Reset for each crawl
    
    from .spider import ResearchGroupSpider
    from scrapy.crawler import CrawlerRunner
    from twisted.internet import reactor, defer
    from twisted.internet.task import deferLater
    
    # Setup Scrapy settings
    #
    # IMPORTANT for this project:
    # - We keep the crawl very conservative so that:
    #   * Small tests finish quickly (even if the seed site is slow or irrelevant)
    #   * We never run an unbounded crawl when keywords do not match anything
    # - Limits are enforced in TWO layers:
    #   * Inside the spider via max_pages / max_depth
    #   * At the engine level via CLOSESPIDER_* and DOWNLOAD_TIMEOUT
    settings = {
        # Politeness / robots
        'ROBOTSTXT_OBEY': True,
        # Keep a small delay, but not too large, so tiny debug runs (3–5 pages)
        # finish quickly even on slow sites.
        'DOWNLOAD_DELAY': 0.5,
        'RANDOMIZE_DOWNLOAD_DELAY': 0.25,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        # For our small, supervised crawls we disable autotrottle; the explicit
        # delay + strict limits below are enough and keep behaviour predictable.
        'AUTOTHROTTLE_ENABLED': False,
        # Hard safety limits so the crawl cannot run "forever"
        #
        # Abort the crawl once Scrapy has scheduled roughly this many pages,
        # even if something goes wrong in the spider logic.
        'CLOSESPIDER_PAGECOUNT': max_pages,
        # Global wall‑clock timeout for the whole crawl (in seconds).
        # Make this small so that a quick test (3 pages) never runs for minutes.
        'CLOSESPIDER_TIMEOUT': 20,
        # Per‑request timeout (seconds). If a server is very slow or hangs,
        # we will give up on that request instead of waiting too long.
        'DOWNLOAD_TIMEOUT': 10,
        # Pipelines and extensions
        # NOTE: dùng đường dẫn đầy đủ theo package thực tế `src.uwss.*` để
        # Scrapy không còn báo lỗi "No module named 'uwss'" sau khi crawl xong.
        'ITEM_PIPELINES': {
            'src.uwss.sources.web_crawler_scrapy.pipeline.MetadataExtractionPipeline': 300,
            'src.uwss.sources.web_crawler_scrapy.pipeline.EmailExtractionPipeline': 400,
            'src.uwss.sources.web_crawler_scrapy.pipeline.UWSSDocumentPipeline': 500,
            'src.uwss.sources.web_crawler_scrapy.adapter.CollectingPipeline': 600,
        },
        'EXTENSIONS': {
            'src.uwss.sources.web_crawler_scrapy.adapter.ItemCollectorExtension': 500,
        },
        'LOG_LEVEL': 'INFO',
    }
    
    # Create crawler runner
    runner = CrawlerRunner(settings)

    # Derive a hard wall‑clock timeout for this crawl.
    # Heuristic: at most ~5s cho mỗi trang + trần trên tuyệt đối 60s.
    timeout_sec = min(max_pages * 5, 60)

    # Create deferred for crawling
    @defer.inlineCallbacks
    def crawl():
        try:
            # Schedule a hard stop on the reactor as a safety net.
            # Nếu vì lý do gì đó Scrapy không đóng spider đúng cách,
            # reactor.stop() này sẽ đảm bảo toàn bộ job kết thúc.
            reactor.callLater(timeout_sec, reactor.stop)

            yield runner.crawl(
                ResearchGroupSpider,
                seed_url=seed_url,
                allowed_domains=allowed_domains or [],
                keywords=keywords or [],
                max_depth=max_depth,
                max_pages=max_pages,
            )
        finally:
            # Safe to call nhiều lần; Twisted sẽ bỏ qua nếu reactor đã dừng.
            if reactor.running:
                reactor.stop()
    
    # Check if reactor is already running
    if not reactor.running:
        # Start crawling
        crawl()
        reactor.run()
    else:
        # If reactor is already running, use CrawlerProcess instead
        from scrapy.crawler import CrawlerProcess
        process = CrawlerProcess(settings)
        process.crawl(
            ResearchGroupSpider,
            seed_url=seed_url,
            allowed_domains=allowed_domains or [],
            keywords=keywords or [],
            max_depth=max_depth,
            max_pages=max_pages,
        )
        process.start()
    
    # Try to read from temp file if pipeline created one
    import json
    import os
    import tempfile
    import glob
    
    # Look for temp files in system temp directory
    temp_dir = tempfile.gettempdir()
    temp_files = glob.glob(os.path.join(temp_dir, 'tmp*.jsonl'))
    
    if temp_files:
        # Sort by modification time, get most recent
        temp_files.sort(key=os.path.getmtime, reverse=True)
        temp_file_path = temp_files[0]
        try:
            logger.info(f"Reading items from temp file: {temp_file_path}")
            with open(temp_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        _items_collected.append(item)
            os.remove(temp_file_path)  # Clean up
            logger.info(f"Read {len(_items_collected)} items from temp file")
        except Exception as e:
            logger.warning(f"Could not read temp file {temp_file_path}: {e}")
    
    # Yield collected items
    logger.info(f"Collected {len(_items_collected)} items")
    for item in _items_collected:
        yield item

