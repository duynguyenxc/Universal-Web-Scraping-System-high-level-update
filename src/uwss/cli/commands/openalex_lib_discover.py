"""CLI command for OpenAlex discovery using pyalex library."""

from __future__ import annotations

import argparse
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict

from sqlalchemy.orm import Session

from ...store import Base, Document
from ...store import create_sqlite_engine, create_engine_from_url
from ...sources.openalex_lib import discover_openalex

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def register(sub) -> None:
    """Register the openalex-lib-discover command."""
    p = sub.add_parser(
        "openalex-lib-discover",
        help="Discover papers via OpenAlex API using pyalex library",
    )
    p.add_argument("--config", default=str(Path("config") / "config.yaml"))
    p.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
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
        help="Filter by publication year (e.g., 2020)",
    )
    p.add_argument(
        "--metrics-out",
        default=None,
        help="Optional JSON file to write harvest metrics",
    )
    p.add_argument("--db-url", default=os.getenv("UWSS_DB_URL"))

    def _cmd(args: argparse.Namespace) -> int:
        """Execute OpenAlex discovery command."""
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

        # Get year filter and contact email (REQUIRED for OpenAlex)
        year_filter = args.year or config_data.get("year_filter")
        contact_email = config_data.get("contact_email")
        
        if not contact_email:
            console.print(
                "[red]contact_email is REQUIRED for OpenAlex API (per ToS). Please set 'contact_email' in config.yaml[/red]"
            )
            return 1

        # Get database engine
        if args.db_url:
            engine, SessionLocal = create_engine_from_url(args.db_url)
        else:
            engine, SessionLocal = create_sqlite_engine(Path(args.db))

        Base.metadata.create_all(engine)
        session = SessionLocal()

        try:
            # Discover papers
            start_time = time.time()
            inserted = 0
            failed = 0
            duplicates = 0

            console.print(
                f"[cyan]Starting OpenAlex discovery via pyalex with {len(keywords)} keywords...[/cyan]"
            )

            for metadata in discover_openalex(
                keywords=keywords,
                max_records=args.max,
                year_filter=year_filter,
                contact_email=contact_email,
            ):
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

                    # Create new document
                    doc = Document(**metadata)
                    session.add(doc)
                    inserted += 1

                    if inserted % 10 == 0:
                        session.commit()
                        console.print(f"[green]Inserted {inserted} records...[/green]")

                except Exception as e:
                    logger.error(f"Error inserting record: {e}")
                    failed += 1
                    session.rollback()

            session.commit()
            elapsed = time.time() - start_time

            console.print(
                f"[green]OpenAlex Discovery: inserted={inserted} duplicates={duplicates} failed={failed} elapsed={elapsed:.1f}s[/green]"
            )

            # Write metrics if requested
            if args.metrics_out:
                metrics: Dict[str, Any] = {
                    "source": "openalex",
                    "inserted": inserted,
                    "duplicates": duplicates,
                    "failed": failed,
                    "elapsed_sec": elapsed,
                }
                import json

                Path(args.metrics_out).write_text(json.dumps(metrics, indent=2))

            return 0

        except Exception as e:
            console.print(f"[red]Error during discovery: {e}[/red]")
            logger.exception(e)
            return 1
        finally:
            session.close()

    p.set_defaults(func=_cmd)

