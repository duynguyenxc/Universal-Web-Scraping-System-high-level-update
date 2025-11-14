"""Quality filtering command for high-quality data collection.

Focuses on filtering for DATA QUALITY and RELEVANCE, not just metadata.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from sqlalchemy import select
from src.uwss.store.db import create_sqlite_engine, create_engine_from_url
from src.uwss.store.models import Document
from src.uwss.quality import assess_document_quality, filter_high_quality
from rich.console import Console

console = Console()


def register(sub) -> None:
	"""Register the quality-filter command."""
	p = sub.add_parser("quality-filter", help="Filter documents by quality criteria (focus on data quality)")
	p.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
	p.add_argument("--db-url", default=None)
	p.add_argument("--min-relevance", type=float, default=0.5, help="Minimum relevance score")
	p.add_argument("--min-completeness", type=float, default=0.3, help="Minimum completeness score")
	p.add_argument("--min-overall", type=float, default=0.4, help="Minimum overall quality score")
	p.add_argument("--require-abstract", action="store_true", help="Require abstract (minimum 50 chars)")
	p.add_argument("--require-title", action="store_true", default=True, help="Require title (default: True)")
	p.add_argument("--limit", type=int, default=None, help="Limit number of results")
	p.add_argument("--out", default=None, help="Output file for filtered IDs")
	
	def _cmd(args: argparse.Namespace) -> int:
		"""Execute quality filter command."""
		if args.db_url:
			from src.uwss.store.db import create_engine_from_url
			engine, SessionLocal = create_engine_from_url(args.db_url)
		else:
			from src.uwss.store.db import create_sqlite_engine
			engine, SessionLocal = create_sqlite_engine(Path(args.db))
		
		session = SessionLocal()
		try:
			# Filter high-quality documents
			high_quality = filter_high_quality(
				session,
				min_relevance=args.min_relevance,
				min_completeness=args.min_completeness,
				min_overall=args.min_overall,
				limit=args.limit
			)
			
			# Additional filters
			filtered = []
			for doc in high_quality:
				# Require abstract if specified
				if args.require_abstract:
					if not doc.abstract or len(doc.abstract) < 50:
						continue
				
				# Require title if specified
				if args.require_title:
					if not doc.title or not doc.title.strip():
						continue
				
				filtered.append(doc)
			
			console.print(f"[green]Found {len(filtered)} high-quality documents[/green]")
			
			# Print sample
			for doc in filtered[:10]:
				quality = assess_document_quality(doc)
				console.print(f"  ID {doc.id}: {doc.title[:60]}...")
				console.print(f"    Relevance: {quality['relevance']:.2f}, Completeness: {quality['completeness']:.2f}, Overall: {quality['overall_quality']:.2f}")
			
			# Save IDs if requested
			if args.out:
				with open(args.out, 'w', encoding='utf-8') as f:
					for doc in filtered:
						f.write(f"{doc.id}\n")
				console.print(f"[green]Saved {len(filtered)} IDs to {args.out}[/green]")
			
			return 0
		finally:
			session.close()
	
	p.set_defaults(func=_cmd)


