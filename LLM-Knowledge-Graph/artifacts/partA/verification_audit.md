## Part A (Education) — Verification Audit (quality gates)

- output dir: `D:/Universal-Web-Scraping-System-high-level-update/Universal-Web-Scraping-System-high-level-update-main/LLM-Knowledge-Graph/graphrag-project/output_partA_subset5_v2`

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

- entities rows: **828**

**Entity types (counts)**

| type               |   count |
|:-------------------|--------:|
| ASSESSMENT_MEASURE |     230 |
| OUTCOME            |     146 |
| INTERVENTION       |     131 |
| MECHANISM          |     117 |
| STUDY_DESIGN       |      54 |
| SETTING_CONTEXT    |      37 |
| COGNITIVE_STATE    |      31 |
| TASK_CASE          |      22 |
| LEARNER_POPULATION |      17 |
| MOTIVATION_AFFECT  |      14 |
| LEARNER_CONTEXT    |      10 |
| CLINICAL_DOMAIN    |      10 |
|                    |       6 |
| COMPARATOR         |       2 |
| CONTEXT            |       1 |

- blacklisted-looking entity titles (heuristic): **0 / 828**

**Top entities by frequency (spot-check for bibliographic noise)**

| title                                       | type               |   frequency |   degree |
|:--------------------------------------------|:-------------------|------------:|---------:|
| DIAGNOSTIC ACCURACY                         | OUTCOME            |           8 |       46 |
| LEARNING OUTCOMES                           | OUTCOME            |           6 |        0 |
| COGNITIVE LOAD                              | COGNITIVE_STATE    |           5 |       21 |
| LEARNING ENVIRONMENT                        | SETTING_CONTEXT    |           4 |        0 |
| COGNITIVE STRATEGIES                        | MECHANISM          |           4 |        0 |
| NOVICE DIAGNOSTICIANS                       | LEARNER_POPULATION |           3 |       11 |
| COGNITIVE LOAD MANAGEMENT                   | MECHANISM          |           3 |        0 |
| DIAGNOSTIC ERRORS                           | OUTCOME            |           3 |        0 |
| STUDY 2                                     | STUDY_DESIGN       |           3 |        4 |
| DIAGNOSTIC PERFORMANCE                      | OUTCOME            |           3 |        0 |
| CLINICAL REASONING                          | MECHANISM          |           3 |        6 |
| STUDY 1                                     | STUDY_DESIGN       |           3 |        4 |
| COGNITIVE REFLECTION                        | MECHANISM          |           3 |        0 |
| MEDICAL STUDENTS                            | LEARNER_POPULATION |           3 |       12 |
| LEARNING OUTCOMES ASSESSMENT                | ASSESSMENT_MEASURE |           3 |        0 |
| CONTRASTIVE LEARNING                        | INTERVENTION       |           3 |        9 |
| INSTRUCTIONAL STRATEGY                      | INTERVENTION       |           3 |        0 |
| LEARNING STRATEGIES                         | MECHANISM          |           3 |        0 |
| BIAS MITIGATION                             | MECHANISM          |           2 |        0 |
| COGNITIVE STRATEGY EFFECTIVENESS ASSESSMENT | ASSESSMENT_MEASURE |           2 |        0 |
| CATEGORICAL PERFORMANCE                     | OUTCOME            |           2 |        0 |
| CATEGORICAL ANALYSIS                        | MECHANISM          |           2 |        0 |
| INSTRUCTIONAL EFFECTS                       | OUTCOME            |           2 |        0 |
| LEARNING EFFECTIVENESS                      | OUTCOME            |           2 |        0 |
| EFFECTIVENESS OF INSTRUCTION                | OUTCOME            |           2 |        0 |

### Claim quality (traceability + CMO)

- source: **claims_fixed.parquet**
- claims rows: **464**
- claims with `[PAGE N]` marker in source_text: **463 / 464**

**Claim completeness (heuristic)**

- missing subject: **0 / 464**
- missing object: **0 / 464**
- missing evidence span (source_text/text): **0 / 464**

**Claim types (counts)**

| type                  |   count |
|:----------------------|--------:|
| INTERVENTION_EFFECT   |     191 |
| OUTCOME_MEASUREMENT   |     121 |
| MECHANISM_EXPLANATION |      88 |
| CONTEXT_MODERATOR     |      64 |

**Sample claims (spot-check)**

