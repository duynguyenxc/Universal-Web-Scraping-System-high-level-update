import scrapy
from urllib.parse import urljoin, urlparse
import re
import json
from sqlalchemy import select
from src.uwss.store import create_sqlite_engine, Document, Base
from src.uwss.store.models import VisitedUrl
from src.uwss.crawl.extractors import extract_metadata


class SeedSpider(scrapy.Spider):
	name = "seed_spider"
	custom_settings = {
		"ROBOTSTXT_OBEY": True,
	}

	def __init__(self, start_urls=None, db_path="data/uwss.sqlite", max_pages: int = 10, keywords: str|None = None, allowed_domains_extra: str|None = None, path_blocklist: str|None = None, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.start_urls = start_urls.split(",") if isinstance(start_urls, str) else (start_urls or [])
		self.db_path = db_path
		self.max_pages = int(max_pages)
		self.pages_crawled = 0
		self.keyword_patterns = []
		if keywords:
			for kw in [k.strip() for k in keywords.split(",") if k.strip()]:
				self.keyword_patterns.append(re.compile(re.escape(kw), re.IGNORECASE))
		engine, self.SessionLocal = create_sqlite_engine(self.db_path)
		Base.metadata.create_all(engine)
		# Restrict to seed domains
		self.allowed_domains = [urlparse(u).netloc for u in self.start_urls if u]
		# Extra whitelist domains (comma-separated)
		self.allowed_domains_extra = []
		if allowed_domains_extra:
			self.allowed_domains_extra = [d.strip().lower() for d in allowed_domains_extra.split(",") if d.strip()]
		# Path blacklist (substring match)
		self.path_blocklist = []
		if path_blocklist:
			self.path_blocklist = [p.strip().lower() for p in path_blocklist.split(",") if p.strip()]

	def parse(self, response):
		# Limit total pages
		if self.pages_crawled >= self.max_pages:
			return
		self.pages_crawled += 1

		# Save the landing page as a candidate if keyword-relevant; extract basic HTML metadata
		session = self.SessionLocal()
		try:
			url = response.url
			# Skip if visited before
			vu = session.get(VisitedUrl, url)
			if vu:
				return
			exists = session.query(Document).filter(Document.source_url == url).first()
			if exists:
				return
			
			# Extract metadata using enhanced extractor
			html_content = response.text
			metadata = extract_metadata(html_content, url)
			
			# Use extracted title or fallback
			title = metadata.get("title") or response.css("title::text").get() or response.css("h1::text").get()
			abstract = metadata.get("abstract")
			
			# keyword filter: require at least one keyword match in title/body if patterns provided
			is_relevant = True
			if self.keyword_patterns:
				# Skip common non-content pages
				skip_titles = {"education", "aci university", "cooperating organizations"}
				if (title or "").strip().lower() in skip_titles:
					return
				full_text = (title or "") + "\n" + (abstract or "") + "\n" + (" ".join(response.css("p::text").getall()) or "")
				is_relevant = any(p.search(full_text) for p in self.keyword_patterns)
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
			
			doc = Document(
				source_url=url,
				landing_url=url,
				status="metadata_only",
				source="scrapy",
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
			from datetime import datetime
			now = datetime.utcnow()
			vu = VisitedUrl(url=url, first_seen=now, last_seen=now, status="ok")
			session.merge(vu)
			session.commit()
		finally:
			session.close()

		# Extract next links (only same domain, http/https)
		for href in response.css("a::attr(href)").getall():
			if not href or href.startswith("javascript:") or href.startswith("mailto:"):
				continue
			next_url = urljoin(response.url, href)
			parsed = urlparse(next_url)
			if parsed.scheme not in ("http", "https"):
				continue
			domain_ok = (parsed.netloc in self.allowed_domains) or (parsed.netloc.lower() in self.allowed_domains_extra)
			if not domain_ok:
				continue
			# Blocklist path substrings
			path_l = (parsed.path or "").lower()
			if any(b in path_l for b in self.path_blocklist):
				continue
			yield scrapy.Request(next_url, callback=self.parse)
