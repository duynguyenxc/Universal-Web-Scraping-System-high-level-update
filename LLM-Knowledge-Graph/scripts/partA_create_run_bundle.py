from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path


def _write_text(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def _copy_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Part A: create a single lightweight run bundle (markdown/json) for sharing/review."
    )
    ap.add_argument("--out-dir", type=Path, default=Path("graphrag-project/output_partA"))
    ap.add_argument("--artifacts-dir", type=Path, default=Path("artifacts/partA"))
    ap.add_argument("--run-name", type=str, default="")
    args = ap.parse_args()

    out_dir = args.out_dir
    artifacts_dir = args.artifacts_dir

    run_name = args.run_name.strip() or datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle_dir = artifacts_dir / "runs" / run_name
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # 1) Front-door index
    idx_src = artifacts_dir / "INDEX.md"
    _copy_if_exists(idx_src, bundle_dir / "INDEX.md")

    # 2) Core verification artifacts
    for name in [
        "verification_note.md",
        "verification_selected_examples.md",
        "verification_audit.md",
        "verification_summary.md",
        "claims_enriched.md",
        "cmo_configurations.md",
        "studies_metadata.csv",
        "studies_metadata.jsonl",
    ]:
        _copy_if_exists(artifacts_dir / name, bundle_dir / name)

    # 3) GraphRAG lightweight exports (human_readable)
    hr = out_dir / "human_readable"
    for name in [
        "community_reports.md",
        "claims.md",
        "entities.md",
        "relationships.md",
        "communities.md",
        "documents.md",
        "stats.json",
    ]:
        _copy_if_exists(hr / name, bundle_dir / "human_readable" / name)

    # 4) Bundle README (the only file someone needs to open first)
    readme = []
    readme.append("## Part A — Run bundle\n")
    readme.append(f"- run: **{run_name}**")
    readme.append(f"- created_at: {datetime.now().isoformat(timespec='seconds')}")
    readme.append("")
    readme.append("### Start here (recommended order)\n")
    readme.append("1. `verification_note.md`")
    readme.append("2. `verification_selected_examples.md`")
    readme.append("3. `verification_audit.md`")
    readme.append("4. `claims_enriched.md`")
    readme.append("5. `cmo_configurations.md`")
    readme.append("6. `human_readable/community_reports.md`")
    readme.append("")
    readme.append("### What is intentionally NOT included\n")
    readme.append("- GraphRAG heavy outputs (`*.parquet`, `lancedb/`) are excluded to keep the bundle lightweight and GitHub-friendly.")
    readme.append("")
    _write_text(bundle_dir / "index.md", "\n".join(readme).strip() + "\n")

    print(f"Created bundle: {bundle_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

