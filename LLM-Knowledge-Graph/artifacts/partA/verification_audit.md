## Part A (Education) — Verification Audit (quality gates)

- output dir: `D:/Universal-Web-Scraping-System-high-level-update/Universal-Web-Scraping-System-high-level-update-main/LLM-Knowledge-Graph/graphrag-project/output_partA_subset5`

### Artifact presence

- **documents.parquet**: YES
- **text_units.parquet**: YES
- **entities.parquet**: YES
- **relationships.parquet**: YES
- **communities.parquet**: YES
- **community_reports.parquet**: YES
- **claims.parquet**: NO
- **covariates.parquet**: YES

### Entity quality (anti-noise)

- entities rows: **370**

**Entity types (counts)**

| type               |   count |
|:-------------------|--------:|
| OUTCOME            |      79 |
| INTERVENTION       |      48 |
| SETTING_CONTEXT    |      46 |
| MECHANISM          |      45 |
| ASSESSMENT_MEASURE |      38 |
| STUDY_DESIGN       |      24 |
| TASK_CASE          |      21 |
| LEARNER_CONTEXT    |      21 |
| COGNITIVE_STATE    |      14 |
| LEARNER_POPULATION |      11 |
|                    |       8 |
| CLINICAL_DOMAIN    |       7 |
| MOTIVATION_AFFECT  |       6 |
| CONTEXT            |       1 |
| COMPARATOR         |       1 |

- blacklisted-looking entity titles (heuristic): **0 / 370**

**Top entities by frequency (spot-check for bibliographic noise)**

| title                             | type               |   frequency |   degree |
|:----------------------------------|:-------------------|------------:|---------:|
| DIAGNOSTIC ACCURACY               | OUTCOME            |           9 |       61 |
| LEARNING ENVIRONMENT              | SETTING_CONTEXT    |           4 |        0 |
| LEARNING OUTCOMES                 | OUTCOME            |           4 |        5 |
| COGNITIVE LOAD                    | COGNITIVE_STATE    |           4 |        2 |
| DIAGNOSTIC KNOWLEDGE              | OUTCOME            |           3 |       16 |
| CONTRASTIVE LEARNING              | INTERVENTION       |           3 |       10 |
| ANALYTIC REASONING                | MECHANISM          |           3 |        6 |
| UNDERGRADUATE PSYCHOLOGY STUDENTS | LEARNER_POPULATION |           3 |       10 |
| MEDICAL STUDENTS                  | LEARNER_POPULATION |           3 |        7 |
| ERRONEOUS EXAMPLES                | INTERVENTION       |           3 |        8 |
| ELABORATED FEEDBACK               | INTERVENTION       |           3 |        9 |
| ECG DIAGNOSIS                     | TASK_CASE          |           3 |        0 |
| FEEDBACK                          | ASSESSMENT_MEASURE |           3 |        2 |
| LEARNING CONTEXT                  | SETTING_CONTEXT    |           2 |        0 |
| LEARNING EFFECTIVENESS            | OUTCOME            |           2 |        0 |
| LEARNING                          | OUTCOME            |           2 |        3 |
| LEARNING ENVIRONMENT EVALUATION   | ASSESSMENT_MEASURE |           2 |        0 |
| EFFECTIVENESS                     | OUTCOME            |           2 |        0 |
| EXPLICIT INSTRUCTIONS             | INTERVENTION       |           2 |        2 |
| LEARNING OUTCOMES ASSESSMENT      | ASSESSMENT_MEASURE |           2 |        0 |
| REASONING STRATEGY                | MECHANISM          |           2 |        2 |
| LEARNING OUTCOMES MEASUREMENT     | ASSESSMENT_MEASURE |           2 |        0 |
| LEARNING EFFECTS                  | OUTCOME            |           2 |        0 |
| STUDENTS                          | LEARNER_POPULATION |           2 |        1 |
| NOVICE DIAGNOSTICIANS             | LEARNER_POPULATION |           2 |        3 |

### Claim quality (traceability + CMO)

- source: **claims_fixed.parquet**
- claims rows: **325**
- claims with `[PAGE N]` marker in source_text: **311 / 325**

**Claim completeness (heuristic)**

- missing subject: **0 / 325**
- missing object: **0 / 325**
- missing evidence span (source_text/text): **0 / 325**

**Claim types (counts)**

| type                  |   count |
|:----------------------|--------:|
| OUTCOME_MEASUREMENT   |     262 |
| MECHANISM_EXPLANATION |      24 |
| INTERVENTION_EFFECT   |      23 |
| CONTEXT_MODERATOR     |       8 |
| OUTCOME               |       4 |
| INTERVENTION          |       2 |
| COMPARATOR            |       2 |

**Sample claims (spot-check)**

