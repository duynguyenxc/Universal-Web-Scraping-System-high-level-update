"""CLI command for TRID sitemap discovery."""

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
from ...sources.trid import discover_trid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def register(sub) -> None:
    """Register the trid-discover-sitemap command."""
    p = sub.add_parser(
        "trid-discover-sitemap",
        help="Discover TRID records via sitemap crawling",
    )
    p.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
    p.add_argument("--max", type=int, default=None, help="Maximum number of records to discover")
    p.add_argument(
        "--throttle",
        type=float,
        default=2.0,
        help="Delay between requests (seconds)",
    )
    p.add_argument(
        "--no-robots-check",
        action="store_true",
        help="Skip robots.txt check (not recommended)",
    )
    p.add_argument(
        "--metrics-out",
        default=None,
        help="Optional JSON file to write harvest metrics",
    )
    p.add_argument("--db-url", default=os.getenv("UWSS_DB_URL"))

    def _cmd(args: argparse.Namespace) -> int:
        """Execute TRID discovery command."""
        from rich.console import Console

        console = Console()

        # Get database engine
        if args.db_url:
            engine, SessionLocal = create_engine_from_url(args.db_url)
        else:
            engine, SessionLocal = create_sqlite_engine(Path(args.db))

        Base.metadata.create_all(engine)
        session = SessionLocal()

        try:
            # Discover TRID records
            start_time = time.time()
            inserted = 0
            failed = 0

            console.print("[cyan]Starting TRID sitemap discovery...[/cyan]")

            for metadata in discover_trid(
                max_records=args.max,
                throttle_sec=args.throttle,
                respect_robots=not args.no_robots_check,
            ):
                try:
                    # Check if document already exists (by source_url)
                    existing = (
                        session.query(Document)
                        .filter(Document.source_url == metadata["source_url"])
                        .first()
                    )

                    if existing:
                        logger.debug(f"Skipping duplicate: {metadata['source_url']}")
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
                "source": "trid",
                "inserted": inserted,
                "failed": failed,
                "elapsed_sec": round(elapsed_sec, 2),
                "throttle_sec": args.throttle,
            }

            console.print(
                f"[green]TRID Discovery: inserted={inserted} failed={failed} elapsed={elapsed_sec:.1f}s[/green]"
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

