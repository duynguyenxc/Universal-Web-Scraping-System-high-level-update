## Part A (Education) — Human‑in‑the‑Loop (HIL) Interaction Spec v1

This spec answers the professor’s question: **how can humans interact with the pipeline at different stages**, and how that feedback **modifies system behavior** in later iterations.

### 1) Design principles

- **Critical locations**: humans intervene only where judgement is required (selection, CMOC fidelity, synthesis).
- **Persistent rules**: feedback is stored as **rule artefacts** and must be **consumed** by later agents.
- **Auditability**: every rule change is recorded with who/when/why and linked to observed failure cases.

### 2) Interaction checkpoints (what the human does)

#### Checkpoint H0 — Protocol approval (before any run)
- **Human action**: confirm IPT summary + definitions of Context/Mechanism/Outcome + output requirements.
- **Artefact produced**: `rules/protocol_overrides.yaml`

#### Checkpoint H1 — Selection review (after screening)
- **Human action**:
  - mark selected papers as **keep / drop / borderline**,
  - add reason codes (why should/shouldn’t be included),
  - provide examples of false positives/false negatives.
- **Artefacts produced**:
  - `rules/selection_rules.yaml`
  - `rules/selection_exceptions.jsonl`

#### Checkpoint H2 — Extraction audit (after claims + entities/edges export)
- **Human action** (sample‑based, not full):
  - confirm if **mechanisms are learner responses** (not logistics),
  - flag generic placeholders (“STUDENTS”, “THE STUDY”),
  - flag ungrounded claims (missing `[PAGE N]`).
- **Artefacts produced**:
  - `rules/extraction_filters.yaml` (banlists, allowlists, typing hints)
  - `rules/mechanism_typing_hints.yaml`

#### Checkpoint H3 — Synthesis review (programme theory/backbone)
- **Human action**:
  - approve or edit the **context backbone** (Richmond‑style key contexts),
  - demand separation of *mechanism‑resource* vs *mechanism‑response* when needed,
  - require contradiction surfacing if two studies disagree.
- **Artefacts produced**:
  - `rules/synthesis_focus.yaml`

#### Checkpoint H4 — Evaluation acceptance (scorecard)
- **Human action**:
  - accept/reject a run as “close enough for reporting” based on thresholds,
  - request a targeted iteration (which metric failed → which rule should change).
- **Artefacts produced**:
  - `rules/acceptance_thresholds.yaml`
  - `rules/iteration_plan.md`

### 3) Rule artefact format (minimal but enforceable)

All rule artefacts live under:

`LLM-Knowledge-Graph/artifacts/partA/rules/`

Recommended minimal schema (YAML):

- `version`: integer or date string
- `created_by`: human identifier
- `created_at`: timestamp
- `rationale`: short explanation
- `rules`: list of rule objects

Rule object examples:

- **ban_entity_title_contains**: list of substrings
- **prefer_mechanism_terms**: list of mechanism keyword hints
- **drop_claim_if_missing_page_marker**: boolean
- **require_cmo_tag**: boolean
- **selection_drop_if**: boolean expression templates (used by screening agent)

### 4) Consumption: how rules change behavior (hard requirement)

Each agent must load rules before running:

- **Selection agent** consumes:
  - `selection_rules.yaml`, `selection_exceptions.jsonl`
- **Extractor/Normalizer** consumes:
  - `extraction_filters.yaml`, `mechanism_typing_hints.yaml`
- **Synthesizer** consumes:
  - `synthesis_focus.yaml`
- **Evaluator** consumes:
  - `acceptance_thresholds.yaml`

### 5) Evidence: what “feedback incorporated” means

In the next run, we should be able to show:

- The previous run had a failure case (linked row in `audit_samples.md`)
- A human rule was added (linked YAML rule id)
- The next run’s scorecard shows the metric improved or the failure disappeared

