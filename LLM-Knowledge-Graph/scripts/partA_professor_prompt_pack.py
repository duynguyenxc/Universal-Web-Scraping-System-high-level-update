from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def _read_entities(out_dir: Path) -> pd.DataFrame:
    p = out_dir / "entities_cmoc_normalized.parquet"
    if not p.exists():
        p = out_dir / "entities.parquet"
    if not p.exists():
        raise FileNotFoundError(p)
    e = pd.read_parquet(p)
    e["title"] = e.get("title", "").fillna("").astype(str)
    e["type"] = e.get("type", "").fillna("").astype(str)
    # keep only typed entries (normalized outputs should already satisfy this)
    e = e[(e["title"].str.strip() != "") & (e["type"].str.strip() != "")].copy()
    return e


def _read_relationships(out_dir: Path) -> pd.DataFrame:
    p = out_dir / "relationships_cmoc_normalized.parquet"
    if not p.exists():
        p = out_dir / "relationships.parquet"
    if not p.exists():
        raise FileNotFoundError(p)
    r = pd.read_parquet(p)
    for c in ["source", "target", "description"]:
        r[c] = r.get(c, "").fillna("").astype(str)
    return r[(r["source"].str.strip() != "") & (r["target"].str.strip() != "")].copy()


def _take_unique(xs: list[str], n: int) -> list[str]:
    out: list[str] = []
    seen = set()
    for x in xs:
        k = x.strip().upper()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(x.strip())
        if len(out) >= n:
            break
    return out


def _format_list(title: str, items: list[str]) -> str:
    lines = [f"### {title}", ""]
    if not items:
        lines.append("- (none)")
        lines.append("")
        return "\n".join(lines)
    for it in items:
        lines.append(f"- {it}")
    lines.append("")
    return "\n".join(lines)


def _sample_edges(r: pd.DataFrame, n: int) -> list[str]:
    # prefer concise, non-empty descriptions; keep a stable sample
    rr = r.copy()
    rr["desc_len"] = rr["description"].fillna("").astype(str).map(len)
    rr = rr.sort_values(["desc_len", "source", "target"], ascending=[True, True, True])
    rows = []
    for _, row in rr.head(n).iterrows():
        s = str(row["source"]).strip()
        t = str(row["target"]).strip()
        d = str(row.get("description", "")).strip()
        rows.append(f"{s} -> {t} | {d}" if d else f"{s} -> {t}")
    return rows


def _write_text(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Part A: generate a prompt pack for professor-style LLM comparison (Richmond paper → expected entities/relations → compare to our KG)."
    )
    ap.add_argument("--out-dir", type=Path, required=True, help="GraphRAG output directory.")
    ap.add_argument(
        "--out-txt",
        type=Path,
        default=None,
        help="Output prompt pack path. Default: artifacts/partA/professor_prompt_pack_<run>.txt",
    )
    ap.add_argument("--max-entities-per-type", type=int, default=35)
    ap.add_argument("--max-edges", type=int, default=120)
    args = ap.parse_args()

    out_dir = args.out_dir
    run = out_dir.name
    out_txt = args.out_txt or Path("LLM-Knowledge-Graph/artifacts/partA") / f"professor_prompt_pack_{run}.txt"

    e = _read_entities(out_dir)
    r = _read_relationships(out_dir)

    # Bucket entities by realist families used in our prompts
    by_type = {t: g["title"].tolist() for t, g in e.groupby("type")}
    def take(t: str) -> list[str]:
        return _take_unique(sorted(by_type.get(t, []), key=str.upper), int(args.max_entities_per_type))

    # Provide both specific and family-ish buckets, because different iterations may use either.
    entities_ctx = _take_unique(
        take("LEARNER_CONTEXT") + take("SETTING_CONTEXT") + take("CONTEXT"),
        int(args.max_entities_per_type),
    )
    entities_mech = _take_unique(
        take("MECHANISM") + take("COGNITIVE_STATE") + take("MOTIVATION_AFFECT"),
        int(args.max_entities_per_type),
    )
    entities_int = take("INTERVENTION")
    entities_out = take("OUTCOME")
    entities_comp = take("COMPARATOR")

    # Prefer normalized KG edge families if present
    edge_lines = _sample_edges(r, int(args.max_edges))

    prompt = []
    prompt.append("You are helping verify a realist-synthesis knowledge graph against a human gold standard review (Richmond et al., 2020).")
    prompt.append("")
    prompt.append("## Task (what the professor asked us to do)")
    prompt.append("1) Read/consider the attached Richmond et al. (2020) paper (especially outcomes/conclusion + Figures 1–3).")
    prompt.append("2) Based on what Richmond *claims* as their outputs, propose what a CMOC-style knowledge graph should contain:")
    prompt.append("   - entity families and example entities (Context, Mechanism Resource, Mechanism Reaction, Outcome, Intervention/Comparator if needed)")
    prompt.append("   - example relationship templates (CMOC directionality), with short predicates")
    prompt.append("3) Compare your proposed entities/relations to the extracted KG snapshot provided below.")
    prompt.append("4) Output a structured critique that we can use to improve prompts and postprocessing rules.")
    prompt.append("")
    prompt.append("## Output format (strict)")
    prompt.append("Return a markdown report with these sections:")
    prompt.append("- A) Expected entities (from Richmond outputs) — grouped by Context / Mresource / Mreaction / Outcome")
    prompt.append("- B) Expected relationship templates (allowed directions)")
    prompt.append("- C) Comparison vs our KG snapshot:")
    prompt.append("  - Missing entities (expected but not found)")
    prompt.append("  - Wrongly typed entities (found but wrong type/family)")
    prompt.append("  - Wrong directionality (edges violating CMOC direction)")
    prompt.append("  - Noisy/generic entities (should be dropped)")
    prompt.append("- D) Concrete improvement actions, in rule form:")
    prompt.append("  - Prompt changes (new constraints / wording)")
    prompt.append("  - Postprocess changes (type inference rules, drop rules, flip rules)")
    prompt.append("")
    prompt.append("## Constraints (realist fidelity)")
    prompt.append("- Treat OUTCOME as a sink (do not use outcome as a causal source edge).")
    prompt.append("- Prefer construct-level entities (avoid bibliographic/logistics entities).")
    prompt.append("- Prefer evidence-local relationships with cue verbs (enables/inhibits/triggers/leads_to/moderates).")
    prompt.append("")
    prompt.append("## Our KG snapshot (for comparison)")
    prompt.append(f"- run_name: {run}")
    prompt.append(f"- entities rows: {len(e)}")
    prompt.append(f"- relationships rows: {len(r)}")
    prompt.append("")
    prompt.append(_format_list("Entities — Context-like (learner_context / setting_context / context)", entities_ctx))
    prompt.append(_format_list("Entities — Mechanism-like (mechanism / cognitive_state / motivation_affect)", entities_mech))
    prompt.append(_format_list("Entities — Intervention", entities_int))
    prompt.append(_format_list("Entities — Outcome", entities_out))
    prompt.append(_format_list("Entities — Comparator", entities_comp))
    prompt.append("### Relationships (sample)")
    prompt.append("")
    for ln in edge_lines:
        prompt.append(f"- {ln}")
    prompt.append("")

    _write_text(out_txt, "\n".join(prompt).strip() + "\n")
    print(f"Wrote: {out_txt.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

