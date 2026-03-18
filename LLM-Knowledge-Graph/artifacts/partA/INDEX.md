## Part A (Education verification) — How to read the outputs (START HERE)

If you feel lost because there are many folders/files, this page is the single “front door”.

### One place to open (for supervisors/reviewers)

Open:

- `LLM-Knowledge-Graph/artifacts/partA/share_v4/index.md`

It is a single page with links to everything important (no hunting across folders).

### What you should read (recommended order, v4)

1) **KG health gates (entities/relationships)**  
`graphrag-project/output_partA_richmond28_v4_run2/human_readable/quality_gates.md`

2) **Gold alignment vs Richmond (Figure 1–3 targets)**  
`artifacts/partA/gold_alignment_output_partA_richmond28_v4_run2.md`

3) **Scorecard (one-page summary for iteration)**  
`artifacts/partA/scorecard_output_partA_richmond28_v4_run2.md`

4) **Professor-style comparison prompt pack (Richmond expected KG → compare our KG)**  
`artifacts/partA/professor_prompt_pack_output_partA_richmond28_v4_run2.txt`

5) **GraphRAG “human_readable” exports (community detection + community_reports)**  
Under the run’s `human_readable/` folder:
- `community_reports.md`
- `communities.md`
- `entities.md`, `relationships.md`, `documents.md`

### Notes (why outputs are split)

- GraphRAG writes heavy artifacts (`*.parquet`, `lancedb/`) into `graphrag-project/output_partA/` for indexing/query.  
- We do **not** commit those heavy artifacts to GitHub.
- Instead, we commit “lightweight snapshots” (Markdown/JSON) so reviewers can read outputs directly on GitHub.

