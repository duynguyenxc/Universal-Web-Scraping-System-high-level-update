## Part A (Education) — Tonight’s “meeting-ready” verification checklist (Richmond benchmark)

This checklist mirrors the professor’s protocol. If all items below are satisfied, you can credibly claim the system is **verification-ready** (process + artifacts), not merely “running”.

### 0) Freeze benchmark package (inputs)
- **Richmond-28 target list**: `LLM-Knowledge-Graph/artifacts/partA/studies_metadata.csv`
- **Corpus coverage snapshot**: `LLM-Knowledge-Graph/artifacts/partA/verification_summary.md`
- **Quality audit (gates)**: `LLM-Knowledge-Graph/artifacts/partA/verification_audit.md`

### 1) Search & screening alignment
- **You can show**: which of the Richmond-28 are present locally (PDF vs URL-only) and what is missing.
- **Artifact**: `studies_metadata.csv` + `verification_summary.md`
- **Pass condition**: for every missing paper, you can point to a reason (missing PDF; URL blocked; etc.).

### 2) CMO extraction fidelity (claims as evidence spans)
- **You can show**: sample claims that link Context/Intervention/Mechanism/Outcome, each with an evidence span/snippet.
- **Artifacts**:
  - `graphrag-project/output_partA/claims.parquet`
  - `graphrag-project/output_partA/human_readable/claims.md`
  - `verification_audit.md` (spot-check)
- **Pass condition**:
  - claims exist for most papers (coverage),
  - claim source text uses short spans (not long quotes),
  - outcomes are endpoints (measured or clearly reported), not metadata.

### 3) Community-defined conceptual entities vs human mechanisms
- **You can show**: community reports that read like “principles/mechanisms” (not author/journal clusters).
- **Artifacts**:
  - `graphrag-project/output_partA/community_reports.parquet`
  - `graphrag-project/output_partA/human_readable/community_reports.md`
- **Pass condition**:
  - community titles are specific (not generic “students/education”),
  - minimal bibliographic noise (authors/journals/years) in top entities.

### 4) Cross-study synthesis
- **You can show**: 2–3 dominant mechanism pathways and at least 1 contradiction/conditional pattern.
- **Artifacts**:
  - `community_reports.md` (global sensemaking)
  - GraphRAG query response output (global method)
- **Pass condition**: every synthesized pattern is grounded with citations/spans.

### 5) Programme theory comparison (structural)
- **You can show**: a mapping table from system communities/CMOs to Richmond programme theory components.
- **Artifacts**:
  - (manual table for meeting) + citations into `community_reports.md`/`claims.md`
- **Pass condition**: structural correspondence is explained; mismatches are documented (not hidden).

### 6) End-to-end “human-like” Q&A demo
- **You can show**: answers to fixed realist questions with explicit citations.
- **Artifacts**:
  - terminal output from `graphrag query --method global`
- **Pass condition**: no “direct answering” without evidence from claims/papers.

