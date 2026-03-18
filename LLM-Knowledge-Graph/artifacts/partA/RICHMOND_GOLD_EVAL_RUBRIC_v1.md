## Richmond Gold Evaluation Rubric v1 (Gold target → Check → Evidence → Metric → Pass threshold)

This rubric operationalizes “**sát Richmond**” into verifiable checks. It is designed to be used both:
- as a **methods section** (what we evaluate and why), and
- as a **run scorecard** (pass/fail gates and iteration targets).

### Global gate (must pass before any comparison)

| Gold target | What to check | Evidence requirement | Metric | Pass threshold |
|---|---|---|---|---|
| Evidence traceability | Every exported claim/CMO candidate is anchored to a source span with document id + page marker | Claim text must include `[PAGE N]` (or equivalent) and stable doc id | % claims with page marker | **≥ 90%** |

---

### Layer 1 — Selection (≈100 → ≈28)

| Gold target | What to check | Evidence requirement | Metric | Pass threshold |
|---|---|---|---|---|
| Included set overlap | Selected set contains Richmond‑28 items (as many as possible) | Each selected item must have title/DOI and stable id | Recall@K vs Richmond‑28 | **≥ 0.80** (target) |
| Precision of selection | Most selected items are truly “intervention→mechanism/outcome” reasoning education papers | Selection log must include reason codes | Precision@K (human audited sample) | **≥ 0.70** (target) |
| Explainability | System can justify inclusion/exclusion with stable reason codes | `exclusion_log.jsonl` entries for dropped studies | % decisions with reason code | **100%** |

Notes:
- Early drafts may be evaluated with smaller corpora; the metric definitions remain the same.

---

### Layer 2 — Extraction (entities / relationships / claims)

| Gold target | What to check | Evidence requirement | Metric | Pass threshold |
|---|---|---|---|---|
| Construct‑level entities | Entities are conceptual constructs (not bibliographic noise) | Top‑N entity titles must be auditable | Noise rate in Top‑N (heuristic + audit) | **≤ 5%** |
| Realist typing | Entities have types aligning to Context/Mechanism/Outcome (and intervention/comparator) | Entity type must be non‑blank | Blank type count | **0** |
| CMOC‑family relations | Graph contains realist‑useful edge families | Edge list + types available | CMO‑ish edge % | **≥ 15%** |
| Mechanism quality | Mechanisms are learner responses/processes (not logistics) | Sampled mechanism edges must cite evidence | % mechanism edges judged valid (audit sample) | **≥ 0.70** |
| Deduplication | Avoid repeated/near‑duplicate claims | Claims export with signatures | Duplicate rate (within doc) | **≤ 10%** |

---

### Layer 3 — Synthesis (programme theory)

| Gold target | What to check | Evidence requirement | Metric | Pass threshold |
|---|---|---|---|---|
| Context backbone | Recover Richmond‑style key student contexts (e.g., knowledge level, coping/self‑efficacy patterns) | Each backbone statement must link to supporting claims | Backbone context recall (keyword + audit) | **≥ 0.80** |
| Pathway alignment | Programme theory expresses C→M→O pathways (not just topic clusters) | Each pathway has multi‑study support with citations | Pathway coverage score (rubric) | **≥ 0.70** |
| Contradiction surfacing | Conflicting findings are not smoothed over | Contradiction section with evidence links | # contradictions surfaced | **≥ 1** when present |

---

### What to report in the draft paper (minimal)

- A table of metrics for **Selection / Extraction / Synthesis**
- A short “iteration story”: Run1 → human rule → Run2 improvement (with evidence links)