| subject_id                        | object_id                         | type                  | covariate_type   | status   | description                                                                                                                                                                                                      | source_text                                                                                                                                                                                                                            | text_unit_id                                                                                                                     |
|:----------------------------------|:----------------------------------|:----------------------|:-----------------|:---------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------|
| NAÏVE STUDENTS                    | DIAGNOSTIC ACCURACY               | OUTCOME_MEASUREMENT   | claim            | TRUE     | Greater diagnostic accuracy was achieved following both contrastive learning and instructions to use a combined reasoning strategy.                                                                              | "Greater diagnostic accuracy was achieved following both contrastive learning and instructions to use a combined reasoning strategy relative to the control conditions." [PAGE 1]                                                      | 34d7c29642ce28a193973eeb16a1b98b1e92531821320de634dc6fb26b208f577b596c5265bc192af8451c523e9dbe4688bd68cd86dbddc5ca49f55289d20a82 |
| COMBINED REASONING STRATEGY       | DIAGNOSTIC ACCURACY               | INTERVENTION_EFFECT   | claim            | TRUE     | Instructions to use a combined reasoning strategy improved diagnostic accuracy compared to control conditions.                                                                                                   | "The effects were observed immediately after learning and following a 1-week delay." [PAGE 1]                                                                                                                                          | 34d7c29642ce28a193973eeb16a1b98b1e92531821320de634dc6fb26b208f577b596c5265bc192af8451c523e9dbe4688bd68cd86dbddc5ca49f55289d20a82 |
| CONTRASTIVE LEARNING              | DIAGNOSTIC ACCURACY               | INTERVENTION_EFFECT   | claim            | TRUE     | Contrastive learning improved diagnostic accuracy compared to standard learning methods.                                                                                                                         | "Greater diagnostic accuracy was achieved following both contrastive learning and instructions to use a combined reasoning strategy relative to the control conditions." [PAGE 1]                                                      | 34d7c29642ce28a193973eeb16a1b98b1e92531821320de634dc6fb26b208f577b596c5265bc192af8451c523e9dbe4688bd68cd86dbddc5ca49f55289d20a82 |
| INSTRUCTIONS                      | MULTIFACETED DIAGNOSTIC REASONING | INTERVENTION          | claim            | TRUE     | Explicit instructions to adopt multifaceted diagnostic reasoning strategies were provided to students.                                                                                                           | "This study assesses the extent to which students spontaneously adopt a combined approach and compares its benefits with those experienced with a contrastive learning strategy." [PAGE 1]                                             | 34d7c29642ce28a193973eeb16a1b98b1e92531821320de634dc6fb26b208f577b596c5265bc192af8451c523e9dbe4688bd68cd86dbddc5ca49f55289d20a82 |
| MULTIFACETED DIAGNOSTIC REASONING | DIAGNOSTIC ACCURACY               | MECHANISM_EXPLANATION | claim            | TRUE     | Utilizing multifaceted diagnostic reasoning strategies enhances diagnostic accuracy in medical education.                                                                                                        | "The results emphasise the importance of explicitly empowering students to utilise multiple diagnostic strategies." [PAGE 1]                                                                                                           | 34d7c29642ce28a193973eeb16a1b98b1e92531821320de634dc6fb26b208f577b596c5265bc192af8451c523e9dbe4688bd68cd86dbddc5ca49f55289d20a82 |
| CONTEXT SPECIFICITY               | DIAGNOSTIC ACCURACY               | CONTEXT_MODERATOR     | claim            | TRUE     | Context specificity influences the effectiveness of diagnostic reasoning strategies in medical education.                                                                                                        | "Multiple studies have supported this contention, as does the overwhelmingly robust phenomenon of context specificity." [PAGE 2]                                                                                                       | 34d7c29642ce28a193973eeb16a1b98b1e92531821320de634dc6fb26b208f577b596c5265bc192af8451c523e9dbe4688bd68cd86dbddc5ca49f55289d20a82 |
| ANALOGICAL TRANSFER               | DIAGNOSTIC ACCURACY               | OUTCOME_MEASUREMENT   | claim            | TRUE     | The study compares the benefits of a combined reasoning strategy with those of analogical transfer in enhancing diagnostic accuracy.                                                                             | "The second objective was to compare the magnitude of benefit of an instruction to use a combined reasoning strategy with that of another strategy that has proven successful in increasing the rate of analogical transfer." [PAGE 2] | 34d7c29642ce28a193973eeb16a1b98b1e92531821320de634dc6fb26b208f577b596c5265bc192af8451c523e9dbe4688bd68cd86dbddc5ca49f55289d20a82 |
| INSTRUCTION                       | SPONTANEOUS DIAGNOSTIC STRATEGY   | MECHANISM_EXPLANATION | claim            | TRUE     | Explicit instruction to utilize a combined strategy is necessary to improve diagnostic performance compared to spontaneous strategies.                                                                           | "To truly determine whether or not an explicit instruction to utilise a combined strategy is beneﬁcial requires an additional control group." [PAGE 2]                                                                                 | 34d7c29642ce28a193973eeb16a1b98b1e92531821320de634dc6fb26b208f577b596c5265bc192af8451c523e9dbe4688bd68cd86dbddc5ca49f55289d20a82 |
| COMBINED STRATEGY                 | DIAGNOSTIC PERFORMANCE            | OUTCOME_MEASUREMENT   | claim            | TRUE     | Promoting a combined strategy improves diagnostic performance compared to isolated strategies.                                                                                                                   | "The need to assess such a comparison provided the first objective of this study." [PAGE 2]                                                                                                                                            | 34d7c29642ce28a193973eeb16a1b98b1e92531821320de634dc6fb26b208f577b596c5265bc192af8451c523e9dbe4688bd68cd86dbddc5ca49f55289d20a82 |
| UNDERGRADUATE PSYCHOLOGY STUDENTS | CONTRASTIVE LEARNING              | CONTEXT_MODERATOR     | claim            | TRUE     | Participants' prior experience with ECGs was nonexistent, providing a baseline for evaluating the intervention's effectiveness. CMO[C=UNDERGRADUATE PSYCHOLOGY STUDENTS; I=CONTRASTIVE LEARNING; M=NONE; O=NONE] | Participants in the contrastive learning condition performed significantly better than those in the non-contrastive learning condition [PAGE 5].                                                                                       | bbe2bdbff40fff445931fe3b697bd72e7d026890c6ba1619dbcf9af3a44c81a5bcc4a56fd4de2cd360db77df557653771aa3b70de5d042ca9ab51d37d8dca8db |
| CONTRASTIVE LEARNING              | DIAGNOSTIC ACCURACY               | INTERVENTION_EFFECT   | claim            | TRUE     | The contrastive learning approach significantly improved diagnostic accuracy compared to non-contrastive learning. CMO[C=NONE; I=CONTRASTIVE LEARNING; M=NONE; O=DIAGNOSTIC ACCURACY]                            | Participants in the contrastive learning condition performed significantly better than those in the non-contrastive learning condition [PAGE 5].                                                                                       | bbe2bdbff40fff445931fe3b697bd72e7d026890c6ba1619dbcf9af3a44c81a5bcc4a56fd4de2cd360db77df557653771aa3b70de5d042ca9ab51d37d8dca8db |
| COMBINED REASONING                | DIAGNOSTIC ACCURACY               | INTERVENTION_EFFECT   | claim            | TRUE     | The combined reasoning condition led to significantly higher diagnostic accuracy compared to the spontaneous reasoning condition. CMO[C=NONE; I=COMBINED REASONING; M=NONE; O=DIAGNOSTIC ACCURACY]               | Those in the combined reasoning condition significantly outperformed those in the spontaneous reasoning condition [PAGE 5].                                                                                                            | bbe2bdbff40fff445931fe3b697bd72e7d026890c6ba1619dbcf9af3a44c81a5bcc4a56fd4de2cd360db77df557653771aa3b70de5d042ca9ab51d37d8dca8db |

