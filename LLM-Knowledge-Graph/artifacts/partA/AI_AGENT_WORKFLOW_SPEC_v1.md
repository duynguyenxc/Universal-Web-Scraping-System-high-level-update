## AI Agent Workflow Specification v1 — Multi‑AI Agent Framework to Simulate Richmond (Human) Workflow

### 1) Objective (what the AI workflow is trying to achieve)
Build a multi‑agent workflow that **simulates the human realist review algorithm** in Richmond et al. (2020) and produces outputs that are **verifiably comparable** to the human gold standard:
- **Selection layer**: from a mixed corpus (~100) select a set close to Richmond‑28.
- **Synthesis layer**: extract and consolidate CMOC‑family entities/relationships/claims into a programme theory comparable to Richmond’s outputs.

This document is the **system method** (what the professor called “the architecture is the method”).

---

## 2) AI “System Architecture” (agents, tools, artefacts, checkpoints)

### 2.1 Agents (who does what)
The framework is a chain of agents. Agents may use the **same underlying LLM**, but each agent has a **different prompt contract** and produces an artefact that becomes the next agent’s input.

- **A0 Protocol Binder** (maps to Human Stage 0–1)
  - Freeze IPT + definitions + evaluation rubric.
- **A1 Corpus Builder** (maps to Human Stage 2 input)
  - Build mixed corpus with provenance (vNext).
- **A2 Screening/Selection** (maps to Human Stage 3)
  - Include/exclude/borderline with realist criteria + rule artefacts (vNext).
- **A3 Per‑paper Ingestion** (maps to Human Stage 4 input)
  - Create page‑anchored text units for each included paper.
- **A4 Extractor (GraphRAG)** (maps to Human Stage 4)
  - Extract entities/relationships + claims with evidence anchors.
- **A5 Normalizer/Validator** (maps to Human Stage 4 QA + structured representation)
  - Deterministic postprocess: CMOC normalization, evidence repair, export CMOC artefacts.
- **A6 Synthesizer** (maps to Human Stage 5)
  - Consolidate cross‑study patterns into programme theory (vNext).
- **A7 Evaluator** (maps to Human Stage 5–6 “compare with gold standard”)
  - Scorecards + audit samples + iteration plan.

### 2.2 Tooling (current implementation vs vNext)
- **Current implementation (already runnable)**
  - Graph extraction and evaluation on Richmond‑28:
    - `scripts/partA_run_graphrag_v4.ps1` (pipeline runner)
    - `scripts/partA_postprocess_kg.py` (CMOC normalization)
    - `scripts/partA_quality_gates.py` (gates)
    - `scripts/partA_scorecard_md.py` (scorecard)
- **vNext (selection + synthesis completion)**
  - A1/A2 (100→28) selection layer and full A6 programme theory synthesizer.

### 2.3 Core artefacts (what each stage must produce)
- Protocol artefacts:
  - `artifacts/partA/paper_review_richmond_2020.md`
  - `artifacts/partA/richmond_gold_targets_v1.json`
  - `artifacts/partA/RICHMOND_GOLD_EVAL_RUBRIC_v1.md`
- Run artefacts (per run directory):
  - `entities.parquet`, `relationships.parquet`, `text_units.parquet`
  - `human_readable/entities.md`, `relationships.md`, `quality_gates.md`
  - `scorecard_*.md`

### 2.4 Human-in-the-loop checkpoints (feedback must change behaviour)
See `artifacts/partA/HIL_INTERACTION_SPEC_v1.md`.
Critical checkpoints:
- after A0: approve IPT + definitions
- after A2: approve selection + exclusion rules (vNext)
- after A5: audit CMOC fidelity and typing/noise rules
- after A7: accept evaluation; decide next iteration changes

---

## 3) AI Algorithm (step-by-step execution sequence; output→input chaining)

### Step 0 — Bind protocol (A0)
**Input**: gold paper review + transcript constraints  
**Output**: frozen IPT + rubric + targets

### Step 1 — Ingest papers (A3)
**Input**: PDFs/full texts  
**Output**: text units with `[PAGE N]` markers (verification anchor)

### Step 2 — Extract KG + claims (A4)
**Input**: text units  
**Output**: `entities.parquet`, `relationships.parquet`, and claim tables (when enabled)

### Step 3 — Normalize & export (A5)
**Input**: raw extraction  
**Output**: CMOC-normalized KG + repaired, evidence-linked claims + CMOC exports

### Step 4 — Evaluate vs Richmond (A7)
**Input**: normalized outputs + gold targets  
**Output**: scorecard + audit samples + iteration plan

