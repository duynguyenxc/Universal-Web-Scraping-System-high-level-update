## Part A (Education) — Verification note (meeting draft)

### What I ran

- Built a benchmark package for the Richmond-28 education corpus (28 records).
- Ingested 20 full-text PDFs + 8 URL-only studies (abstract fallback), and indexed with Microsoft GraphRAG using a CMO-oriented schema.

### Corpus coverage (from artifacts)

- **records (Richmond-28 target)**: 28
- **PDF-backed**: 20
- **URL-only**: 8
- **with DOI**: 27
- **with abstract** (used for URL-only ingestion): 20

### Evidence-grounded outputs produced

- Knowledge graph artifacts: `documents.parquet`, `text_units.parquet`, `entities.parquet`, `relationships.parquet`.
- Community-defined concept artifacts: `communities.parquet`, `community_reports.parquet` (human-readable export available).
- Claim/evidence artifacts: `covariates.parquet` (exported as `human_readable/claims.md`).

### Representative results (selected)

- **Community-as-mechanism**: *Self-Explanation in Medical Education* (community=8, rank=7.5, size=126).
- **Community-as-mechanism**: *Self-Explanation and Clinical Reasoning in Medical Education* (community=24, rank=8.5, size=65).
- **Community-as-mechanism**: *Diagnostic Performance and Self-Explanation in Medical Education* (community=57, rank=8.5, size=51).

**Sample CMO-relevant claims (evidence spans):**

- **INTERVENTION_EFFECT**: Self-explanation (SE) has been shown to be effective for medical students at the clerkship level, supporting the learning of clinical reasoning in context.
  - evidence: The use of self-explanation (SE) in the course of solving clinical cases has been shown to be effective for medical students at the clerkship level [PAGE 3].) 2. (SELF-EXPLANATION
- **INTERVENTION_EFFECT**: Medical students who generated self-explanations showed improved diagnostic performance on less familiar clinical cases compared to those who did not.
  - evidence: Students in the self-explanation condition, compared with those in the control condition, demonstrated better diagnostic performance on subsequent clinical cases, but this effect emerged only for cases concerning the less familiar topic. [PAGE 1]) 2. (SELF-EXP…
- **INTERVENTION_EFFECT**: Self-explanation (SE) engages students in active learning and has shown to be an effective technique to improve clinical reasoning in clerks.
  - evidence: Educational strategies that promote the development of clinical reasoning in students remain scarce. Generating self-explanations (SE) engages students in active learning and has shown to be an effective technique to improve clinical reasoning in clerks. [PAGE…

### Verification status vs. professor protocol (this week)

- **Search/screening alignment**: Corpus coverage is explicit (PDF-backed vs URL-only) and traceable via DOI/title metadata.
- **CMO extraction**: Claims include intervention effects, mechanism explanations, context moderators, and outcome measurements.
- **Community-defined concepts**: Communities summarize recurring mechanisms (e.g., self-explanation, schema-based learning, reflection).
- **Programme theory comparison (next)**: Map top mechanism-communities to Richmond’s programme theory components (structural comparison).

### Known limitations (transparent)

- 8/28 studies are URL-only (abstract-based), so evidence spans may be less detailed than full text.
- Only ~25% of extracted claim snippets preserve `[PAGE N]` markers; improving span traceability is a next refinement.

### Where to look in the repo

- Selected examples: `LLM-Knowledge-Graph/artifacts/partA/verification_selected_examples.md`
- Quality gates: `LLM-Knowledge-Graph/artifacts/partA/verification_audit.md`
- Community reports: `LLM-Knowledge-Graph/graphrag-project/output_partA/human_readable/community_reports.md`
- Claims: `LLM-Knowledge-Graph/graphrag-project/output_partA/human_readable/claims.md`
