from __future__ import annotations

"""
Backward-compatible entrypoint for the previous v3 script name.

Use `scripts/partA_postprocess_kg.py` for new work (supports v2/v3/v4, CMOC-family
directionality flipping, and consistent output filenames).
"""

from partA_postprocess_kg import cli


def main() -> int:
    return cli(default_label="v3")


if __name__ == "__main__":
    raise SystemExit(main())

