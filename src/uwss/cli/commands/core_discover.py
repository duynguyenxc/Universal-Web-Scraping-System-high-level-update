"""CLI command for CORE discovery."""

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
from ...sources.core import discover_core

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def register(sub) -> None:
    """Register the core-discover command."""
    p = sub.add_parser(
        "core-discover",
        help="Discover papers from CORE via OAI-PMH",
    )
    p.add_argument("--config", default=str(Path("config") / "config.yaml"))
    p.add_argument("--db", default=str(Path("data") / "uwss.sqlite"))
    p.add_argument("--max", type=int, default=None, help="Maximum number of records to discover")
    p.add_argument(
        "--from",
        dest="from_date",
        default=None,
        help="Start date (YYYY-MM-DD format)",
    )
    p.add_argument(
        "--until",
        dest="until_date",
        default=None,
        help="End date (YYYY-MM-DD format)",
    )
    p.add_argument(
        "--throttle",
        type=float,
        default=1.0,
        help="Delay between requests (seconds). CORE recommends 1.0+ for polite use.",
    )
    p.add_argument(
        "--metrics-out",
        default=None,
        help="Optional JSON file to write harvest metrics",
    )
    p.add_argument("--db-url", default=os.getenv("UWSS_DB_URL"))

    def _cmd(args: argparse.Namespace) -> int:
        """Execute CORE discovery command."""
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
            # Discover CORE records
            start_time = time.time()
            inserted = 0
            failed = 0
            duplicates = 0

            console.print("[cyan]Starting CORE discovery (OAI-PMH)...[/cyan]")

            for metadata in discover_core(
                max_records=args.max,
                from_date=getattr(args, "from_date", None),
                until_date=getattr(args, "until_date", None),
                throttle_sec=args.throttle,
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
                "source": "core",
                "inserted": inserted,
                "duplicates": duplicates,
                "failed": failed,
                "elapsed_sec": round(elapsed_sec, 2),
                "throttle_sec": args.throttle,
            }

            console.print(
                f"[green]CORE Discovery: inserted={inserted} duplicates={duplicates} failed={failed} elapsed={elapsed_sec:.1f}s[/green]"
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