| subject_id                  | object_id                                    | type                  | covariate_type   | status   | description                                                                                                                                                            | source_text                                                                                                                                                                                                                                                  | text_unit_id                                                                                                                     |
|:----------------------------|:---------------------------------------------|:----------------------|:-----------------|:---------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------|
| NAÏVE STUDENTS              | DIAGNOSTIC ACCURACY                          | INTERVENTION_EFFECT   | claim            | TRUE     | Greater diagnostic accuracy was achieved following both contrastive learning and instructions to use a combined reasoning strategy relative to the control conditions. | "Greater diagnostic accuracy was achieved following both contrastive learning and instructions to use a combined reasoning strategy relative to the control conditions." [PAGE 1]                                                                            | 34d7c29642ce28a193973eeb16a1b98b1e92531821320de634dc6fb26b208f577b596c5265bc192af8451c523e9dbe4688bd68cd86dbddc5ca49f55289d20a82 |
| COMBINED REASONING STRATEGY | DIAGNOSTIC ACCURACY                          | MECHANISM_EXPLANATION | claim            | TRUE     | Explicitly empowering students to utilise multiple diagnostic strategies, including non-analytic approaches, improves diagnostic accuracy.                             | "The results emphasise the importance of explicitly empowering students to utilise multiple diagnostic strategies, including non-analytic approaches." [PAGE 1]                                                                                              | 34d7c29642ce28a193973eeb16a1b98b1e92531821320de634dc6fb26b208f577b596c5265bc192af8451c523e9dbe4688bd68cd86dbddc5ca49f55289d20a82 |
| CONTRASTIVE LEARNING        | ANALOGICAL TRANSFER                          | INTERVENTION_EFFECT   | claim            | TRUE     | The study compares the benefits of a combined reasoning strategy with those experienced with a contrastive learning strategy known to enhance analogical transfer.     | "The second objective was to compare the magnitude of beneﬁt of an instruction to use a combined reasoning strategy with that of another strategy that has proven successful in increasing the rate of analogical transfer in non-medical domains." [PAGE 2] | 34d7c29642ce28a193973eeb16a1b98b1e92531821320de634dc6fb26b208f577b596c5265bc192af8451c523e9dbe4688bd68cd86dbddc5ca49f55289d20a82 |
| INSTRUCTION                 | COMBINED REASONING STRATEGY                  | MECHANISM_EXPLANATION | claim            | TRUE     | Participants given a combined instruction demonstrated better diagnostic accuracy compared to those with non-combined instructions.                                    | "When tested, participants given either set of non-combined instructions demonstrated equal diagnostic accuracy, but their performance was poor compared with that of participants who had been given a combined instruction." [PAGE 2]                      | 34d7c29642ce28a193973eeb16a1b98b1e92531821320de634dc6fb26b208f577b596c5265bc192af8451c523e9dbe4688bd68cd86dbddc5ca49f55289d20a82 |
| NAÏVE STUDENTS              | MULTIFACETED DIAGNOSTIC REASONING STRATEGIES | INTERVENTION_EFFECT   | claim            | TRUE     | Teaching novices to utilise analytic and non-analytic reasoning strategies yields higher diagnostic accuracy than teaching either in isolation.                        | "Recent studies have shown that teaching novices to utilise analytic and non-analytic reasoning strategies yields higher diagnostic accuracy than teaching either in isolation." [PAGE 1]                                                                    | 34d7c29642ce28a193973eeb16a1b98b1e92531821320de634dc6fb26b208f577b596c5265bc192af8451c523e9dbe4688bd68cd86dbddc5ca49f55289d20a82 |
| CONTEXT SPECIFICITY         | DIAGNOSTIC DECISION MAKING                   | CONTEXT_MODERATOR     | claim            | TRUE     | The study highlights the importance of context specificity in the effectiveness of diagnostic decision-making strategies.                                              | "Multiple studies have supported this contention, as does the overwhelmingly robust phenomenon of context specificity." [PAGE 2]                                                                                                                             | 34d7c29642ce28a193973eeb16a1b98b1e92531821320de634dc6fb26b208f577b596c5265bc192af8451c523e9dbe4688bd68cd86dbddc5ca49f55289d20a82 |
| INSTRUCTION                 | DIAGNOSTIC STRATEGY                          | MECHANISM_EXPLANATION | claim            | TRUE     | Explicit instructions to utilise a combined strategy improve performance in diagnostic reasoning tasks.                                                                | "To truly determine whether or not an explicit instruction to utilise a combined strategy is beneﬁcial requires an additional control group." [PAGE 2]                                                                                                       | 34d7c29642ce28a193973eeb16a1b98b1e92531821320de634dc6fb26b208f577b596c5265bc192af8451c523e9dbe4688bd68cd86dbddc5ca49f55289d20a82 |
| COMBINED STRATEGY           | DIAGNOSTIC PERFORMANCE                       | OUTCOME_MEASUREMENT   | claim            | TRUE     | The study measures the impact of a combined strategy on diagnostic performance through accuracy assessments.                                                           | "The need to assess such a comparison provided the first objective of this study." [PAGE 2]                                                                                                                                                                  | 34d7c29642ce28a193973eeb16a1b98b1e92531821320de634dc6fb26b208f577b596c5265bc192af8451c523e9dbe4688bd68cd86dbddc5ca49f55289d20a82 |
| ANALOGICAL TRANSFER         | PROBLEM SOLVING                              | MECHANISM_EXPLANATION | claim            | TRUE     | Analogical transfer enhances problem-solving abilities by applying learned solution principles to new problems.                                                        | "Analogical transfer is defined by psychologists as successful problem solving through the use of solution principles that were learned in response to problems encountered previously." [PAGE 2]                                                            | 34d7c29642ce28a193973eeb16a1b98b1e92531821320de634dc6fb26b208f577b596c5265bc192af8451c523e9dbe4688bd68cd86dbddc5ca49f55289d20a82 |
| MULTIFACETED MODEL          | DIAGNOSTIC EXPERTISE                         | CONTEXT_MODERATOR     | claim            | TRUE     | The study discusses the multifaceted model of clinical reasoning as a means to enhance diagnostic expertise in medical education.                                      | "Building on the work of Norman et al., Ark et al. tested the efﬁcacy of a variety of instructions provided to novice readers of electrocardiograms." [PAGE 2]                                                                                               | 34d7c29642ce28a193973eeb16a1b98b1e92531821320de634dc6fb26b208f577b596c5265bc192af8451c523e9dbe4688bd68cd86dbddc5ca49f55289d20a82 |
| ECG DIAGNOSIS               | COMBINED REASONING                           | INTERVENTION_EFFECT   | claim            | TRUE     | Instructions to use a combined reasoning approach lead to better diagnostic performance compared to analytic instructions.                                             | "instructions to be both feature-oriented and to trust similarity-based reasoning strategies... have led to significantly better diagnostic performance than alternative sets of instructions." [PAGE 6]                                                     | d7d6308c3b8432d7e69d37824f3e96fbae9bb6c9a1a297c5cea4e716d0dabd53d99d07fb39dc26eb2f1b01389677de656bfe7d183b84f895fc69c6d5a099e0c3 |
| CONTRASTIVE LEARNING        | DIAGNOSTIC ACCURACY                          | INTERVENTION_EFFECT   | claim            | TRUE     | Instructions for contrastive learning improve diagnostic accuracy compared to non-contrastive learning.                                                                | "learners who were instructed to compare and contrast categories... achieved greater diagnostic accuracy than those who were simply told to learn the relationship between the features and disorders." [PAGE 6]                                             | d7d6308c3b8432d7e69d37824f3e96fbae9bb6c9a1a297c5cea4e716d0dabd53d99d07fb39dc26eb2f1b01389677de656bfe7d183b84f895fc69c6d5a099e0c3 |

