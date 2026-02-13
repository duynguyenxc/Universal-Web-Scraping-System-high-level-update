## Part A (Education) — Verification Audit (quality gates)

- output dir: `D:/Universal-Web-Scraping-System-high-level-update/Universal-Web-Scraping-System-high-level-update-main/LLM-Knowledge-Graph/graphrag-project/output_partA_subset5_v4_noclaims`

### Artifact presence

- **documents.parquet**: YES
- **text_units.parquet**: YES
- **entities.parquet**: YES
- **relationships.parquet**: YES
- **communities.parquet**: YES
- **community_reports.parquet**: YES
- **claims.parquet**: NO
- **covariates.parquet**: NO

### Entity quality (anti-noise)

- entities rows: **170**

**Entity types (counts)**

| type               |   count |
|:-------------------|--------:|
| INTERVENTION       |      40 |
| MECHANISM          |      34 |
| CONTEXT            |      25 |
| OUTCOME            |      24 |
|                    |      18 |
| COMPARATOR         |       9 |
| LEARNER_POPULATION |       6 |
| COGNITIVE_STATE    |       5 |
| LEARNER_CONTEXT    |       4 |
| CLINICAL_DOMAIN    |       3 |
| STUDY_DESIGN       |       1 |
| SETTING_CONTEXT    |       1 |

- blacklisted-looking entity titles (heuristic): **1 / 170**

**Top entities by frequency (spot-check for bibliographic noise)**

| title                              | type               |   frequency |   degree |
|:-----------------------------------|:-------------------|------------:|---------:|
| DIAGNOSTIC ACCURACY                | OUTCOME            |          11 |       44 |
| CLINICAL REASONING                 | MECHANISM          |           7 |       22 |
| DIAGNOSTIC KNOWLEDGE               | OUTCOME            |           6 |       20 |
| CONTRASTIVE LEARNING               | INTERVENTION       |           4 |        5 |
| NON-CONTRASTIVE LEARNING           | COMPARATOR         |           3 |        0 |
| MEDICAL STUDENTS                   | LEARNER_POPULATION |           3 |        0 |
| ELABORATED FEEDBACK                | INTERVENTION       |           3 |        3 |
| ERRONEOUS EXAMPLES                 | INTERVENTION       |           3 |        3 |
| NON-ANALYTIC REASONING             | MECHANISM          |           3 |        3 |
| KCR FEEDBACK                       | COMPARATOR         |           2 |        1 |
| SPONTANEOUS REASONING CONDITION    | COMPARATOR         |           2 |        1 |
| CONTRASTIVE LEARNING CONDITION     | INTERVENTION       |           2 |        2 |
| NON-CONTRASTIVE LEARNING CONDITION | COMPARATOR         |           2 |        1 |
| WORKED EXAMPLES                    | INTERVENTION       |           2 |        1 |
| NO REASONING INSTRUCTION           | COMPARATOR         |           2 |        1 |
| NOVICE DIAGNOSTICIANS              | LEARNER_POPULATION |           2 |        0 |
| COMBINED REASONING INSTRUCTION     | INTERVENTION       |           2 |        4 |
| CONCEPTUAL KNOWLEDGE               | OUTCOME            |           2 |        2 |
| EXPLICIT INSTRUCTION               |                    |           2 |        2 |
| ANALYTIC REASONING                 |                    |           2 |        3 |
| FEEDBACK                           | INTERVENTION       |           2 |        1 |
| CASE-BASED WORKED EXAMPLE APPROACH | INTERVENTION       |           2 |        3 |
| COMBINED REASONING CONDITION       | INTERVENTION       |           2 |        2 |
| PRIOR KNOWLEDGE                    | LEARNER_CONTEXT    |           2 |        1 |
| DIAGNOSTIC ERRORS                  | OUTCOME            |           2 |       11 |

### Community structure

- communities rows: **13**

### Community report quality (principle-level heuristics)

- community_reports rows: **13**
- generic/too-short titles (heuristic): **0 / 13**

**Community report headers (sample)**

|   community |   level | title                                                              |   rank |   size |
|------------:|--------:|:-------------------------------------------------------------------|-------:|-------:|
|           9 |       1 | Analytic Reasoning and Diagnostic Processes Community              |    7.5 |      4 |
|          10 |       1 | Diagnostic Accuracy in ECG Interpretation                          |    7.5 |     30 |
|          11 |       1 | Non-Analytic Reasoning and Diagnostic Hypothesis Manipulation      |    6   |      2 |
|          12 |       1 | Multifaceted Diagnostic Reasoning in Medical Education             |    7.5 |      2 |
|           0 |       0 | Diagnostic Errors and Decision-Making Factors                      |    8   |     11 |
|           1 |       0 | Clinical Reasoning and ECG Interpretation Community                |    8   |     22 |
|           2 |       0 | Diagnostic Accuracy and Reasoning Strategies in ECG Interpretation |    7.5 |     38 |
|           3 |       0 | Diagnostic Reasoning Strategies and Their Impact                   |    7.5 |      3 |
|           4 |       0 | Combined Reasoning Instruction and Diagnostic Accuracy             |    7.5 |      5 |
|           5 |       0 | Contrastive Learning and Diagnostic Accuracy Community             |    8   |      5 |
|           6 |       0 | Combined Approach to Clinical Reasoning and Diagnostic Accuracy    |    7   |      2 |
|           7 |       0 | Diagnostic Education Community                                     |    7.5 |      4 |
|           8 |       0 | Non-Analytic Processes and Prior Experience                        |    6   |      2 |

### What to verify against Richmond (next)

- **Search/screening alignment**: overlap with Richmond-28 + explain mismatches.
- **CMO fidelity**: do extracted claims support C→M→O patterns?
- **Concept alignment**: map community titles ↔ Richmond mechanisms/programme theory components.
- **Cross-study synthesis**: identify dominant patterns + contradictions with citations/spans.
