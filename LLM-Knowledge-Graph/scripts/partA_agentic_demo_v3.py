from __future__ import annotations

import argparse
import subprocess
from datetime import datetime
from pathlib import Path


def _run_graphrag_query(*, root: Path, config: Path, data: Path, method: str, query: str) -> str:
    """
    Lightweight "agent tool": call GraphRAG query CLI and capture stdout.
    We keep this dependency-free (no LangChain required) so the demo runs anywhere.
    """
    cmd = [
        "graphrag",
        "query",
        "--root",
        str(root),
        "--config",
        str(config),
        "--data",
        str(data),
        "--method",
        method,
        "--query",
        query,
        "--response-type",
        "Bullet list of 8-12 items",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        raise RuntimeError(f"GraphRAG query failed (exit={proc.returncode}).\nSTDERR:\n{err}\nSTDOUT:\n{out}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Part A v3: agentic-style demo (GraphRAG as KG layer; no LangChain required)."
    )
    ap.add_argument("--out-dir", type=Path, required=True, help="GraphRAG output directory (contains entities.parquet).")
    ap.add_argument("--config", type=Path, default=Path("graphrag-project/settings.partA.v3.yaml"))
    ap.add_argument("--root", type=Path, default=Path("graphrag-project"))
    ap.add_argument("--method", type=str, default="global", choices=["global", "local", "basic", "drift"])
    ap.add_argument(
        "--out-md",
        type=Path,
        default=Path("artifacts/partA/agentic_demo_v3.md"),
        help="Where to write the demo report.",
    )
    args = ap.parse_args()

    questions = [
        # Professor-style: "what did they have in mind" -> extract programme theory components.
        "From the included papers, what are the key learner contexts (e.g., prior knowledge, self-efficacy/confidence) that moderate intervention effectiveness? Provide evidence-grounded bullets.",
        # Richmond backbone: mechanisms and why.
        "What mechanisms explain why an intervention improves (or harms) diagnostic accuracy? Focus on cognitive load, self-explanation, illness scripts, reflection, pattern recognition.",
        # CMO: intervention -> mechanism -> outcome.
        "List the main intervention → mechanism → outcome pathways supported by evidence in this corpus (CMO-style).",
        # Contradictions are important in the journal abstract.
        "Are there contradictory findings (same intervention, different outcomes across contexts)? If yes, summarize the contradiction patterns and the context differences.",
    ]

    root = args.root.resolve()
    config = args.config.resolve()
    out_dir = args.out_dir.resolve()

    lines: list[str] = []
    lines.append("## Part A v3 — Agentic demo (GraphRAG as knowledge layer)\n")
    lines.append(f"- generated_at: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- out_dir: `{out_dir.as_posix()}`")
    lines.append(f"- query_method: `{args.method}`")
    lines.append(f"- config: `{config.as_posix()}`")
    lines.append("")
    lines.append("### What this demonstrates")
    lines.append("- GraphRAG answers **global sensemaking** questions over the corpus via communities/summaries.")
    lines.append("- Outputs are intended to be **auditable** via evidence snippets/claims (see `claims_fixed.md` in the run).")
    lines.append("")

    for i, q in enumerate(questions, start=1):
        lines.append(f"### Q{i}. {q}")
        ans = _run_graphrag_query(root=root, config=config, data=out_dir, method=args.method, query=q)
        lines.append("")
        lines.append(ans)
        lines.append("")

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(f"Wrote: {args.out_md.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

