from __future__ import annotations

import argparse
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class GoldSpec:
    contexts: list[str]
    resources: list[str]
    reactions: list[str]
    outcomes: list[str]


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.upper()
    s = s.replace("→", " ")
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _clean_md_item(s: str) -> str:
    s = s.strip()
    # remove markdown emphasis/backticks
    s = re.sub(r"[*`]+", "", s).strip()
    # collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _parse_gold_md(md: str) -> GoldSpec:
    """
    Parse `RICHMOND_GOLD_ENTITIES_RELATIONS_v1.md` into four lists:
    - contexts
    - mechanism resources
    - mechanism reactions
    - outcomes
    """
    section = None
    contexts: list[str] = []
    resources: list[str] = []
    reactions: list[str] = []
    outcomes: list[str] = []

    for raw in md.splitlines():
        ln = raw.strip()
        if ln.startswith("### 1.1"):
            section = "contexts"
            continue
        if ln.startswith("### 1.2"):
            section = "resources"
            continue
        if ln.startswith("### 1.3"):
            section = "reactions"
            continue
        if ln.startswith("### 1.4"):
            section = "outcomes"
            continue
        if ln.startswith("## 2)") or ln.startswith("## 3)"):
            section = None
            continue
        if section is None:
            continue

        # numbered items in contexts
        m_num = re.match(r"^\d+\.\s+\*\*(.+)\*\*\s*$", ln)
        if m_num:
            item = _clean_md_item(m_num.group(1))
            if section == "contexts":
                contexts.append(item)
            continue

        # bullet items in other sections
        m_b = re.match(r"^-+\s+\*\*(.+)\*\*\s*(?:\(|$)", ln)
        if m_b:
            item = _clean_md_item(m_b.group(1))
            if section == "resources":
                resources.append(item)
            elif section == "reactions":
                reactions.append(item)
            elif section == "outcomes":
                outcomes.append(item)
            continue

    # de-dup while preserving order
    def uniq(xs: list[str]) -> list[str]:
        seen = set()
        out = []
        for x in xs:
            k = _norm(x)
            if not k or k in seen:
                continue
            seen.add(k)
            out.append(x)
        return out

    return GoldSpec(
        contexts=uniq(contexts),
        resources=uniq(resources),
        reactions=uniq(reactions),
        outcomes=uniq(outcomes),
    )


