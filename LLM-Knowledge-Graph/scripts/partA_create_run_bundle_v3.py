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


def _rel_from_share_to_outdir(out_dir: Path) -> str:
    """
    share page lives at: artifacts/partA/share_v3/index.md
    so the repo-root for relative links is 3 levels up.
    """
    try:
        rel = out_dir.relative_to(Path("LLM-Knowledge-Graph"))
    except Exception:
        rel = out_dir
    return (Path("../../../") / rel).as_posix()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Part A v3: create a review-friendly entrypoint without overwriting v1/v2 artifacts."
    )
    ap.add_argument("--out-dir", type=Path, default=Path("graphrag-project/output_partA_v3"))
    ap.add_argument("--artifacts-dir", type=Path, default=Path("artifacts/partA"))
    ap.add_argument(
        "--mode",
        type=str,
        default="share",
        choices=["share", "runs"],
        help="share: write a stable link-page under artifacts/partA/share_v3/. "
        "runs: create a timestamped bundle under artifacts/partA/runs_v3/.",
    )
    ap.add_argument("--run-name", type=str, default="", help="Used only for mode=runs (default: timestamp).")
    args = ap.parse_args()

    out_dir = args.out_dir
    artifacts_dir = args.artifacts_dir

    if args.mode == "share":
        share_dir = artifacts_dir / "share_v3"
        share_dir.mkdir(parents=True, exist_ok=True)

        out_rel = _rel_from_share_to_outdir(out_dir)

        lines: list[str] = []
        lines.append("## Part A (Education) — Share page v3 (START HERE)\n")
        lines.append(f"- updated_at: {datetime.now().isoformat(timespec='seconds')}\n")
        lines.append("### Recommended reading order\n")
        lines.append("1. `../verification_note.md`")
        lines.append("2. `../verification_selected_examples.md`")
        lines.append("3. `../verification_audit_v3.md`")
        lines.append("4. `../claims_enriched_v3.md`")
        lines.append("5. `../cmo_configurations_v3.md`")
        lines.append(f"6. `{out_rel}/human_readable/community_reports.md`")
        lines.append("")
        lines.append("### Raw GraphRAG human_readable exports\n")
        lines.append(f"- `{out_rel}/human_readable/claims.md`")
        lines.append(f"- `{out_rel}/human_readable/claims_fixed.md` (if present)")
        lines.append(f"- `{out_rel}/human_readable/entities.md`")
        lines.append(f"- `{out_rel}/human_readable/relationships.md`")
        lines.append(f"- `{out_rel}/human_readable/communities.md`")
        lines.append(f"- `{out_rel}/human_readable/documents.md`")
        lines.append(f"- `{out_rel}/human_readable/stats.json`")
        lines.append("")
        lines.append("### Notes\n")
        lines.append("- v3 artifacts are intentionally separated from earlier runs for clean comparison.")
        lines.append("- Heavy GraphRAG outputs (`*.parquet`, `lancedb/`) are intentionally not included/committed.")
        _write_text(share_dir / "index.md", "\n".join(lines).strip() + "\n")
        print(f"Wrote: {share_dir.resolve() / 'index.md'}")
        return 0

    run_name = args.run_name.strip() or datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle_dir = artifacts_dir / "runs_v3" / run_name
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # Core artifacts (v3 filenames)
    for name in [
        "verification_note.md",
        "verification_selected_examples.md",
        "verification_audit_v3.md",
        "claims_enriched_v3.md",
        "cmo_configurations_v3.md",
        "studies_metadata.csv",
        "studies_metadata.jsonl",
    ]:
        _copy_if_exists(artifacts_dir / name, bundle_dir / name)

    hr = out_dir / "human_readable"
    for name in [
        "community_reports.md",
        "claims.md",
        "claims_fixed.md",
        "entities.md",
        "relationships.md",
        "communities.md",
        "documents.md",
        "stats.json",
    ]:
        _copy_if_exists(hr / name, bundle_dir / "human_readable" / name)

    readme = []
    readme.append("## Part A v3 — Run bundle\n")
    readme.append(f"- run: **{run_name}**")
    readme.append(f"- created_at: {datetime.now().isoformat(timespec='seconds')}")
    readme.append("")
    readme.append("### Start here (recommended order)\n")
    readme.append("1. `verification_note.md`")
    readme.append("2. `verification_selected_examples.md`")
    readme.append("3. `verification_audit_v3.md`")
    readme.append("4. `claims_enriched_v3.md`")
    readme.append("5. `cmo_configurations_v3.md`")
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

