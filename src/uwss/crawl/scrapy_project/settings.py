BOT_NAME = "uwss_scraper"
SPIDER_MODULES = ["src.uwss.crawl.scrapy_project.spiders"]
NEWSPIDER_MODULE = "src.uwss.crawl.scrapy_project.spiders"

# Robots.txt compliance
ROBOTSTXT_OBEY = True
ROBOTSTXT_USER_AGENT = "uwss/0.1"

# Rate limiting
DOWNLOAD_DELAY = 1.0
RANDOMIZE_DOWNLOAD_DELAY = 0.5  # Random delay between 0.5 * DOWNLOAD_DELAY and 1.5 * DOWNLOAD_DELAY
CONCURRENT_REQUESTS_PER_DOMAIN = 2  # Conservative to respect crawl-delay
CONCURRENT_REQUESTS = 8

# Timeouts
DOWNLOAD_TIMEOUT = 30

# Retry
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# User-Agent
DEFAULT_REQUEST_HEADERS = {
	"User-Agent": "uwss/0.1 (Academic Research Crawler; +contact email in config)",
	"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
	"Accept-Language": "en-US,en;q=0.5",
}

# Item pipelines
ITEM_PIPELINES = {
}

# AutoThrottle (respects server response times)
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = False

# Logging
LOG_LEVEL = "INFO"
