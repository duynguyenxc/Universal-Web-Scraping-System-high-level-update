"""CLI command for Crossref discovery."""

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
from ...sources.crossref import discover_crossref

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def register(sub) -> None:
    """Register the crossref-discover command."""
    p = sub.add_parser(
        "crossref-discover",
        help="Discover papers from Crossref via REST API",
    )
    p.add_argument("--config", default=str(Path("config") / "config.yaml"))
    p.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
    p.add_argument("--max", type=int, default=None, help="Maximum number of records to discover")
    p.add_argument(
        "--throttle",
        type=float,
        default=1.0,
        help="Delay between requests (seconds). Crossref recommends 1.0+ for polite use.",
    )
    p.add_argument(
        "--year",
        type=int,
        default=None,
        help="Filter by publication year (e.g., 2020)",
    )
    p.add_argument(
        "--contact-email",
        default=None,
        help="Contact email (recommended for polite use). Can also be set in config.yaml as 'contact_email'",
    )
    p.add_argument(
        "--metrics-out",
        default=None,
        help="Optional JSON file to write harvest metrics",
    )
    p.add_argument("--db-url", default=os.getenv("UWSS_DB_URL"))

    def _cmd(args: argparse.Namespace) -> int:
        """Execute Crossref discovery command."""
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
            console.print("[red]No keywords found in config. Please set 'domain_keywords' in config.yaml[/red]")
            return 1

        # Get contact email (recommended for polite use)
        contact_email = args.contact_email or config_data.get("contact_email")

        # Get database engine
        if args.db_url:
            engine, SessionLocal = create_engine_from_url(args.db_url)
        else:
            engine, SessionLocal = create_sqlite_engine(Path(args.db))

        Base.metadata.create_all(engine)
        session = SessionLocal()

        try:
            # Discover Crossref records
            start_time = time.time()
            inserted = 0
            failed = 0
            duplicates = 0

            console.print(f"[cyan]Starting Crossref discovery with {len(keywords)} keywords...[/cyan]")
            if contact_email:
                console.print(f"[cyan]Contact email: {contact_email}[/cyan]")

            for metadata in discover_crossref(
                keywords=keywords,
                max_records=args.max,
                contact_email=contact_email,
                throttle_sec=args.throttle,
                year_filter=args.year,
            ):
                try:
                    # Check for duplicates (by DOI first, then source_url)
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
                    
                    if existing:
                        logger.debug(f"Skipping duplicate: {metadata.get('title', 'N/A')[:50]}")
                        duplicates += 1
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
                "source": "crossref",
                "inserted": inserted,
                "duplicates": duplicates,
                "failed": failed,
                "elapsed_sec": round(elapsed_sec, 2),
                "throttle_sec": args.throttle,
                "keywords_count": len(keywords),
            }

            console.print(
                f"[green]Crossref Discovery: inserted={inserted} duplicates={duplicates} failed={failed} elapsed={elapsed_sec:.1f}s[/green]"
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

        finally:
            session.close()

    p.set_defaults(func=_cmd)