### Community structure

- communities rows: **10**

### Community report quality (principle-level heuristics)

- community_reports rows: **10**
- generic/too-short titles (heuristic): **0 / 10**

**Community report headers (sample)**

|   community |   level | title                                                                    |   rank |   size |
|------------:|--------:|:-------------------------------------------------------------------------|-------:|-------:|
|           8 |       1 | Diagnostic Accuracy in ECG Interpretation                                |    7.5 |     18 |
|           9 |       1 | Diagnostic Accuracy and Reasoning Strategies in ECG Interpretation       |    7.5 |      7 |
|           0 |       0 | Cognitive Load and Diagnostic Knowledge Community                        |    7.5 |     11 |
|           1 |       0 | Diagnostic Reasoning Strategies in Medical Education                     |    7.5 |     13 |
|           2 |       0 | ECG Diagnosis Community Insights                                         |    7.5 |      9 |
|           3 |       0 | Analytic Tendencies and Diagnostic Accuracy                              |    7.5 |      2 |
|           4 |       0 | Medical Education Community: Erroneous Examples and Diagnostic Knowledge |    8   |      8 |
|           5 |       0 | Diagnostic Accuracy and ECG Interpretation Community                     |    7.5 |     25 |
|           6 |       0 | Non-Analytic Tendencies and Diagnostic Accuracy                          |    6.5 |      2 |
|           7 |       0 | Medical Education Community: Reasoning Strategy and Instruction          |    7.5 |      4 |

### What to verify against Richmond (next)

- **Search/screening alignment**: overlap with Richmond-28 + explain mismatches.
- **CMO fidelity**: do extracted claims support C→M→O patterns?
- **Concept alignment**: map community titles ↔ Richmond mechanisms/programme theory components.
- **Cross-study synthesis**: identify dominant patterns + contradictions with citations/spans.
