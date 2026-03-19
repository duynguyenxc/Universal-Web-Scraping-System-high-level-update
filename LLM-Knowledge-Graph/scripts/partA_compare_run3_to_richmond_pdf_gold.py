from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RUN3_DIR = ROOT / "LLM-Knowledge-Graph" / "graphrag-project" / "output_partA_richmond28_v4_run3"
PDF_GOLD = ROOT / "LLM-Knowledge-Graph" / "documents" / "Richmond KG Specification.pdf"


@dataclass(frozen=True)
class GoldEntity:
    id: str
    label: str
    etype: str  # P/C/I/M_resource/M_response/O


@dataclass(frozen=True)
class GoldRel:
    id: str
    subj: str
    pred: str  # ENABLES/CONSTRAINS/TRIGGERS/PROVIDES/OPERATES_THROUGH/LEADS_TO/MODERATES/ASSOCIATED_WITH
    obj: str


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("’", "'").replace("“", '"').replace("”", '"')
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _token_jaccard(a: str, b: str) -> float:
    ta = set(_norm(a).split())
    tb = set(_norm(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(1, len(ta | tb))


def extract_pdf_text(pdf_path: Path) -> str:
    # Try PyMuPDF first, then pypdf.
    try:
        import fitz  # type: ignore

        doc = fitz.open(pdf_path)
        return "\n".join(page.get_text("text") for page in doc)
    except Exception:
        try:
            from pypdf import PdfReader  # type: ignore

            r = PdfReader(str(pdf_path))
            return "\n".join((page.extract_text() or "") for page in r.pages)
        except Exception as e2:
            raise RuntimeError(f"Failed to extract PDF text: {pdf_path}") from e2


def parse_gold_from_pdf_text(text: str) -> tuple[list[GoldEntity], list[GoldRel]]:
    text = text.replace("“", '"').replace("”", '"').replace("’", "'")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    entities: list[GoldEntity] = []
    for i, ln in enumerate(lines):
        # PDF extraction often puts E01 on its own line, then label on following lines.
        m = re.match(r"^(E\d{2})(?:\s+(.*))?$", ln)
        if not m:
            continue
        eid = m.group(1)
        rest = (m.group(2) or "").strip()
        buf: list[str] = []
        if rest:
            buf.append(rest)
        etype = None
        for j in range(i + 1, min(len(lines), i + 60)):
            tok = lines[j]
            if tok in {"P", "C", "I", "M_resource", "M_response", "O"}:
                etype = tok
                break
            # stop if next entity/relation starts
            if re.match(r"^(E\d{2}|R\d{2})\b", tok):
                break
            # skip obvious table headers
            if tok.lower() in {"id", "entity_label", "entity_type", "evidence_quote", "location_pointer"}:
                continue
            buf.append(tok)
        label = re.sub(r"\s+", " ", " ".join(buf)).strip(" -\t")
        if etype and label:
            entities.append(GoldEntity(eid, label, etype))

    preds = [
        "ENABLES",
        "CONSTRAINS",
        "TRIGGERS",
        "PROVIDES",
        "OPERATES_THROUGH",
        "LEADS_TO",
        "MODERATES",
        "ASSOCIATED_WITH",
    ]
    rels: list[GoldRel] = []
    for i, ln in enumerate(lines):
        # Same issue: R01 often appears alone on a line.
        m = re.match(r"^(R\d{2})(?:\s+(.*))?$", ln)
        if not m:
            continue
        rid = m.group(1)
        rest = (m.group(2) or "").strip()
        subj_parts: list[str] = []
        if rest:
            subj_parts.append(rest)
        pred = None
        obj_parts: list[str] = []

        # Scan following lines: subject until predicate token, then object.
        mode = "subj"
        for j in range(i + 1, min(len(lines), i + 80)):
            tok = lines[j]
            if re.match(r"^(E\d{2}|R\d{2})\b", tok):
                break
            if tok.lower() in {"id", "subject", "predicate", "object", "evidence_quote", "location_pointer"}:
                continue
            if mode == "subj":
                if tok in preds:
                    pred = tok
                    mode = "obj"
                    continue
                subj_parts.append(tok)
            else:
                # Stop object at first quote or location markers.
                if '"' in tok:
                    tok = tok.split('"', 1)[0].strip()
                    if tok:
                        obj_parts.append(tok)
                    break
                if tok.startswith("Results") or tok.startswith("Figure") or tok.startswith("Location:"):
                    break
                obj_parts.append(tok)

        subj = re.sub(r"\s+", " ", " ".join(subj_parts)).strip(" -\t")
        obj = re.sub(r"\s+", " ", " ".join(obj_parts)).strip(" -\t")
        if pred and subj and obj:
            rels.append(GoldRel(rid, subj, pred, obj))

    return entities, rels


def load_run3() -> tuple[pd.DataFrame, pd.DataFrame]:
    ent_p = RUN3_DIR / "entities_cmoc_normalized.parquet"
    rel_p = RUN3_DIR / "relationships_cmoc_normalized.parquet"
    if not ent_p.exists():
        raise FileNotFoundError(ent_p)
    if not rel_p.exists():
        raise FileNotFoundError(rel_p)
    ent = pd.read_parquet(ent_p)
    rel = pd.read_parquet(rel_p)
    return ent, rel


def build_entity_index(ent: pd.DataFrame) -> dict[str, dict[str, str]]:
    # index normalized title -> {title,type}
    idx: dict[str, dict[str, str]] = {}
    for _, row in ent.iterrows():
        title = str(row.get("title", "")).strip()
        if not title:
            continue
        k = _norm(title)
        if not k:
            continue
        if k not in idx:
            idx[k] = {"title": title, "type": str(row.get("type", "")).strip()}
    return idx


def best_entity_match(gold_label: str, idx: dict[str, dict[str, str]]) -> tuple[str | None, float, list[tuple[str, float]]]:
    k = _norm(gold_label)
    if k in idx:
        return idx[k]["title"], 1.0, [(idx[k]["title"], 1.0)]
    # fuzzy: token jaccard
    scores: list[tuple[str, float]] = []
    for kn, v in idx.items():
        s = _token_jaccard(k, kn)
        if s >= 0.55:
            scores.append((v["title"], s))
    scores.sort(key=lambda x: x[1], reverse=True)
    if not scores:
        return None, 0.0, []
    return scores[0][0], scores[0][1], scores[:5]


def gold_type_ok(gold_type: str, run_type: str) -> bool:
    rt = (run_type or "").upper()
    gt = gold_type
    if gt == "I":
        return rt == "INTERVENTION"
    if gt == "O":
        return rt == "OUTCOME"
    if gt == "P":
        return "POPULATION" in rt or rt == "LEARNER_POPULATION"
    if gt == "C":
        return "CONTEXT" in rt or rt in {"SETTING_CONTEXT", "LEARNER_CONTEXT", "CONTEXT", "CLINICAL_DOMAIN"}
    if gt in {"M_resource", "M_response"}:
        return rt == "MECHANISM" or "MECHANISM" in rt or rt in {"COGNITIVE_STATE", "MOTIVATION_AFFECT"}
    return False


def build_edge_lookup(rel: pd.DataFrame) -> dict[tuple[str, str], list[str]]:
    # (source_title_norm, target_title_norm) -> list of description strings
    out: dict[tuple[str, str], list[str]] = {}
    for _, row in rel.iterrows():
        s = str(row.get("source", "")).strip()
        t = str(row.get("target", "")).strip()
        if not s or not t:
            continue
        desc = str(row.get("description", "")).strip().lower()
        key = (_norm(s), _norm(t))
        out.setdefault(key, []).append(desc)
    return out


def pred_matches(gold_pred: str, run_desc: str) -> bool:
    d = (run_desc or "").lower()
    gp = gold_pred
    if gp == "ENABLES":
        return "enable" in d
    if gp == "CONSTRAINS":
        return "constrain" in d or "reduce" in d or "decrease" in d or "hinder" in d
    if gp == "TRIGGERS":
        return "trigger" in d or "cause" in d or "lead" in d or "result" in d or "elic" in d
    if gp == "PROVIDES":
        return "provide" in d or "offer" in d
    if gp == "OPERATES_THROUGH":
        return "operate" in d or "through" in d
    if gp == "LEADS_TO":
        return "lead" in d or "result" in d or "improv" in d or "increase" in d or "decrease" in d
    if gp == "MODERATES":
        return "moderate" in d or "moderat" in d
    if gp == "ASSOCIATED_WITH":
        return "associate" in d or "correl" in d or "link" in d or "related" in d
    return False


def main() -> None:
    ent, rel = load_run3()
    idx = build_entity_index(ent)
    edges = build_edge_lookup(rel)

    pdf_text = extract_pdf_text(PDF_GOLD)
    gold_entities, gold_rels = parse_gold_from_pdf_text(pdf_text)

    # Save parsed gold so it can be inspected.
    (RUN3_DIR / "_gold_from_pdf_entities.json").write_text(
        json.dumps([e.__dict__ for e in gold_entities], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (RUN3_DIR / "_gold_from_pdf_rels.json").write_text(
        json.dumps([r.__dict__ for r in gold_rels], ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Entity coverage
    matched = []
    missing = []
    type_mismatch = []
    for e in gold_entities:
        m_title, score, top = best_entity_match(e.label, idx)
        if not m_title or score < 0.70:
            missing.append((e.id, e.etype, e.label, top))
            continue
        run_type = idx[_norm(m_title)]["type"]
        matched.append((e.id, e.etype, e.label, m_title, score, run_type))
        if not gold_type_ok(e.etype, run_type):
            type_mismatch.append((e.id, e.etype, e.label, m_title, run_type, score))

    # Edge coverage (requires entity matches)
    ent_map = {gid: m_title for (gid, _, _, m_title, _, _) in matched}
    gold_edges_total = 0
    gold_edges_hit = 0
    gold_edges_missing = []
    gold_edges_pred_mismatch = []
    for r in gold_rels:
        gold_edges_total += 1
        subj = r.subj
        obj = r.obj
        # match entities by label, not by E-id (relations table uses subject/object text).
        subj_m, subj_s, _ = best_entity_match(subj, idx)
        obj_m, obj_s, _ = best_entity_match(obj, idx)
        if not subj_m or subj_s < 0.70 or not obj_m or obj_s < 0.70:
            gold_edges_missing.append((r.id, r.pred, subj, obj, "entity_not_found"))
            continue
        k = (_norm(subj_m), _norm(obj_m))
        descs = edges.get(k, [])
        if not descs:
            # allow reversed edge if was_flipped created direction change (best-effort)
            rev = edges.get((_norm(obj_m), _norm(subj_m)), [])
            if rev:
                descs = [f"(reversed){d}" for d in rev]
        if not descs:
            gold_edges_missing.append((r.id, r.pred, subj_m, obj_m, "edge_not_found"))
            continue
        if any(pred_matches(r.pred, d) for d in descs):
            gold_edges_hit += 1
        else:
            gold_edges_pred_mismatch.append((r.id, r.pred, subj_m, obj_m, descs[:5]))

    # Print report
    print("=== Richmond PDF gold vs run3 CMOC-normalized (quick coverage) ===")
    print(f"Run3 entities: {len(ent)} | Run3 relationships: {len(rel)}")
    print(f"Gold entities parsed from PDF: {len(gold_entities)}")
    print(f"Gold relations parsed from PDF: {len(gold_rels)}")
    print()
    print(f"Entity coverage (>=0.70 token match): {len(matched)}/{len(gold_entities)} = {len(matched)/max(1,len(gold_entities)):.1%}")
    print(f"  Type mismatches among matched: {len(type_mismatch)}")
    print(f"Edge coverage (entity matched + edge exists + predicate approx): {gold_edges_hit}/{gold_edges_total} = {gold_edges_hit/max(1,gold_edges_total):.1%}")
    print(f"  Missing edges: {len(gold_edges_missing)}")
    print(f"  Predicate mismatches: {len(gold_edges_pred_mismatch)}")
    print()

    print("Top missing gold entities (up to 15):")
    for (eid, etype, label, top) in missing[:15]:
        top_s = ", ".join([f"{t}:{s:.2f}" for t, s in top[:3]]) if top else "-"
        print(f"  {eid} [{etype}] {label} | candidates: {top_s}")
    print()

    print("Top type mismatches (up to 15):")
    for (eid, etype, label, m_title, run_type, score) in type_mismatch[:15]:
        print(f"  {eid} gold={etype} matched='{m_title}' run_type={run_type} score={score:.2f}")
    print()

    print("Top missing gold edges (up to 20):")
    for rid, pred, subj, obj, why in gold_edges_missing[:20]:
        print(f"  {rid} {subj} --{pred}--> {obj} | {why}")
    print()

    print("Top predicate mismatches (up to 20):")
    for rid, pred, subj_m, obj_m, descs in gold_edges_pred_mismatch[:20]:
        print(f"  {rid} {subj_m} --{pred}--> {obj_m} | run_desc={descs}")

    # Save a machine-readable summary
    summary = {
        "run3": {"entities": int(len(ent)), "relationships": int(len(rel))},
        "gold": {"entities": int(len(gold_entities)), "relationships": int(len(gold_rels))},
        "coverage": {
            "entities_matched": int(len(matched)),
            "entities_total": int(len(gold_entities)),
            "edges_hit": int(gold_edges_hit),
            "edges_total": int(gold_edges_total),
            "type_mismatch": int(len(type_mismatch)),
            "edges_missing": int(len(gold_edges_missing)),
            "edges_predicate_mismatch": int(len(gold_edges_pred_mismatch)),
        },
    }
    (RUN3_DIR / "_gold_alignment_summary_from_pdf.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()

