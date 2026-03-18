## One‑by‑one Prompts Specification v1 (per-agent contracts, step-by-step, non‑vague)

This document operationalises the professor’s requirement:
> “special prompts for each… serious one‑by‑one, one‑by‑one prompts… step by step… output becomes input for next agent.”

It specifies **prompt contracts** (what each agent must do, with what input, producing what output schema, and when it must stop).

### 0) Prompting conventions (applies to all agents)
- **Inputs are bounded**: each agent receives a fixed schema, not free-form context.
- **Outputs are structured**: JSON (or schema-constrained markdown) with stable fields.
- **Evidence anchoring**: whenever the agent asserts a CMOC claim, it must cite an evidence snippet; if `[PAGE N]` exists in input, it must be preserved.
- **Stop conditions**: agent must explicitly output `INSUFFICIENT_EVIDENCE` rather than hallucinating.

---

## A2 — Screening / Selection Agent (≈100 → ≈28)

### A2.1 Objective
Select studies that **contribute to programme theory building** (realist relevance), not merely topical overlap.

### A2.2 System prompt (contract)
**Input schema** (per record):
- `paper_id`, `title`, `abstract`, `keywords`, `year`, `venue`, `url_or_pdf`, `metadata_fields`
- `protocol`: operational definitions of Context/Mechanism/Outcome + inclusion/exclusion principles
- `rules`: selection rule artefacts (e.g., `selection_rules.yaml`)

**Required output schema** (JSON per paper):
- `paper_id`
- `decision`: `include | exclude | borderline`
- `reason_codes`: stable codes (e.g., `NO_INTERVENTION`, `NO_LEARNER_CONTEXT`, `NO_OUTCOME`, `NOT_UNDERGRAD`, `NOT_HPE`, `INSUFFICIENT_DETAIL`)
- `cmoc_hint` (if include/borderline): `C=...; I=...; M=...; O=...`
- `confidence`: 0.0–1.0
- `notes`: short, audit-friendly

**Stop condition**
- If abstract is insufficient to justify include/exclude: output `borderline` and request full text.

---

## A4 — Extractor (GraphRAG): Entities + Relationships (`extract_graph`)

### A4.1 Concrete prompt file in repo
- `graphrag-project/prompts_partA_v4/extract_graph.txt`

### A4.2 System prompt (contract)
**Input**
- Chunked paper text units, preserving `[PAGE N]` markers where present.

**Required behaviour**
- Extract **construct-level** nodes; avoid:
  - bibliographic noise (author lists, venues),
  - placeholders (`ENTITY`, empty titles),
  - study logistics unless needed as Context.
- Prefer realist families:
  - **Context** (learner/teacher/setting constraints),
  - **Intervention** (educational resource/technique),
  - **Mechanism** (resource/response; cognitive/affective processes),
  - **Outcome** (measurable endpoints),
  - limited method nodes (only when explicitly moderating outcomes).

**Relationship constraints**
- Prefer CMOC-family directions:
  - `CONTEXT → MECHANISM`
  - `INTERVENTION → MECHANISM`
  - `MECHANISM → OUTCOME`
  - `INTERVENTION → OUTCOME` (when mechanism implicit)
- If direction uncertain: emit relationship with explicit hedging in `description` (do not force).

**Stop condition**
- If a chunk contains only procedural text (e.g., measurement details) with no explanatory CMOC content: output nothing.

---

## A4b — Extractor (GraphRAG): Claims (`extract_covariates`)

### A4b.1 Concrete prompt file in repo
- `graphrag-project/prompts_partA_v4/extract_claims.txt`

### A4b.2 System prompt (contract)
**Input**
- Chunked text units with evidence and `[PAGE N]` markers.

**Required output fields** (row schema)
- `subject`, `object`
- `claim_type` (e.g., `TRIGGERS`, `ENABLES`, `INHIBITS`, `IMPROVES`, `WORSENS`, `MODERATES`)
- `status` (e.g., `SUPPORTED | CONTRADICTED | UNCERTAIN`)
- `description` must end with an explicit CMOC tag:
  - `CMO[C=...; I=...; M=...; O=...]`
- `source_text`: must include `[PAGE N]` when present in input

**Stop condition**
- If the CMOC cannot be stated without inventing C/I/M/O: output `INSUFFICIENT_EVIDENCE`.

---

## A5 — Normalizer / Postprocess (deterministic rule layer)

### A5.1 Deterministic modules in repo
- `scripts/partA_repair_claims_parquet.py` (claim repair + evidence filling)
- `scripts/partA_postprocess_kg.py` (CMOC-family normalization)

### A5.2 Rule contract
- **Entity typing**: if invalid/unmapped type → keep auditable but mark for iteration (do not silently “fix” without logging).
- **CMOC directionality**: if reverse edge is CMOC-family and forward is not → flip and mark `[FLIPPED_FOR_CMOC]`.
- **Outcome sink constraint**: drop remaining OUTCOME-as-source edges in normalized graph.

---

## A7 — Evaluator (gold comparison + iteration targets)

### A7.1 Implementation evidence
- `scripts/partA_scorecard_md.py`
- `artifacts/partA/RICHMOND_GOLD_EVAL_RUBRIC_v1.md`

### A7.2 Output schema
- `scorecard_*.md` with:
  - quality gates (blank types, corrupt titles, CMOC-edge ratio)
  - traceability stats (claims with `[PAGE N]`, CMO tags)
  - gold keyword proxy recall (contexts/mechanisms/outcomes)
- `iteration_plan.md` (when gates fail: which prompt/rule changes are required)