def _match_items(*, gold_items: list[str], entity_texts: list[str]) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """
    High-precision token overlap match (handles paraphrases better than strict substring).
    Returns:
    - missing gold items
    - matches: [(gold_item, [matched_entity_titles...])]
    """
    STOP = {
        "THE",
        "A",
        "AN",
        "AND",
        "OR",
        "OF",
        "TO",
        "IN",
        "ON",
        "WITH",
        "FOR",
        "FROM",
        "AS",
        "BY",
        "WHEN",
        "THAT",
        "THIS",
        "THEIR",
        "STUDENTS",
        "STUDENT",
        "LEVEL",
        "OUTCOMES",
        "OUTCOME",
        "MECHANISM",
        "MECHANISMS",
        "CONTEXT",
        "CONTEXTS",
    }

    def toks(s: str) -> set[str]:
        ns = _norm(s)
        # keep short but meaningful tokens like LOW/HIGH
        ts = {t for t in ns.split(" ") if len(t) >= 3 and t not in STOP}
        return ts

    def variants(s: str) -> list[str]:
        """
        Expand composite gold labels into smaller alternatives so matching is feasible:
        - remove parenthetical notes
        - split on '/', ' OR ', ';'
        - keep arrow constructs as-is but also split around arrows
        """
        s2 = re.sub(r"\([^)]*\)", "", s).strip()
        s2 = s2.replace("→", " → ")
        parts: list[str] = []
        # split by ';' then by '/' and ' OR ' (keep it simple and predictable)
        for p in re.split(r"\s*;\s*", s2):
            for q in re.split(r"\s+OR\s+|/+", p, flags=re.IGNORECASE):
                parts.append(q)
        out = []
        for p in parts:
            pp = p.strip()
            if not pp:
                continue
            # also split around arrows for reaction statements
            if "→" in pp:
                left, right = [x.strip() for x in pp.split("→", 1)]
                if left:
                    out.append(left)
                if right:
                    out.append(right)
            out.append(pp)
        # de-dup normalized
        seen = set()
        uniq = []
        for x in out:
            k = _norm(x)
            if not k or k in seen:
                continue
            seen.add(k)
            uniq.append(x)

        # Add keyphrase variants to reduce false positives for long composite labels.
        words = _norm(s).split(" ")
        wset = set(words)
        if "KNOWLEDGE" in wset:
            if "LOW" in wset:
                uniq.append("LOW KNOWLEDGE")
            if "HIGH" in wset:
                uniq.append("HIGH KNOWLEDGE")
            if "MIXED" in wset:
                uniq.append("MIXED KNOWLEDGE")
            if "APPLY" in wset or "APPLICATION" in wset:
                uniq.append("APPLY KNOWLEDGE")
        if "COPING" in wset:
            uniq.append("COPING")
        if "EFFICACY" in wset:
            uniq.append("SELF EFFICACY")
        if "CONFIDENCE" in wset:
            uniq.append("SELF CONFIDENCE")

        # final de-dup normalized after adding keyphrases
        seen2 = set()
        uniq2 = []
        for x in uniq:
            k = _norm(x)
            if not k or k in seen2:
                continue
            seen2.add(k)
            uniq2.append(x)
        return uniq2

    # index entities by token sets
    ent_index: list[tuple[set[str], str]] = []
    for t in entity_texts:
        tt = (t or "").strip()
        if not tt:
            continue
        ent_index.append((toks(tt), tt))

    missing: list[str] = []
    matches: list[tuple[str, list[str]]] = []

    for g in gold_items:
        vs = variants(g)
        vts = [toks(v) for v in vs]
        vts = [t for t in vts if t]
        if not vts:
            continue
        hit_titles: list[str] = []
        for et, orig in ent_index:
            ok = False
            for gt in vts:
                # Require overlap >= 1 for single-token variants; otherwise >=2 and >=50% of variant tokens
                min_overlap = 1 if len(gt) <= 1 else max(2, int((len(gt) * 0.5) + 0.999))
                if len(gt & et) >= min_overlap:
                    ok = True
                    break
            if not ok:
                continue
            title = orig.split(" :: ", 1)[0].strip()
            hit_titles.append(title)
            if len(hit_titles) >= 8:
                break
        if hit_titles:
            matches.append((g, hit_titles))
        else:
            missing.append(g)

    return missing, matches


def _cmoc_family_counts(rels: pd.DataFrame) -> dict[str, int]:
    fam = rels.get("source_family", "").fillna("").astype(str) + "→" + rels.get("target_family", "").fillna("").astype(str)
    fam = fam.value_counts().to_dict()
    # keep stable keys
    keys = ["CONTEXT→MECHANISM", "CONTEXT→OUTCOME", "INTERVENTION→MECHANISM", "MECHANISM→OUTCOME", "INTERVENTION→OUTCOME", "COMPARATOR→OUTCOME"]
    return {k: int(fam.get(k, 0)) for k in keys}


