"""
Deprecated.

This file originally hardcoded local absolute paths to export a small sample into
`graphrag-project/input/`.

Use the parameterized script instead:
  python scripts/graphrag_prepare_input.py --day 25-12-06 --max-docs 50 --clean
"""

from __future__ import annotations


def main() -> int:
    print(__doc__.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