### Community structure

- communities rows: **9**

### Community report quality (principle-level heuristics)

- community_reports rows: **9**
- generic/too-short titles (heuristic): **0 / 9**

**Community report headers (sample)**

|   community |   level | title                                                            |   rank |   size |
|------------:|--------:|:-----------------------------------------------------------------|-------:|-------:|
|           0 |       0 | Diagnostic Learning Strategies Community                         |    8   |     45 |
|           1 |       0 | Novice Diagnosticians and Clinical Reasoning                     |    6.5 |      5 |
|           2 |       0 | Combined Reasoning in Diagnostic Accuracy                        |    7.5 |      2 |
|           3 |       0 | Combined Reasoning Strategy in ECG Diagnosis                     |    7.5 |      3 |
|           4 |       0 | Diagnostic Education Community                                   |    8   |      6 |
|           5 |       0 | Diagnostic Improvement Community: Reasoning Strategy and Novices |    7.5 |      3 |
|           6 |       0 | ECG Diagnostic Study Community                                   |    7.5 |      5 |
|           7 |       0 | Diagnostic Accuracy in ECG Assessment                            |    7.5 |      3 |
|           8 |       0 | ECG Diagnostic Instruction Community                             |    7.5 |      4 |

### What to verify against Richmond (next)

- **Search/screening alignment**: overlap with Richmond-28 + explain mismatches.
- **CMO fidelity**: do extracted claims support C→M→O patterns?
- **Concept alignment**: map community titles ↔ Richmond mechanisms/programme theory components.
- **Cross-study synthesis**: identify dominant patterns + contradictions with citations/spans.
