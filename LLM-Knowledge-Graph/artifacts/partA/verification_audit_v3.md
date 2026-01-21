## Part A (Education) — Verification Audit (quality gates)

- output dir: `D:/Universal-Web-Scraping-System-high-level-update/Universal-Web-Scraping-System-high-level-update-main/LLM-Knowledge-Graph/graphrag-project/output_partA_subset5_v3`

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

- entities rows: **216**

**Entity types (counts)**

| type               |   count |
|:-------------------|--------:|
| INTERVENTION       |      42 |
| MECHANISM          |      38 |
| SETTING_CONTEXT    |      27 |
| OUTCOME            |      18 |
|                    |      15 |
| LEARNER_CONTEXT    |      14 |
| CLINICAL_DOMAIN    |      14 |
| LEARNER_POPULATION |      13 |
| COGNITIVE_STATE    |      10 |
| COMPARATOR         |       9 |
| STUDY_DESIGN       |       9 |
| COGNITIVE STATE    |       4 |
| CONTEXT            |       2 |
| MOTIVATION_AFFECT  |       1 |

- blacklisted-looking entity titles (heuristic): **0 / 216**

**Top entities by frequency (spot-check for bibliographic noise)**

| title                               | type               |   frequency |   degree |
|:------------------------------------|:-------------------|------------:|---------:|
| DIAGNOSTIC ACCURACY                 | OUTCOME            |          10 |       62 |
| CONTRASTIVE LEARNING                | INTERVENTION       |           5 |        3 |
| DIAGNOSTIC KNOWLEDGE                | OUTCOME            |           5 |       30 |
| ELABORATED FEEDBACK                 | INTERVENTION       |           5 |        3 |
| FEEDBACK                            | INTERVENTION       |           5 |        5 |
| ECG DIAGNOSIS                       | CLINICAL_DOMAIN    |           4 |        7 |
| ERRONEOUS EXAMPLES                  | INTERVENTION       |           4 |        4 |
| UNDERGRADUATE PSYCHOLOGY STUDENTS   | LEARNER_POPULATION |           4 |        4 |
| ANALYTIC REASONING                  | MECHANISM          |           3 |        5 |
| NON-ANALYTIC REASONING              | MECHANISM          |           3 |        4 |
| MEDICAL STUDENTS                    | LEARNER_POPULATION |           3 |        3 |
| COMBINED REASONING INSTRUCTIONS     | INTERVENTION       |           3 |        7 |
| ELECTROCARDIOGRAM DIAGNOSIS         | CLINICAL_DOMAIN    |           2 |        1 |
| COMBINED REASONING APPROACH         | INTERVENTION       |           2 |        4 |
| SPONTANEOUS REASONING               | INTERVENTION       |           2 |        1 |
| COGNITIVE LOAD                      | COGNITIVE_STATE    |           2 |        0 |
| NON-CONTRASTIVE LEARNING            | COMPARATOR         |           2 |        1 |
| MIXED DESIGN ANOVA                  | STUDY_DESIGN       |           2 |        1 |
| PATTERN RECOGNITION                 | MECHANISM          |           2 |        2 |
| TEST PHASE                          | SETTING_CONTEXT    |           2 |        2 |
| COMPUTER-BASED LEARNING ENVIRONMENT | SETTING_CONTEXT    |           2 |        3 |
| PRACTICE PHASE                      | SETTING_CONTEXT    |           2 |        2 |
| WORKED EXAMPLES                     | INTERVENTION       |           2 |        2 |
| COMBINED REASONING STRATEGY         | INTERVENTION       |           2 |        2 |
| CONTROL GROUP                       | COMPARATOR         |           2 |        2 |

### Claim quality (traceability + CMO)

- source: **claims_fixed.parquet**
- claims rows: **792**
- claims with `[PAGE N]` marker in source_text: **768 / 792**

**Claim completeness (heuristic)**

