## Part A — Scorecard (markdown-based) — `output_partA_richmond28_v4_run2`

- output dir: `LLM-Knowledge-Graph/graphrag-project/output_partA_richmond28_v4_run2`
- generated from: `human_readable/*.md` (no parquet required)

### A) Quality gates (run health)

- entities rows: **874**
- blank entity types: **0** (target 0)
- corrupt entity titles: **0** (target 0)
- relationships rows: **916**
- CMO-ish edges: **762** (**83.19%**, target ≥ 15%)

### B) Claim traceability (verification gate)

- claims source: `claims_fixed.parquet`
- claims rows: **500**
- claims with `[PAGE N]`: **210** (**42.00%**, target ≥ 90%)
- claims with `CMO[...]` tag: **500** (**100.00%**)
- missing subject: **0**
- missing object: **0**
- missing source_text: **0**

### C) Richmond gold target recall (keyword proxy)

- contexts hit: **3/9** (**33.33%**)
- mechanisms hit: **11/11** (**100.00%**)
- outcomes hit: **6/6** (**100.00%**)

- context hits: CONFIDENCE, PRIOR KNOWLEDGE, SELF-EFFICACY
- mechanism hits: ANALYTIC REASONING, ANXIETY, COGNITIVE LOAD, ILLNESS SCRIPTS, INSIGHT, NON-ANALYTIC REASONING, PATTERN RECOGNITION, REFLECTION, SELF-EXPLANATION, STRESS, UNDERSTANDING
- outcome hits: CONFIDENCE RATING, DIAGNOSTIC ACCURACY, DIAGNOSTIC PERFORMANCE, ERROR RATE, RETENTION, SATISFACTION

### D) Notes / next iteration hints

- `[PAGE N]` coverage < 90%: enforce evidence spans earlier (ingestion + claim prompt).
- Keyword recall is only a proxy; final judgement requires sample audit against Richmond CMOCs.
