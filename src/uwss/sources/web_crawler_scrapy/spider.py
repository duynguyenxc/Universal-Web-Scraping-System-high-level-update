"""Scrapy spider for crawling research group websites."""

import logging
import re
from typing import Set, List, Dict, Any
from urllib.parse import urljoin, urlparse

import scrapy
from scrapy.http import Response
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

logger = logging.getLogger(__name__)


class ResearchGroupSpider(CrawlSpider):
    """Spider to crawl research group websites and extract relevant content."""
    
    name = 'research_group'
    custom_settings = {
        'ROBOTSTXT_OBEY': True,
        'DOWNLOAD_DELAY': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 1,
        'AUTOTHROTTLE_MAX_DELAY': 10,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 2.0,
    }
    
    def __init__(
        self,
        seed_url: str,
        allowed_domains: List[str] = None,
        keywords: List[str] = None,
        max_depth: int = 2,
        max_pages: int = 100,
        *args,
        **kwargs
    ):
        """Initialize spider with crawl configuration.
        
        Args:
            seed_url: Starting URL (research group homepage)
            allowed_domains: List of allowed domains to crawl
            keywords: Keywords to filter relevant content
            max_depth: Maximum crawl depth from seed URL
            max_pages: Maximum number of pages to crawl
        """
        super().__init__(*args, **kwargs)
        
        self.start_urls = [seed_url]
        self.allowed_domains = allowed_domains or []
        # Original keyword phrases (may be long phrases from config.yaml)
        self.keywords = [k.lower() for k in (keywords or [])]

        # Derive token-level keywords to make matching easier and more robust.
        # Example: "reinforced concrete corrosion experiment" ->
        # tokens: ["reinforced", "concrete", "corrosion", "experiment"]
        stopwords = {
            "and", "or", "of", "the", "in", "on", "for", "to", "with",
            "a", "an", "by", "at", "from", "over", "under", "into",
            "long", "term", "test", "experiment", "monitoring", "measurement",
        }
        self.keyword_tokens = set()
        for phrase in self.keywords:
            # Extract alphabetic tokens
            for token in re.findall(r"[a-zA-Z]+", phrase):
                t = token.lower()
                if len(t) > 2 and t not in stopwords:
                    self.keyword_tokens.add(t)
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.pages_crawled = 0
        self.visited_urls: Set[str] = set()
        
        # Extract domain from seed URL if not provided
        if not self.allowed_domains:
            parsed = urlparse(seed_url)
            domain = parsed.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            self.allowed_domains = [domain]
        
        # Setup link extractor
        self.link_extractor = LinkExtractor(
            allow_domains=self.allowed_domains,
            deny_extensions=['pdf', 'zip', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'],
            unique=True,
        )
        
        logger.info(f"Initialized spider: seed={seed_url}, domains={self.allowed_domains}, "
                   f"keywords={len(self.keywords)}, max_depth={max_depth}, max_pages={max_pages}")
    
    def parse_start_url(self, response: Response):
        """Parse the seed URL."""
        return self.parse_page(response, depth=0)
    
    def parse_page(self, response: Response, depth: int = 0):
        """Parse a page and extract content if relevant."""
        self.pages_crawled += 1
        url = response.url
        self.visited_urls.add(url)
        
        # Check if we've exceeded max pages
        if self.pages_crawled > self.max_pages:
            logger.info(f"Reached max_pages limit ({self.max_pages}), stopping crawl")
            return
        
        # Check depth
        if depth > self.max_depth:
            logger.debug(f"Max depth reached for {url}")
            return

        # Extract text content for relevance check
        text_content = self._extract_text(response)
        
        # Check relevance
        is_relevant = self._check_relevance(text_content)
        
        if is_relevant:
            logger.info(f"Relevant page found: {url} (depth={depth})")
            
            # Extract metadata
            item = {
                'source_url': url,
                'title': self._extract_title(response),
                'abstract': self._extract_abstract(response, text_content),
                'year': self._extract_year(response, text_content),
                'authors': self._extract_authors(response, text_content),
                'group': self._extract_group(response, text_content),
                'emails': self._extract_emails(text_content),
                # Keep raw HTML for downstream researcher extraction;
                # pipelines are responsible for dropping this field from final output.
                'raw_html': response.text,
                'content': text_content[:50000],  # Limit content size
                'depth': depth,
                'topic': 'web-crawl',
                'status': 'not_fetched',
            }
            
            yield item
        
        # Follow links
        if depth < self.max_depth:
            links = self.link_extractor.extract_links(response)
            for link in links:
                if link.url not in self.visited_urls:
                    yield response.follow(
                        link.url,
                        callback=self.parse_page,
                        cb_kwargs={'depth': depth + 1},
                        errback=self._handle_error
                    )
    
    def _extract_text(self, response: Response) -> str:
        """Extract clean main-text content from response.

        We first try `trafilatura` to remove navigation/boilerplate and get the
        main article content. If that fails for any reason, we fall back to a
        simpler CSS-based text extraction.
        """
        html = response.text
        text = ""
        try:
            # Lazy import so that other parts of the system do not require
            # trafilatura unless the crawler is used.
            import trafilatura

            extracted = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=False,
                no_fallback=True,
            )
            if extracted:
                text = extracted
        except Exception:
            # Fallback to previous simple behaviour
            text = " ".join(response.css("body *::text").getall())

        # Clean up whitespace
        text = " ".join(text.split())
        return text.lower()
    
    def _check_relevance(self, text: str) -> bool:
        """Check if text contains relevant keywords."""
        # If no keywords configured, accept all pages
        if not self.keywords and not self.keyword_tokens:
            return True

        text_lower = text.lower()

        # 1) Phrase-level matches (for short phrases / single words)
        phrase_matches = 0
        if self.keywords:
            phrase_matches = sum(1 for keyword in self.keywords if keyword and keyword in text_lower)

        # 2) Token-level matches (for long phrases from config.yaml)
        token_matches = 0
        tokens = self.keyword_tokens
        if tokens:
            token_matches = sum(1 for t in tokens if t in text_lower)

        # Decide relevance:
        # - If at least 1 phrase matches -> relevant
        # - OR if enough individual tokens match
        #   (require at least 2 tokens or 20% of tokens, whichever is larger)
        token_threshold = 0
        if tokens:
            token_threshold = max(2, int(len(tokens) * 0.2))

        is_relevant = False
        if phrase_matches >= 1:
            is_relevant = True
        elif tokens and token_matches >= token_threshold:
            is_relevant = True

        if is_relevant:
            logger.debug(
                f"Relevant page: phrase_matches={phrase_matches}, "
                f"token_matches={token_matches}/{len(tokens) if tokens else 0}"
            )

        return is_relevant
    
    def _extract_title(self, response: Response) -> str:
        """Extract title from page."""
        # Try multiple sources
        title = (
            response.css('title::text').get() or
            response.css('h1::text').get() or
            response.css('meta[property="og:title"]::attr(content)').get() or
            response.css('meta[name="citation_title"]::attr(content)').get() or
            ''
        )
        return title.strip()
    
    def _extract_abstract(self, response: Response, text: str) -> str:
        """Extract abstract or summary from page."""
        # Try meta tags first
        abstract = (
            response.css('meta[name="description"]::attr(content)').get() or
            response.css('meta[property="og:description"]::attr(content)').get() or
            response.css('meta[name="citation_abstract"]::attr(content)').get() or
            ''
        )
        
        if abstract:
            return abstract.strip()
        
        # Try to find abstract section
        abstract_sections = response.css(
            'section.abstract, div.abstract, p.abstract, '
            '[class*="abstract"], [id*="abstract"]'
        )
        if abstract_sections:
            abstract_text = ' '.join(abstract_sections.css('*::text').getall())
            if len(abstract_text) > 50:
                return abstract_text.strip()[:1000]
        
        # Fallback: first paragraph or first 500 chars
        first_para = response.css('p::text').get()
        if first_para and len(first_para) > 50:
            return first_para.strip()[:1000]
        
        return text[:500].strip() if text else ''
    
    def _extract_year(self, response: Response, text: str) -> int:
        """Extract year from page."""
        # Try meta tags
        year_str = (
            response.css('meta[name="citation_publication_date"]::attr(content)').get() or
            response.css('meta[property="article:published_time"]::attr(content)').get() or
            ''
        )
        
        if year_str:
            # Extract year from date string
            year_match = re.search(r'(\d{4})', year_str)
            if year_match:
                year = int(year_match.group(1))
                if 1990 <= year <= 2025:
                    return year
        
        # Try to find year in text (20xx pattern)
        year_matches = re.findall(r'\b(19\d{2}|20[0-2]\d)\b', text)
        if year_matches:
            years = [int(y) for y in year_matches if 1990 <= int(y) <= 2025]
            if years:
                return max(years)  # Return most recent year
        
        return None
    
    def _extract_authors(self, response: Response, text: str) -> List[str]:
        """Extract authors from page."""
        authors = []
        
        # Try meta tags
        meta_authors = response.css('meta[name="citation_author"]::attr(content)').getall()
        if meta_authors:
            authors.extend([a.strip() for a in meta_authors])
        
        # Try to find author sections
        author_sections = response.css(
            '[class*="author"], [id*="author"], '
            '[class*="people"], [id*="people"], '
            '[class*="team"], [id*="team"]'
        )
        
        for section in author_sections:
            # Look for names (capitalized words pattern)
            names = section.css('h3, h4, strong, .name, .author-name').css('::text').getall()
            authors.extend([n.strip() for n in names if len(n.strip()) > 2])
        
        # Remove duplicates and clean
        authors = list(dict.fromkeys(authors))  # Preserve order, remove dupes
        return [a for a in authors if len(a) > 2][:20]  # Limit to 20 authors
    
    def _extract_group(self, response: Response, text: str) -> str:
        """Extract research group name."""
        # Try meta tags
        group = (
            response.css('meta[name="citation_author_institution"]::attr(content)').get() or
            response.css('meta[property="og:site_name"]::attr(content)').get() or
            ''
        )
        
        if group:
            return group.strip()
        
        # Try to find group name in headings
        group_headings = response.css('h1, h2, .group-name, .lab-name, .research-group').css('::text').getall()
        for heading in group_headings:
            heading_lower = heading.lower()
            if any(kw in heading_lower for kw in ['lab', 'group', 'research', 'center', 'institute']):
                return heading.strip()
        
        return ''
    
    def _extract_emails(self, text: str) -> List[str]:
        """Extract email addresses from text."""
        # Email regex pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        # Filter out common non-personal emails
        filtered = []
        for email in emails:
            email_lower = email.lower()
            if not any(skip in email_lower for skip in ['noreply', 'no-reply', 'donotreply', 'example.com']):
                filtered.append(email)
        
        # Remove duplicates
        return list(dict.fromkeys(filtered))
    
    def _handle_error(self, failure):
        """Handle request errors."""
        logger.warning(f"Request failed: {failure.request.url} - {failure.value}")