- missing subject: **0 / 792**
- missing object: **0 / 792**
- missing evidence span (source_text/text): **13 / 792**

**Claim types (counts)**

| type                  |   count |
|:----------------------|--------:|
| INTERVENTION_EFFECT   |     351 |
| CONTEXT_MODERATOR     |     233 |
| MECHANISM_EXPLANATION |     132 |
| OUTCOME_MEASUREMENT   |      66 |
| >DIAGNOSTIC ACCURACY< |       9 |
| <CONTEXT_MODERATOR    |       1 |

**Sample claims (spot-check)**

| subject_id                    | object_id                          | type                  | covariate_type   | status   | description                                                                                                                                                                                                                        | source_text                                                                                                                                                                                                                   | text_unit_id                                                                                                                     |
|:------------------------------|:-----------------------------------|:----------------------|:-----------------|:---------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------|
| NAÏVE STUDENTS                | DIAGNOSTIC ACCURACY                | INTERVENTION_EFFECT   | claim            | TRUE     | Training naı̈ve students to utilize a combined approach to diagnostic reasoning leads to greater diagnostic accuracy compared to control conditions. CMO[C=NONE; I=training naı̈ve students; M=NONE; O=greater diagnostic accuracy.] | Greater diagnostic accuracy was achieved following both contrastive learning and instructions to use a combined reasoning strategy relative to the control conditions. [PAGE 1]                                               | 7b46a2f96038bf5ba0d86c85d6de2a0df0f4b34de431fb6c7a22e72903e22e8e3431a5c81b9f9d1393ef7f497301375f9cf825c8682a1d29b4479486e0862d1e |
| COMBINED REASONING STRATEGY   | DIAGNOSTIC ACCURACY                | INTERVENTION_EFFECT   | claim            | TRUE     | Instructions to use a combined reasoning strategy improve diagnostic accuracy in medical education. CMO[C=NONE; I=instructions to use a combined reasoning strategy; M=NONE; O=improved diagnostic accuracy.]                      | Greater diagnostic accuracy was achieved following both contrastive learning and instructions to use a combined reasoning strategy relative to the control conditions. [PAGE 1]                                               | 7b46a2f96038bf5ba0d86c85d6de2a0df0f4b34de431fb6c7a22e72903e22e8e3431a5c81b9f9d1393ef7f497301375f9cf825c8682a1d29b4479486e0862d1e |
| CONTRASTIVE LEARNING          | DIAGNOSTIC ACCURACY                | INTERVENTION_EFFECT   | claim            | TRUE     | Contrastive learning enhances diagnostic accuracy compared to standard learning methods. CMO[C=NONE; I=contrastive learning; M=NONE; O=enhanced diagnostic accuracy.]                                                              | Greater diagnostic accuracy was achieved following both contrastive learning and instructions to use a combined reasoning strategy relative to the control conditions. [PAGE 1]                                               | 7b46a2f96038bf5ba0d86c85d6de2a0df0f4b34de431fb6c7a22e72903e22e8e3431a5c81b9f9d1393ef7f497301375f9cf825c8682a1d29b4479486e0862d1e |
| INSTRUCTIONS                  | MULTIFACETED DIAGNOSTIC REASONING  | MECHANISM_EXPLANATION | claim            | TRUE     | Providing instructions to adopt multifaceted diagnostic reasoning strategies empowers students to utilize multiple approaches effectively. CMO[C=NONE; I=providing instructions; M=empowering students; O=NONE.]                   | The results emphasise the importance of explicitly empowering students to utilise multiple diagnostic strategies, including non-analytic approaches. [PAGE 1]                                                                 | 7b46a2f96038bf5ba0d86c85d6de2a0df0f4b34de431fb6c7a22e72903e22e8e3431a5c81b9f9d1393ef7f497301375f9cf825c8682a1d29b4479486e0862d1e |
| CONTEXT SPECIFICITY           | MULTIFACETED MODEL                 | CONTEXT_MODERATOR     | claim            | TRUE     | Context specificity influences the effectiveness of a multifaceted model of clinical reasoning in medical education. CMO[C=context specificity; I=NONE; M=NONE; O=NONE.]                                                           | Multiple studies have supported this contention, as does the overwhelmingly robust phenomenon of context specificity. [PAGE 2]                                                                                                | 7b46a2f96038bf5ba0d86c85d6de2a0df0f4b34de431fb6c7a22e72903e22e8e3431a5c81b9f9d1393ef7f497301375f9cf825c8682a1d29b4479486e0862d1e |
| COMPARATIVE LEARNING STRATEGY | ANALOGICAL TRANSFER                | INTERVENTION_EFFECT   | claim            | TRUE     | A contrastive learning strategy enhances analogical transfer in diagnostic reasoning. CMO[C=NONE; I=contrastive learning strategy; M=NONE; O=enhanced analogical transfer.]                                                        | This study assesses the extent to which students spontaneously adopt a combined approach and compares its benefits with those experienced with a contrastive learning strategy known to enhance analogical transfer. [PAGE 1] | 7b46a2f96038bf5ba0d86c85d6de2a0df0f4b34de431fb6c7a22e72903e22e8e3431a5c81b9f9d1393ef7f497301375f9cf825c8682a1d29b4479486e0862d1e |
| INSTRUCTIONAL STRATEGIES      | DIAGNOSTIC DECISION-MAKING         | MECHANISM_EXPLANATION | claim            | TRUE     | Instructional strategies that promote a combined approach to diagnostic decision-making improve students' reasoning capabilities. CMO[C=NONE; I=instructional strategies; M=improving reasoning capabilities; O=NONE.]             | This work began in the 1970s with Elstein et al.’s presentation of the hypothetico-deductive model of reasoning. [PAGE 2]                                                                                                     | 7b46a2f96038bf5ba0d86c85d6de2a0df0f4b34de431fb6c7a22e72903e22e8e3431a5c81b9f9d1393ef7f497301375f9cf825c8682a1d29b4479486e0862d1e |
| STUDENTS                      | MULTIFACETED DIAGNOSTIC STRATEGIES | OUTCOME_MEASUREMENT   | claim            | TRUE     | The effectiveness of multifaceted diagnostic strategies was evaluated through students' performance in diagnostic tasks. CMO[C=NONE; I=NONE; M=NONE; O=effectiveness evaluated.]                                                   | The results emphasise the importance of explicitly empowering students to utilise multiple diagnostic strategies, including non-analytic approaches. [PAGE 1]                                                                 | 7b46a2f96038bf5ba0d86c85d6de2a0df0f4b34de431fb6c7a22e72903e22e8e3431a5c81b9f9d1393ef7f497301375f9cf825c8682a1d29b4479486e0862d1e |
| INSTRUCTION                   | DIAGNOSTIC TASK                    | MECHANISM_EXPLANATION | claim            | TRUE     | Instruction on how to approach a diagnostic task influences students' reasoning strategies. CMO[C=NONE; I=instruction; M=influencing reasoning strategies; O=NONE.]                                                                | The remaining participants were given no instructions on how to approach the diagnostic task. [PAGE 1]                                                                                                                        | 7b46a2f96038bf5ba0d86c85d6de2a0df0f4b34de431fb6c7a22e72903e22e8e3431a5c81b9f9d1393ef7f497301375f9cf825c8682a1d29b4479486e0862d1e |
| STUDENTS                      | DIAGNOSTIC STRATEGIES              | OUTCOME_MEASUREMENT   | claim            | TRUE     | The study measured how students adopted diagnostic strategies after receiving different instructional methods. CMO[C=NONE; I=NONE; M=NONE; O=adoption of diagnostic strategies measured.]                                          | This study assesses the extent to which students spontaneously adopt a combined approach and compares its benefits with those experienced with a contrastive learning strategy. [PAGE 1]                                      | 7b46a2f96038bf5ba0d86c85d6de2a0df0f4b34de431fb6c7a22e72903e22e8e3431a5c81b9f9d1393ef7f497301375f9cf825c8682a1d29b4479486e0862d1e |
| INSTRUCTION                   | DIAGNOSTIC ACCURACY                | MECHANISM_EXPLANATION | claim            | TRUE     | Instructional methods that encourage a combined reasoning approach lead to improved diagnostic accuracy. CMO[C=NONE; I=instructional methods; M=leading to improved accuracy; O=NONE.]                                             | The results emphasise the importance of explicitly empowering students to utilise multiple diagnostic strategies. [PAGE 1]                                                                                                    | 7b46a2f96038bf5ba0d86c85d6de2a0df0f4b34de431fb6c7a22e72903e22e8e3431a5c81b9f9d1393ef7f497301375f9cf825c8682a1d29b4479486e0862d1e |
| STUDENTS                      | DIAGNOSTIC TASKS                   | INTERVENTION_EFFECT   | claim            | TRUE     | Students who received specific instructions performed better on diagnostic tasks. CMO[C=NONE; I=specific instructions; M=NONE; O=better performance on diagnostic tasks.]                                                          | The remaining participants were given no instructions on how to approach the diagnostic task. [PAGE 1]                                                                                                                        | 7b46a2f96038bf5ba0d86c85d6de2a0df0f4b34de431fb6c7a22e72903e22e8e3431a5c81b9f9d1393ef7f497301375f9cf825c8682a1d29b4479486e0862d1e |

