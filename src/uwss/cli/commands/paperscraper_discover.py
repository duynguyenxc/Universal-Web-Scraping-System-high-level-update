"""CLI command for Paperscraper discovery.

This command provides a unified interface to discover papers from multiple
sources supported by paperscraper: PubMed, arXiv, medRxiv, bioRxiv, chemRxiv.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict

from sqlalchemy.orm import Session

from ...store import Base, Document
from ...store import create_sqlite_engine, create_engine_from_url
from ...sources.paperscraper import (
    discover_paperscraper_pubmed,
    discover_paperscraper_arxiv,
    discover_paperscraper_medrxiv,
    discover_paperscraper_biorxiv,
    discover_paperscraper_chemrxiv,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Map source names to discover functions
DISCOVER_FUNCTIONS = {
    "pubmed": discover_paperscraper_pubmed,
    "arxiv": discover_paperscraper_arxiv,
    "medrxiv": discover_paperscraper_medrxiv,
    "biorxiv": discover_paperscraper_biorxiv,
    "chemrxiv": discover_paperscraper_chemrxiv,
}


def register(sub) -> None:
    """Register the paperscraper-discover command."""
    p = sub.add_parser(
        "paperscraper-discover",
        help="Discover papers via paperscraper library (PubMed, arXiv, medRxiv, bioRxiv, chemRxiv)",
    )
    p.add_argument("--config", default=str(Path("config") / "config.yaml"))
    p.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
    p.add_argument(
        "--source",
        choices=["pubmed", "arxiv", "medrxiv", "biorxiv", "chemrxiv"],
        required=True,
        help="Source to discover from",
    )
    p.add_argument(
        "--max",
        type=int,
        default=None,
        help="Maximum number of records to discover",
    )
    p.add_argument(
        "--year",
        type=int,
        default=None,
        help="Filter by publication year (e.g., 2020). Note: Applied post-query for paperscraper.",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Number of keywords per query batch (for arXiv, default: 5). Smaller batches avoid API query length limits.",
    )
    p.add_argument(
        "--metrics-out",
        default=None,
        help="Optional JSON file to write harvest metrics",
    )
    p.add_argument("--db-url", default=os.getenv("UWSS_DB_URL"))

    def _cmd(args: argparse.Namespace) -> int:
        """Execute Paperscraper discovery command."""
        from rich.console import Console
        import yaml

        console = Console()

        # Load config
        config_path = Path(args.config)
        config_data = {}
        if config_path.exists():
            with config_path.open("r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}

        # Get keywords from config
        keywords = config_data.get("domain_keywords", [])
        if not keywords:
            console.print(
                "[red]No keywords found in config. Please set 'domain_keywords' in config.yaml[/red]"
            )
            return 1

        # Get year filter (from config or argument)
        year_filter = args.year or config_data.get("year_filter")

        # Get database engine
        if args.db_url:
            engine, SessionLocal = create_engine_from_url(args.db_url)
        else:
            engine, SessionLocal = create_sqlite_engine(Path(args.db))

        Base.metadata.create_all(engine)
        session = SessionLocal()

        try:
            # Get discover function for selected source
            discover_fn = DISCOVER_FUNCTIONS.get(args.source)
            if not discover_fn:
                console.print(f"[red]Unknown source: {args.source}[/red]")
                return 1

            # Discover papers
            start_time = time.time()
            inserted = 0
            failed = 0
            duplicates = 0

            console.print(
                f"[cyan]Starting {args.source} discovery via paperscraper with {len(keywords)} keywords...[/cyan]"
            )

            # Prepare kwargs for discover function
            discover_kwargs = {
                "keywords": keywords,
                "max_records": args.max,
                "year_filter": year_filter,
            }
            
            # Add batch_size for arXiv (and potentially other sources that support it)
            if args.source == "arxiv":
                discover_kwargs["batch_size"] = args.batch_size
            
            for metadata in discover_fn(**discover_kwargs):
                try:
                    # Check for duplicates (by DOI first, then source_url, then title)
                    existing = None
                    if metadata.get("doi"):
                        existing = (
                            session.query(Document)
                            .filter(Document.doi == metadata["doi"])
                            .first()
                        )

                    if not existing and metadata.get("source_url"):
                        existing = (
                            session.query(Document)
                            .filter(Document.source_url == metadata["source_url"])
                            .first()
                        )

                    if not existing and metadata.get("title"):
                        existing = (
                            session.query(Document)
                            .filter(Document.title == metadata["title"])
                            .first()
                        )

                    if existing:
                        logger.debug(
                            f"Skipping duplicate: {metadata.get('title', 'N/A')[:50]}"
                        )
                        duplicates += 1
                        continue

                    # Apply year filter if specified (paperscraper doesn't support it directly)
                    if year_filter and metadata.get("year"):
                        if metadata["year"] < year_filter:
                            continue

                    # Create new document
                    doc = Document(**metadata)
                    session.add(doc)
                    session.commit()
                    inserted += 1

                    if inserted % 10 == 0:
                        console.print(f"[green]Inserted {inserted} records...[/green]")

                except Exception as e:
                    logger.error(f"Failed to insert record: {e}")
                    session.rollback()
                    failed += 1
                    continue

            elapsed_sec = time.time() - start_time

            # Prepare metrics
            metrics = {
                "source": f"paperscraper_{args.source}",
                "inserted": inserted,
                "duplicates": duplicates,
                "failed": failed,
                "elapsed_sec": round(elapsed_sec, 2),
                "keywords_count": len(keywords),
                "year_filter": year_filter,
            }

            console.print(
                f"[green]Paperscraper Discovery ({args.source}): inserted={inserted} duplicates={duplicates} failed={failed} elapsed={elapsed_sec:.1f}s[/green]"
            )

            # Save metrics if requested
            if args.metrics_out:
                try:
                    Path(args.metrics_out).parent.mkdir(parents=True, exist_ok=True)
                    Path(args.metrics_out).write_text(
                        json.dumps(metrics, indent=2), encoding="utf-8"
                    )
                    console.print(f"[green]Saved metrics to {args.metrics_out}[/green]")
                except Exception as e:
                    logger.error(f"Failed to save metrics: {e}")

            return 0

        except ImportError as e:
            console.print(
                f"[red]paperscraper library not available: {e}[/red]\n"
                f"[yellow]Install with: pip install paperscraper[/yellow]"
            )
            return 1
        except Exception as e:
            logger.error(f"Error during discovery: {e}")
            console.print(f"[red]Discovery failed: {e}[/red]")
            return 1
        finally:
            session.close()

    p.set_defaults(func=_cmd)