def _write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Part A: compare normalized KG against Richmond gold entities/relations spec.")
    ap.add_argument("--out-dir", type=Path, required=True, help="GraphRAG output directory (contains *_cmoc_normalized.parquet).")
    ap.add_argument(
        "--gold-md",
        type=Path,
        default=Path("LLM-Knowledge-Graph/artifacts/partA/RICHMOND_GOLD_ENTITIES_RELATIONS_v1.md"),
        help="Gold spec markdown path.",
    )
    ap.add_argument(
        "--out-md",
        type=Path,
        default=None,
        help="Optional output markdown path. Default: artifacts/partA/gold_alignment_<run>.md",
    )
    args = ap.parse_args()

    out_dir = args.out_dir
    run_name = out_dir.name
    out_md = args.out_md or Path("LLM-Knowledge-Graph/artifacts/partA") / f"gold_alignment_{run_name}.md"

    e_path = out_dir / "entities_cmoc_normalized.parquet"
    r_path = out_dir / "relationships_cmoc_normalized.parquet"
    if not e_path.exists() or not r_path.exists():
        print(f"ERROR: expected normalized parquet not found in {out_dir}")
        print(f"- missing: {e_path} or {r_path}")
        return 1

    gold = _parse_gold_md(_read_text(args.gold_md))

    e = pd.read_parquet(e_path)
    r = pd.read_parquet(r_path)

    # Build entity texts for matching: TITLE :: DESCRIPTION
    titles = e.get("title", "").fillna("").astype(str).tolist()
    descs = e.get("description", "").fillna("").astype(str).tolist()
    entity_texts = []
    for t, d in zip(titles, descs, strict=False):
        t = (t or "").strip()
        if not t:
            continue
        dd = re.sub(r"\s+", " ", (d or "")).strip()
        entity_texts.append(f"{t} :: {dd}" if dd else t)

    miss_ctx, hit_ctx = _match_items(gold_items=gold.contexts, entity_texts=entity_texts)
    miss_res, hit_res = _match_items(gold_items=gold.resources, entity_texts=entity_texts)
    miss_rea, hit_rea = _match_items(gold_items=gold.reactions, entity_texts=entity_texts)
    miss_out, hit_out = _match_items(gold_items=gold.outcomes, entity_texts=entity_texts)

    fam_counts = _cmoc_family_counts(r)

    def pct(hit: int, total: int) -> str:
        return f"{(hit/total*100.0):.2f}%" if total else "0.00%"

    lines: list[str] = []
    lines.append(f"## Gold alignment report — `{run_name}` (Richmond Figure 1–3 targets)")
    lines.append("")
    lines.append(f"- out_dir: `{out_dir.as_posix()}`")
    lines.append(f"- gold_spec: `{args.gold_md.as_posix()}`")
    lines.append("")
    lines.append("### A) Run health (normalized KG)")
    lines.append("")
    lines.append(f"- entities (normalized): **{len(e)}**")
    lines.append(f"- relationships (normalized): **{len(r)}**")
    lines.append("")
    lines.append("### B) CMOC-family edge distribution (normalized)")
    lines.append("")
    for k, v in fam_counts.items():
        lines.append(f"- {k}: **{v}**")
    lines.append("")
    lines.append("### C) Gold entity coverage (token match against entity title/description; high-precision keyphrases)")
    lines.append("")
    lines.append(f"- contexts: **{len(hit_ctx)}/{len(gold.contexts)}** ({pct(len(hit_ctx), len(gold.contexts))})")
    lines.append(f"- mechanism resources: **{len(hit_res)}/{len(gold.resources)}** ({pct(len(hit_res), len(gold.resources))})")
    lines.append(f"- mechanism reactions: **{len(hit_rea)}/{len(gold.reactions)}** ({pct(len(hit_rea), len(gold.reactions))})")
    lines.append(f"- outcomes: **{len(hit_out)}/{len(gold.outcomes)}** ({pct(len(hit_out), len(gold.outcomes))})")
    lines.append("")

    def emit_hits(title: str, hits: list[tuple[str, list[str]]], missing: list[str]) -> None:
        lines.append(f"### {title}")
        lines.append("")
        if hits:
            lines.append("**Hits (gold item → matched entities):**")
            for g, ents in hits[:25]:
                lines.append(f"- **{g}** → {', '.join(f'`{x}`' for x in ents[:5])}" + (" ..." if len(ents) > 5 else ""))
            if len(hits) > 25:
                lines.append(f"- *(+{len(hits)-25} more hits omitted for brevity)*")
            lines.append("")
        if missing:
            lines.append("**Missing (no strict match found):**")
            for g in missing[:25]:
                lines.append(f"- **{g}**")
            if len(missing) > 25:
                lines.append(f"- *(+{len(missing)-25} more missing omitted for brevity)*")
            lines.append("")

    emit_hits("D) Gold contexts (Figure 2 backbone)", hit_ctx, miss_ctx)
    emit_hits("E) Gold mechanism resources (Figure 2–3)", hit_res, miss_res)
    emit_hits("F) Gold mechanism reactions (Figure 2–3)", hit_rea, miss_rea)
    emit_hits("G) Gold outcomes (Figure 2–3)", hit_out, miss_out)

    lines.append("### H) Interpretation (what to do next)")
    lines.append("")
    lines.append("- If **contexts** are missing: tighten extraction prompts to force explicit student-level contexts (coping, mixed-knowledge groups, inability-to-apply-knowledge) into `LEARNER_CONTEXT` entities.")
    lines.append("- If **resources/reactions** are missing: add an explicit “resource vs reaction” instruction in prompts and/or a postprocess normalizer that maps common phrases to `INTERVENTION` vs `MOTIVATION_AFFECT/COGNITIVE_STATE/MECHANISM`.")
    lines.append("- This report is **strict-match** by design (high precision). It will undercount paraphrases; that is acceptable for iteration (if you want, we can add fuzzy matching next).")
    lines.append("")

    _write_md(out_md, "\n".join(lines).strip() + "\n")
    print(f"Wrote: {out_md.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

