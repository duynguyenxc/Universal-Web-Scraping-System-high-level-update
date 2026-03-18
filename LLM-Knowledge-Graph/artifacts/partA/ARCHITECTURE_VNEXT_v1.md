## Part A (Education) — Multi‑Agent Architecture Sketch v1 (Richmond‑aligned)

This document is the **execution‑grade frame** requested in the meeting transcript: *how many agents, what each agent does, what the outputs are, and how humans can interact at critical locations*.

### 0) Goal (verification target)

- **Target gold standard**: Richmond et al. (2020) realist review output built from **28 included studies** and expressed as **CMOCs + programme theory**.
- **System goal**: a multi‑agent pipeline that can:
  - **(a) select** a set close to Richmond’s included set (selection layer),
  - **(b) extract** verification‑grade entities/relationships/claims with evidence anchors (extraction layer),
  - **(c) synthesize** programme theory (synthesis layer),
  - **(d) evaluate** closeness to Richmond with explicit metrics and audit trails.

### 1) Pipeline overview (agents + artifacts)

```
Corpus (≈100, includes Richmond‑28) + Richmond metadata + PDFs
  ↓
[Agent A0] Protocol Binder (IPT + definitions + criteria)
  ↓  (protocol.json + ontology.yaml + gold_targets.json)
[Agent A1] Corpus Builder (search/harvest + dedupe)
  ↓  (corpus_catalog.jsonl)
[Agent A2] Screening / Selection
  ↓  (selected_set.jsonl + exclusion_log.jsonl + selection_metrics.md)
[Agent A3] Per‑paper Ingestion (PDF→text units + page markers)
  ↓  (graphrag_input/*.txt)
[Agent A4] Graph/Claim Extractor (LLM; GraphRAG extract_graph + extract_covariates)
  ↓  (entities.*, relationships.*, claims/covariates.* + human_readable/*.md)
[Agent A5] Realist Normalizer (CMOC typing + dedupe + anti-noise rules)
  ↓  (claims_enriched.md + cmo_configurations.md + normalized_entities/relationships)
[Agent A6] Synthesizer (programme theory + context backbone)
  ↓  (programme_theory.md + cmoc_backbone.md)
[Agent A7] Evaluator (gold comparison)
  ↓  (scorecard.md + audit_samples.md)

HUMAN checkpoints: after A0, A2, A5, A6, A7 (rules saved and consumed)
```

### 2) Agents (responsibilities + I/O contracts)

#### Agent A0 — Protocol Binder (human‑guided)
- **Purpose**: freeze “what counts” as Context/Mechanism/Outcome and what the pipeline must output.
- **Input**: Richmond paper + supervisor abstract + meeting transcript constraints.
- **Output artifacts**:
  - `protocol.json`: scope, inclusion logic, outputs required, evaluation plan pointers.
  - `ontology.yaml`: entity types + allowed CMOC relation families.
  - `richmond_gold_targets_v1.json`: gold contexts/mechanisms/outcomes keywords (for automated recall checks).
- **Human checkpoint (required)**: approve/edit the protocol before running selection/extraction.

#### Agent A1 — Corpus Builder (≈100)
- **Purpose**: build a comparison‑ready corpus where Richmond‑28 are *known members* of a larger set.
- **Input**: seed queries + metadata for Richmond‑28.
- **Output artifacts**:
  - `corpus_catalog.jsonl`: doc_id, title, year, abstract, pdf_path/url, provenance.

#### Agent A2 — Screening / Selection (100 → ~28)
- **Purpose**: simulate realist screening (criteria + theory‑driven relevance).
- **Input**: `corpus_catalog.jsonl` + `protocol.json` + any human rules.
- **Output artifacts**:
  - `selected_set.jsonl` (target size ~28, not hard‑coded),
  - `exclusion_log.jsonl` (reason codes),
  - `selection_metrics.md` (precision/recall vs Richmond set, when labels are available).
- **Human checkpoint (critical)**: review borderline studies and add rules to reduce false positives/negatives.

#### Agent A3 — Per‑paper Ingestion (evidence anchoring)
- **Purpose**: prepare verification‑grade text with stable identifiers and page markers.
- **Input**: PDFs and/or URL abstracts.
- **Output artifacts**:
  - `graphrag_input/*.txt` with `[PAGE N]` markers and stable `DocumentID`.
- **Hard gate**: if page anchors are missing, do **not** proceed to “verification claims”.

#### Agent A4 — Graph/Claim Extractor (LLM)
- **Purpose**: extract construct‑level entities/relations + evidence‑linked claims.
- **Input**: `graphrag_input/*.txt` + prompts.
- **Output artifacts**:
  - `entities.*`, `relationships.*`, `claims/covariates.*`, `human_readable/*.md`.
- **Note**: this stage is where **OpenAI quota** is consumed.

#### Agent A5 — Realist Normalizer (deterministic post‑process)
- **Purpose**: enforce CMOC fidelity, reduce noise, dedupe, prefer learner‑response mechanisms.
- **Input**: raw GraphRAG outputs.
- **Output artifacts**:
  - `claims_enriched.md` (verification‑grade claims),
  - `cmo_configurations.md` (draft CMOC candidates).
- **Human checkpoint (critical)**: validate a sample and add persistent rules (see HIL spec).

#### Agent A6 — Synthesizer (programme theory)
- **Purpose**: build programme theory from recurrent CMOCs; surface contradictions.
- **Input**: enriched claims + CMOCs.
- **Output artifacts**:
  - `programme_theory.md`,
  - `cmoc_backbone.md` (contexts ↔ mechanisms ↔ outcomes).
- **Human checkpoint**: approve backbone contexts/mechanism families; add rules for synthesis focus.

#### Agent A7 — Evaluator (gold comparison)
- **Purpose**: compute “closeness to Richmond” metrics at 3 layers.
- **Input**: selection output + extraction output + synthesis output + gold targets.
- **Output artifacts**:
  - `scorecard.md` (metrics + pass/fail gates),
  - `audit_samples.md` (evidence trace examples).

### 3) What “similar outcome” means (operational definition)

We do **not** claim perfect identity with Richmond. We require:
- **Auditability first**: claims/edges/CMOCs must cite evidence spans (doc + page markers).
- **Backbone recovery**: key contexts/mechanism families/outcomes must be recoverable in extracted entities/claims/communities.
- **Selection closeness**: from a mixed corpus, the selected set must substantially overlap Richmond’s included set.

### 4) Minimal run sequence (practical)

1. Run A3→A5 on a **subset (2–5 PDFs)**, iterate prompts/rules until gates pass.
2. Run the same on **Richmond‑28** (full).
3. Only then, enable A1→A2 selection layer for the “100→28” experiment.

