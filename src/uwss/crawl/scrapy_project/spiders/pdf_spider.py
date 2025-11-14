"""Spider for discovering and extracting scattered PDFs from web pages.

Focuses on finding PDF documents linked from HTML pages and extracting their metadata.
"""

import scrapy
from urllib.parse import urljoin, urlparse
import re
import json
from datetime import datetime
from sqlalchemy import select
from src.uwss.store import create_sqlite_engine, Document, Base
from src.uwss.store.models import VisitedUrl
from src.uwss.crawl.extractors import extract_metadata


class PDFSpider(scrapy.Spider):
    """Spider for discovering PDFs from web pages."""
    
    name = "pdf_spider"
    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 1.5,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
    }
    
    # Academic domain patterns
    ACADEMIC_DOMAINS = [
        r'\.edu$',
        r'\.ac\.[a-z]{2,}$',
        r'\.gov$',
        r'\.org$',
    ]
    
    def __init__(
        self,
        start_urls=None,
        db_path="data/uwss.sqlite",
        max_pages: int = 100,
        max_depth: int = 2,
        keywords: str | None = None,
        allowed_domains_extra: str | None = None,
        path_blocklist: str | None = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.start_urls = start_urls.split(",") if isinstance(start_urls, str) else (start_urls or [])
        self.db_path = db_path
        self.max_pages = int(max_pages)
        self.max_depth = int(max_depth)
        self.pages_crawled = 0
        self.pdfs_found = 0
        self.keyword_patterns = []
        if keywords:
            for kw in [k.strip() for k in keywords.split(",") if k.strip()]:
                self.keyword_patterns.append(re.compile(re.escape(kw), re.IGNORECASE))
        
        engine, self.SessionLocal = create_sqlite_engine(self.db_path)
        Base.metadata.create_all(engine)
        
        # Restrict to seed domains
        self.allowed_domains = [urlparse(u).netloc for u in self.start_urls if u]
        # Extra whitelist domains
        self.allowed_domains_extra = []
        if allowed_domains_extra:
            self.allowed_domains_extra = [d.strip().lower() for d in allowed_domains_extra.split(",") if d.strip()]
        # Path blacklist
        self.path_blocklist = []
        if path_blocklist:
            self.path_blocklist = [p.strip().lower() for p in path_blocklist.split(",") if p.strip()]
    
    def _is_academic_domain(self, domain: str) -> bool:
        """Check if domain is academic."""
        domain_lower = domain.lower()
        for pattern in self.ACADEMIC_DOMAINS:
            if re.search(pattern, domain_lower):
                return True
        return False
    
    def _is_pdf_url(self, url: str) -> bool:
        """Check if URL points to a PDF."""
        url_lower = url.lower()
        return url_lower.endswith('.pdf') or 'application/pdf' in url_lower
    
    def parse(self, response):
        """Parse response and extract PDFs."""
        # Limit total pages
        if self.pages_crawled >= self.max_pages:
            return
        self.pages_crawled += 1
        
        # Check depth
        depth = response.meta.get('depth', 0)
        if depth > self.max_depth:
            return
        
        url = response.url
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # If this is a PDF, extract metadata
        if self._is_pdf_url(url):
            self._process_pdf(response, url)
            return
        
        # Otherwise, extract PDF links from HTML
        session = self.SessionLocal()
        try:
            # Skip if visited
            vu = session.get(VisitedUrl, url)
            if vu:
                return
            
            # Extract all PDF links from page
            pdf_links = []
            for href in response.css('a::attr(href)').getall():
                if not href:
                    continue
                full_url = urljoin(response.url, href)
                if self._is_pdf_url(full_url):
                    pdf_links.append(full_url)
            
            # Also check meta tags
            pdf_meta = response.xpath('//meta[@name="citation_pdf_url"]/@content').get()
            if pdf_meta:
                pdf_links.append(urljoin(response.url, pdf_meta))
            
            # Process each PDF link
            for pdf_url in pdf_links:
                # Check if already exists
                exists = session.query(Document).filter(Document.pdf_url == pdf_url).first()
                if exists:
                    continue
                
                # Create document for PDF
                # Extract metadata from parent page
                html_content = response.text
                metadata = extract_metadata(html_content, url)
                
                # Use parent page title or PDF filename
                title = metadata.get("title") or response.css("title::text").get()
                if not title:
                    # Extract from PDF URL
                    pdf_path = urlparse(pdf_url).path
                    title = pdf_path.split('/')[-1].replace('.pdf', '').replace('_', ' ').replace('-', ' ')
                
                # Keyword filter
                is_relevant = True
                if self.keyword_patterns:
                    full_text = (title or "") + "\n" + (metadata.get("abstract") or "")
                    is_relevant = any(p.search(full_text) for p in self.keyword_patterns)
                
                if not is_relevant:
                    continue
                
                # Create document
                authors_json = json.dumps(metadata.get("authors", [])) if metadata.get("authors") else None
                affiliations_json = json.dumps(metadata.get("affiliations", [])) if metadata.get("affiliations") else None
                
                doc = Document(
                    source_url=pdf_url,
                    landing_url=url,  # Parent page
                    pdf_url=pdf_url,
                    status="metadata_only",
                    source="scrapy_pdf",
                    title=title,
                    abstract=metadata.get("abstract"),
                    authors=authors_json,
                    affiliations=affiliations_json,
                    doi=metadata.get("doi"),
                    year=metadata.get("year"),
                    venue=metadata.get("venue"),
                    oa_status="fulltext_pdf",
                )
                session.add(doc)
                self.pdfs_found += 1
            
            session.commit()
            
            # Mark visited
            now = datetime.utcnow()
            vu = VisitedUrl(url=url, first_seen=now, last_seen=now, status="ok")
            session.merge(vu)
            session.commit()
        finally:
            session.close()
        
        # Follow links (prioritize pages that might have PDFs)
        links_found = []
        for href in response.css("a::attr(href)").getall():
            if not href or href.startswith(("javascript:", "mailto:", "#")):
                continue
            
            next_url = urljoin(response.url, href)
            parsed_next = urlparse(next_url)
            
            if parsed_next.scheme not in ("http", "https"):
                continue
            
            # Check domain
            domain_ok = (
                parsed_next.netloc in self.allowed_domains or
                parsed_next.netloc.lower() in self.allowed_domains_extra
            )
            if not domain_ok:
                continue
            
            # Blocklist
            path_l = (parsed_next.path or "").lower()
            if any(b in path_l for b in self.path_blocklist):
                continue
            
            # Prioritize academic domains and PDF-related paths
            is_academic = self._is_academic_domain(parsed_next.netloc)
            is_pdf_related = any(word in path_l for word in ['pdf', 'paper', 'publication', 'publications', 'research'])
            priority = 1.0 if is_academic else 0.5
            if is_pdf_related:
                priority += 0.3
            
            links_found.append((next_url, priority))
        
        # Sort by priority
        links_found.sort(key=lambda x: x[1], reverse=True)
        
        # Follow top links
        for next_url, _ in links_found[:15]:  # Limit to 15 links per page
            yield scrapy.Request(
                next_url,
                callback=self.parse,
                meta={'depth': depth + 1}
            )
    
    def _process_pdf(self, response, url: str):
        """Process a PDF response directly."""
        session = self.SessionLocal()
        try:
            # Check if exists
            exists = session.query(Document).filter(Document.pdf_url == url).first()
            if exists:
                return
            
            # Extract filename for title
            pdf_path = urlparse(url).path
            title = pdf_path.split('/')[-1].replace('.pdf', '').replace('_', ' ').replace('-', ' ')
            
            # Create document
            doc = Document(
                source_url=url,
                landing_url=url,
                pdf_url=url,
                status="metadata_only",
                source="scrapy_pdf",
                title=title,
                oa_status="fulltext_pdf",
            )
            session.add(doc)
            self.pdfs_found += 1
            session.commit()
        finally:
            session.close()


