## Professor transcript requirements — Traceability Matrix v1 (deliverables + verification)

This matrix enumerates the **6 requirements** the professor states (repeatedly) in the transcript and maps each requirement to:
- **deliverables** (what file(s) must exist),
- **implementation evidence** (where it is in code/artifacts),
- **verification method** (how to check it is real, not hand-wavy).

---

## R1) Human Workflow Specification (Gold Standard)
**Professor intent (transcript)**: “how the human… in that process… what is their intent… they establish criteria… define something… then screen… then go to 28 publications…”

- **Deliverable**:
  - `artifacts/partA/HUMAN_WORKFLOW_SPEC_RICHMOND_v1.md`
- **Gold source anchor**:
  - `artifacts/partA/paper_review_richmond_2020.md`
- **Verification**:
  - The workflow document must contain (a) objective, (b) roles/tools/artefacts, (c) staged algorithm with inputs/operations/outputs, and (d) verifiable outputs (28 included + CMOCs + programme theory).

---

## R2) AI can “do the same workflow” (human → agent mapping)
**Professor intent (transcript)**: “do you feel you can make the AI agent to do that… to do the same… what the human do in that process?”

- **Deliverable**:
  - `artifacts/partA/AI_AGENT_WORKFLOW_SPEC_v1.md`
- **Verification**:
  - Each human stage (framing, IPT, search, screening, per-paper extraction, synthesis, evaluation) has an explicit agent counterpart with defined I/O and artefacts.

---

## R3) Definition of “agent” as LLM + prompts + publication input, chained by outputs
**Professor intent (transcript)**: “AI agent is… a language model… receive special prompts… feed with publication… output as input for another agent…”

- **Deliverables**:
  - `artifacts/partA/ONE_BY_ONE_PROMPTS_SPEC_v1.md` (prompt contracts)
  - Concrete extraction prompts:
    - `graphrag-project/prompts_partA_v4/extract_graph.txt`
    - `graphrag-project/prompts_partA_v4/extract_claims.txt`
- **Verification**:
  - Run produces tangible artefacts (`entities.parquet`, `relationships.parquet`, and later `claims_fixed`) that demonstrate prompt-driven extraction.

---

## R4) Multi-agent framework must be “serious one-by-one prompts, step-by-step”
**Professor intent (transcript)**: “special prompts for each… serious one-by-one… step by step… finish one then next…”

- **Deliverable**:
  - `artifacts/partA/ONE_BY_ONE_PROMPTS_SPEC_v1.md` with per-agent prompt contracts (inputs, output schema, stop conditions).
- **Verification**:
  - Agent outputs are consumed by subsequent stages:
    - ingestion → GraphRAG extraction → deterministic postprocess → evaluation scorecard.
  - Evidence: `scripts/partA_run_graphrag_v4.ps1` sequences these steps.

---

## R5) Human-in-the-loop at different stages; feedback modifies behavior
**Professor intent (transcript)**: “people not only provide one input… provide input at different stage… feedback… incorporate… modify behavior…”

- **Deliverable**:
  - `artifacts/partA/HIL_INTERACTION_SPEC_v1.md`
- **Verification**:
  - At least one concrete iteration shows: human feedback → persisted rule artefact → measurable change in next run’s metrics (scorecard/quality gates).

---

## R6) Evaluation vs gold standard with explicit metrics (selection + synthesis)
**Professor intent (transcript)**: “compare outcome with publication… golden standard… define metrics… metrics tell how close…”

- **Deliverables**:
  - `artifacts/partA/RICHMOND_GOLD_EVAL_RUBRIC_v1.md`
  - `artifacts/partA/richmond_gold_targets_v1.json`
  - `scripts/partA_scorecard_md.py` (automated scorecard)
- **Verification**:
  - Scorecard is generated from a run directory and reports selection/extraction/synthesis proxies reproducibly, e.g.:
    - `artifacts/partA/scorecard_output_partA_richmond28_v4_run2.md`

