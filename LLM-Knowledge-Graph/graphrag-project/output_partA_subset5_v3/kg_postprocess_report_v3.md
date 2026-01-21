## Part A v3 — KG postprocess (CMO normalization)

- out_dir: `LLM-Knowledge-Graph/graphrag-project/output_partA_subset5_v3`
- wrote: `entities_cmo_normalized.parquet`, `relationships_cmo_normalized.parquet`

### Summary

- entities: 216 → 216
- relationships: 186 → 186
- blank entity types: 15 → 3
- OUTCOME-as-source edges: 86 → 7

### What was normalized

- **Type spelling/enum normalization** (e.g., `COGNITIVE STATE` → `COGNITIVE_STATE`).
- **Conservative blank-type inference** for a small set of obvious titles (logged below).
- **Directionality normalization**: edges with `OUTCOME → X` flipped to `X → OUTCOME` and marked with `[FLIPPED_FOR_CMO]`.

### Inferred types for previously blank entities (conservative rules)

- `FEATURE ANALYSIS` → `MECHANISM`
- `TRAINING TIME` → `SETTING_CONTEXT`
- `SPONTANEOUS INSTRUCTIONS` → `INTERVENTION`
- `TIME-ON-TASK` → `OUTCOME`
- `CASE-BASED LEARNING` → `INTERVENTION`
- `CONTROL GROUP STUDENTS` → `COMPARATOR`
- `HYPOTHESIS TESTING` → `MECHANISM`
- `JUNIOR DOCTORS` → `LEARNER_POPULATION`
- `TRAINING PHASE` → `SETTING_CONTEXT`
- `BIASED ECG PRESENTATION` → `COGNITIVE_STATE`
- `NO INSTRUCTION CONDITION` → `COMPARATOR`
- `DOCTOR` → `LEARNER_POPULATION`

### Remaining blank/unknown entity types (requires prompt/ontology iteration)

- `SPONTANEOUS REASONING CONDITION`
- `CONTEXT`
- `LARGER EXPERIMENTAL GROUPS`

### Notes

- Note: claim schema noise is handled in claims_fixed.parquet; this script only normalizes entities/relationships.
