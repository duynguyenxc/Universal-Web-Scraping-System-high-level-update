## Part A (Education verification) — How to read the outputs (START HERE)

If you feel lost because there are many folders/files, this page is the single “front door”.

### One place to open (for supervisors/reviewers)

Open:

- `artifacts/partA/share/index.md`

It is a single page with links to everything important (no hunting across folders).

### What you should read (recommended order)

1) **Verification note (short narrative)**  
`verification_note.md`  
What it is: meeting-ready summary of what was run + what is verified/not-yet-verified.

2) **Selected examples (quick demo)**  
`verification_selected_examples.md`  
What it is: a small curated set of communities/claims to show quickly.

3) **Verification audit (quality gates)**  
`verification_audit.md`  
What it is: coverage + anti-noise + traceability checks + spot-check tables.

4) **Verification-grade claims table (paper-linked)**  
`claims_enriched.md`  
What it is: claims joined to paper metadata via `text_unit_id` so each row is auditable (DOI/title/year + evidence snippet).

5) **Draft CMO configurations (auto-generated)**  
`cmo_configurations.md`  
What it is: per-paper CMO candidates derived from claims + entity typing; intended for Richmond-style mapping + human refinement.

6) **GraphRAG “human_readable” exports (raw GraphRAG artifacts)**  
`graphrag-project/output_partA_v2/human_readable/`  
Key files:
- `community_reports.md` (largest, most important GraphRAG artifact)
- `claims.md` (sample view; not verification-grade)
- `claims_fixed.md` (repaired claims view; verification helper when covariates parsing fails)
- `entities.md`, `relationships.md`, `communities.md`, `documents.md`
- `stats.json`

### Notes (why outputs are split)

- GraphRAG writes heavy artifacts (`*.parquet`, `lancedb/`) into `graphrag-project/output_partA/` for indexing/query.  
- We do **not** commit those heavy artifacts to GitHub.
- Instead, we commit “lightweight snapshots” (Markdown/JSON) so reviewers can read outputs directly on GitHub.