### Community structure

- communities rows: **15**

### Community report quality (principle-level heuristics)

- community_reports rows: **15**
- generic/too-short titles (heuristic): **0 / 15**

**Community report headers (sample)**

|   community |   level | title                                                                |   rank |   size |
|------------:|--------:|:---------------------------------------------------------------------|-------:|-------:|
|          10 |       1 | Diagnostic Accuracy in ECG Interpretation                            |    7.5 |     47 |
|          11 |       1 | Diagnostic Learning Strategies Community                             |    8   |      3 |
|          12 |       1 | Diagnostic Knowledge Community                                       |    7.5 |     22 |
|          13 |       1 | Medical Education Community: Feedback and Learning Strategies        |    7.5 |      9 |
|          14 |       1 | Educational Strategies: Worked Example Approach and Self-Explanation |    7.5 |      3 |
|           0 |       0 | Diagnostic Accuracy and Learning Strategies in ECG Interpretation    |    8   |     50 |
|           1 |       0 | Combined Reasoning Approaches in ECG Diagnosis                       |    7.5 |     12 |
|           2 |       0 | Analytic Tendencies and Feature Manipulation                         |    6   |      2 |
|           3 |       0 | Clinical Reasoning and Diagnostic Skills Community                   |    8   |     19 |
|           4 |       0 | Undergraduate Psychology Students and ECG Diagnosis                  |    6.5 |      4 |
|           5 |       0 | Schema Construction and Learning Methods                             |    7.5 |      3 |
|           6 |       0 | Diagnostic Knowledge and Elaborated Feedback Community               |    8   |     34 |
|           7 |       0 | ECG Diagnostic Training Community                                    |    7.5 |      4 |
|           8 |       0 | Non-Analytic Tendencies and Diagnostic Hypothesis Manipulation       |    6   |      2 |
|           9 |       0 | ECG Diagnosis and Feedback Mechanisms                                |    7.5 |     13 |

### What to verify against Richmond (next)

- **Search/screening alignment**: overlap with Richmond-28 + explain mismatches.
- **CMO fidelity**: do extracted claims support C→M→O patterns?
- **Concept alignment**: map community titles ↔ Richmond mechanisms/programme theory components.
- **Cross-study synthesis**: identify dominant patterns + contradictions with citations/spans.
