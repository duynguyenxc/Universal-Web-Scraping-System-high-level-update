"""Spider for crawling research group websites and faculty pages.

Focuses on academic domains (.edu, .ac.*, .gov, .org) and extracts:
- Research publications
- Faculty information
- Lab/project pages
- PDF documents
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
from src.uwss.crawl.extractors.researcher_extractor import extract_researcher_info


class ResearchSpider(scrapy.Spider):
    """Spider for research groups, faculty pages, and lab websites."""
    
    name = "research_spider"
    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 2.0,  # More conservative for academic sites
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,  # Very conservative
    }
    
    # Academic domain patterns (higher priority)
    ACADEMIC_DOMAINS = [
        r'\.edu$',
        r'\.ac\.[a-z]{2,}$',  # .ac.uk, .ac.jp, etc.
        r'\.gov$',
        r'\.org$',
    ]
    
    def __init__(
        self,
        start_urls=None,
        db_path="data/uwss.sqlite",
        max_pages: int = 50,
        max_depth: int = 3,
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
        """Check if domain is academic (.edu, .ac.*, .gov, .org)."""
        domain_lower = domain.lower()
        for pattern in self.ACADEMIC_DOMAINS:
            if re.search(pattern, domain_lower):
                return True
        return False
    
    def _score_domain(self, domain: str) -> float:
        """Score domain for academic relevance (higher = better)."""
        if self._is_academic_domain(domain):
            return 1.0
        if domain.lower().endswith('.org'):
            return 0.7
        return 0.3
    
    def parse(self, response):
        """Parse response and extract metadata."""
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
        
        # Prefer academic domains
        domain_score = self._score_domain(domain)
        
        session = self.SessionLocal()
        try:
            # Skip if visited before
            vu = session.get(VisitedUrl, url)
            if vu:
                return
            
            # Check if document exists
            exists = session.query(Document).filter(Document.source_url == url).first()
            if exists:
                return
            
            # Extract metadata using enhanced extractor
            html_content = response.text
            metadata = extract_metadata(html_content, url)
            
            # Also extract researcher info (for faculty pages)
            researcher_info = extract_researcher_info(html_content, url)
            
            # Merge researcher info into metadata if available
            if researcher_info.get("name") and not metadata.get("authors"):
                metadata["authors"] = [researcher_info["name"]]
            if researcher_info.get("affiliation") and not metadata.get("affiliations"):
                metadata["affiliations"] = [researcher_info["affiliation"]]
            if researcher_info.get("research_interests") and not metadata.get("keywords"):
                metadata["keywords"] = researcher_info["research_interests"]
            
            # Use extracted title or fallback
            title = metadata.get("title") or response.css("title::text").get() or response.css("h1::text").get()
            abstract = metadata.get("abstract")
            
            # Keyword filter: require at least one keyword match if patterns provided
            is_relevant = True
            if self.keyword_patterns:
                # Skip common non-content pages
                skip_titles = {
                    "home", "about", "contact", "education", "login", "sign up",
                    "privacy", "terms", "cookie", "sitemap", "404", "error"
                }
                title_lower = (title or "").strip().lower()
                if any(skip in title_lower for skip in skip_titles):
                    return
                
                full_text = (title or "") + "\n" + (abstract or "") + "\n" + (" ".join(response.css("p::text").getall()) or "")
                is_relevant = any(p.search(full_text) for p in self.keyword_patterns)
            
            # Skip if not relevant
            if not is_relevant:
                return
            
            # Prepare document data
            authors_json = json.dumps(metadata.get("authors", [])) if metadata.get("authors") else None
            affiliations_json = json.dumps(metadata.get("affiliations", [])) if metadata.get("affiliations") else None
            keywords_json = json.dumps(metadata.get("keywords", [])) if metadata.get("keywords") else None
            
            # Determine OA status
            oa_status = "closed"
            if metadata.get("pdf_url"):
                oa_status = "fulltext_pdf"
            elif abstract:
                oa_status = "abstract_only"
            
            # Create document
            doc = Document(
                source_url=url,
                landing_url=url,
                status="metadata_only",
                source="scrapy_research",
                title=title,
                abstract=abstract,
                authors=authors_json,
                affiliations=affiliations_json,
                keywords=keywords_json,
                doi=metadata.get("doi"),
                year=metadata.get("year"),
                pdf_url=metadata.get("pdf_url"),
                venue=metadata.get("venue"),
                oa_status=oa_status,
            )
            session.add(doc)
            session.commit()
            
            # Mark visited
            now = datetime.utcnow()
            vu = VisitedUrl(url=url, first_seen=now, last_seen=now, status="ok")
            session.merge(vu)
            session.commit()
        finally:
            session.close()
        
        # Follow links (prioritize academic domains)
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
            
            # Blocklist path substrings
            path_l = (parsed_next.path or "").lower()
            if any(b in path_l for b in self.path_blocklist):
                continue
            
            # Score and prioritize academic domains
            next_domain_score = self._score_domain(parsed_next.netloc)
            links_found.append((next_url, next_domain_score))
        
        # Sort by domain score (academic first)
        links_found.sort(key=lambda x: x[1], reverse=True)
        
        # Follow links (limit to top N per page to avoid explosion)
        for next_url, _ in links_found[:20]:  # Limit to 20 links per page
            yield scrapy.Request(
                next_url,
                callback=self.parse,
                meta={'depth': depth + 1}
            )

