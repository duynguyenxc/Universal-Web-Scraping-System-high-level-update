from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console


console = Console()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="llm-kg",
        description="LLM Knowledge Graph subproject (works on top of UWSS outputs).",
    )
    sub = p.add_subparsers(dest="command")

    p.add_argument(
        "--config",
        default=str(Path("configs") / "example.yaml"),
        help="Path to LLM-KG config (YAML).",
    )

    # placeholder command: validate-config
    v = sub.add_parser("validate-config", help="Validate config file exists (placeholder).")
    v.set_defaults(func=cmd_validate_config)

    # placeholder command: ingest-jsonl
    ij = sub.add_parser("ingest-jsonl", help="Ingest UWSS JSONL exports (placeholder).")
    ij.add_argument("--input", required=True, help="Path to UWSS export JSONL (or a run folder).")
    ij.set_defaults(func=cmd_ingest_jsonl)

    return p


def cmd_validate_config(args: argparse.Namespace) -> int:
    cfg = Path(args.config)
    if not cfg.exists():
        console.print(f"[red]Config not found:[/red] {cfg}")
        return 1
    console.print(f"[green]Config OK:[/green] {cfg}")
    return 0


def cmd_ingest_jsonl(args: argparse.Namespace) -> int:
    p = Path(args.input)
    if not p.exists():
        console.print(f"[red]Input not found:[/red] {p}")
        return 1
    console.print(
        "[yellow]Placeholder:[/yellow] ingestion not implemented yet. "
        "Next step will parse UWSS JSONL and build an intermediate corpus."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())



