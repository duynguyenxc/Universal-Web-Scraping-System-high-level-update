from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _as_list(v: Any) -> list[str]:
    if v is None:
        return []
    # numpy/pandas arrays
    if hasattr(v, "tolist") and callable(getattr(v, "tolist")):
        try:
            vv = v.tolist()
            if isinstance(vv, list):
                return [str(x) for x in vv if str(x).strip()]
        except Exception:
            pass
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    if isinstance(v, tuple):
        return [str(x) for x in v if str(x).strip()]
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return []
        # Sometimes a single id is stored as a string; treat as singletons.
        return [s]
    return [str(v)]

def text_units_by_id(text_units: pd.DataFrame) -> dict[str, dict[str, Any]]:
    # Cache-friendly dict index
    cols = [c for c in ["id", "text"] if c in text_units.columns]
    if "id" not in cols or "text" not in cols:
        return {}
    return text_units.set_index("id")[["text"]].to_dict(orient="index")


def _infer_claim_type(source_type: str, target_type: str) -> str:
    st = (source_type or "").strip().upper()
    tt = (target_type or "").strip().upper()
    if tt == "OUTCOME":
        if st == "INTERVENTION":
            return "INTERVENTION_EFFECT"
        if st in {"MECHANISM", "COGNITIVE_STATE", "MOTIVATION_AFFECT"}:
            return "MECHANISM_EXPLANATION"
        if st in {"CONTEXT", "LEARNER_CONTEXT", "SETTING_CONTEXT", "TASK_CASE"}:
            return "CONTEXT_MODERATOR"
    if tt in {"MECHANISM", "COGNITIVE_STATE", "MOTIVATION_AFFECT"}:
        if st in {"CONTEXT", "LEARNER_CONTEXT", "SETTING_CONTEXT", "TASK_CASE"}:
            return "CONTEXT_MODERATOR"
        if st == "INTERVENTION":
            return "MECHANISM_EXPLANATION"
    return "MECHANISM_EXPLANATION"


def _infer_cmo_fields(source: str, target: str, source_type: str, target_type: str) -> tuple[str, str, str, str]:
    st = (source_type or "").strip().upper()
    tt = (target_type or "").strip().upper()
    C = "NONE"
    I = "NONE"
    M = "NONE"
    O = "NONE"

    # Default: treat mechanism-family as MECHANISM slot.
    def is_mech(t: str) -> bool:
        return t in {"MECHANISM", "COGNITIVE_STATE", "MOTIVATION_AFFECT"}

    def is_context(t: str) -> bool:
        return t in {"CONTEXT", "LEARNER_CONTEXT", "SETTING_CONTEXT", "TASK_CASE"}

    if st == "INTERVENTION":
        I = source
    elif is_context(st):
        C = source
    elif is_mech(st):
        M = source

    if tt == "OUTCOME":
        O = target
    elif is_mech(tt):
        M = target if M == "NONE" else M
    elif is_context(tt):
        C = target if C == "NONE" else C

    return (C, I, M, O)


@dataclass(frozen=True)
class ClaimRow:
    subject_id: str
    object_id: str
    type: str
    status: str
    start_date: str
    end_date: str
    description: str
    source_text: str
    text_unit_id: str


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate claims_fixed.parquet offline from relationships + text_units (fallback when GraphRAG claims/covariates are missing)."
    )
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--max-claims", type=int, default=500, help="Cap number of claims to write (top by weight).")
    ap.add_argument("--out-parquet", type=str, default="claims_fixed.parquet")
    args = ap.parse_args()

    out_dir: Path = args.out_dir
    rel_p = out_dir / "relationships.parquet"
    ent_p = out_dir / "entities.parquet"
    tu_p = out_dir / "text_units.parquet"
    if not rel_p.exists():
        raise SystemExit(f"Missing: {rel_p}")
    if not ent_p.exists():
        raise SystemExit(f"Missing: {ent_p}")
    if not tu_p.exists():
        raise SystemExit(f"Missing: {tu_p}")

    rels = pd.read_parquet(rel_p)
    ents = pd.read_parquet(ent_p)
    tus = pd.read_parquet(tu_p)

    # title -> type mapping (GraphRAG relationships use titles, not ids)
    emap = ents.set_index("title")["type"].fillna("").astype(str).to_dict()

    rels = rels.copy()
    rels["__w"] = rels.get("weight", 0).fillna(0).astype(float)
    rels = rels.sort_values("__w", ascending=False).head(int(args.max_claims))

    tu_index = text_units_by_id(tus)

    rows: list[ClaimRow] = []
    for _, r in rels.iterrows():
        src = _s(r.get("source")).strip()
        tgt = _s(r.get("target")).strip()
        if not src or not tgt:
            continue
        st = _s(emap.get(src, "")).strip()
        tt = _s(emap.get(tgt, "")).strip()
        ctype = _infer_claim_type(st, tt)

        # evidence snippet from first linked text_unit
        tu_ids = r.get("text_unit_ids")
        tuid = ""
        evidence = ""
        ids = _as_list(tu_ids)
        if ids:
            tuid = ids[0]
            evidence = _s(tu_index.get(tuid, {}).get("text", "")).strip()
        if len(evidence) > 800:
            evidence = evidence[:800].rstrip() + "…"

        C, I, M, O = _infer_cmo_fields(src, tgt, st, tt)
        rel_desc = _s(r.get("description")).strip()
        desc = rel_desc if rel_desc else f"{src} -> {tgt}"
        desc = desc.strip()
        desc = desc + "\n" + f"CMO[C={C}; I={I}; M={M}; O={O}]"

        rows.append(
            ClaimRow(
                subject_id=src,
                object_id=tgt,
                type=ctype,
                status="TRUE",
                start_date="NONE",
                end_date="NONE",
                description=desc,
                source_text=evidence,
                text_unit_id=tuid,
            )
        )

    out_df = pd.DataFrame([c.__dict__ for c in rows])
    out_p = out_dir / args.out_parquet
    out_df.to_parquet(out_p, index=False)
    print(f"Wrote: {out_p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

