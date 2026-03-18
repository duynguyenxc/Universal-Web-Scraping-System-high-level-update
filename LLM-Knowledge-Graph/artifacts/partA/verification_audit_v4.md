## Part A (Education) — Verification Audit (quality gates)

- output dir: `D:/Universal-Web-Scraping-System-high-level-update/Universal-Web-Scraping-System-high-level-update-main/LLM-Knowledge-Graph/graphrag-project/output_partA_richmond28_v4_run3`

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

- entities rows: **944**

**Entity types (counts)**

| type                |   count |
|:--------------------|--------:|
| INTERVENTION        |     237 |
| MECHANISM           |     163 |
| OUTCOME             |     147 |
|                     |      87 |
| LEARNER_CONTEXT     |      76 |
| SETTING_CONTEXT     |      76 |
| CONTEXT             |      37 |
| LEARNER_POPULATION  |      35 |
| COMPARATOR          |      22 |
| STUDY_DESIGN        |      18 |
| MOTIVATION_AFFECT   |      12 |
| CLINICAL_DOMAIN     |      11 |
| COGNITIVE_STATE     |      10 |
| "INTERVENTION"      |       5 |
| "MECHANISM"         |       3 |
| "LEARNER_CONTEXT"   |       2 |
| "OUTCOME"           |       2 |
| "MOTIVATION_AFFECT" |       1 |

- blacklisted-looking entity titles (heuristic): **1 / 944**

**Top entities by frequency (spot-check for bibliographic noise)**

| title                             | type               |   frequency |   degree |
|:----------------------------------|:-------------------|------------:|---------:|
| DIAGNOSTIC ACCURACY               | OUTCOME            |          40 |      133 |
| DIAGNOSTIC PERFORMANCE            | OUTCOME            |          28 |       94 |
| SELF-EXPLANATION                  | INTERVENTION       |          20 |       48 |
| PRIOR KNOWLEDGE                   | LEARNER_CONTEXT    |          10 |       10 |
| STRUCTURED REFLECTION             | INTERVENTION       |           9 |       15 |
| ILLNESS SCRIPTS                   | MECHANISM          |           8 |       18 |
| DIAGNOSTIC ERROR                  | OUTCOME            |           8 |       18 |
| FEEDBACK                          | INTERVENTION       |           7 |        8 |
| CONTROL GROUP                     | COMPARATOR         |           7 |        4 |
| STUDENT PERFORMANCE               | OUTCOME            |           6 |       15 |
| REPEATED TESTING                  | INTERVENTION       |           6 |        8 |
| COGNITIVE BIASES                  | MECHANISM          |           6 |        9 |
| KNOWLEDGE RESTRUCTURING           | MECHANISM          |           6 |       10 |
| DIAGNOSTIC COMPETENCE             | OUTCOME            |           6 |       16 |
| UNDERGRADUATE PSYCHOLOGY STUDENTS | LEARNER_POPULATION |           5 |        1 |
| SCHEMA-BASED INSTRUCTION          | INTERVENTION       |           5 |       12 |
| FEEDBACK TIMING                   | SETTING_CONTEXT    |           5 |        4 |
| PROMPTS                           | INTERVENTION       |           5 |        7 |
| DIAGNOSTIC KNOWLEDGE              | OUTCOME            |           5 |       11 |
| FAR-TRANSFER CASES                | SETTING_CONTEXT    |           5 |        2 |
| CASEBOOK APPLICATION              | INTERVENTION       |           5 |        8 |
| INTER-RATER RELIABILITY           | STUDY_DESIGN       |           4 |        0 |
| LESS FAMILIAR CASES               | SETTING_CONTEXT    |           4 |        3 |
| ANALYTIC TRAINING                 | INTERVENTION       |           4 |        8 |
| PATTERN RECOGNITION               | MECHANISM          |           4 |        4 |

### Claim quality (traceability + CMO)

- source: **claims_fixed.parquet**
- claims rows: **1517**
- claims with `[PAGE N]` marker in source_text: **1187 / 1517**

**Claim completeness (heuristic)**

- missing subject: **0 / 1517**
- missing object: **0 / 1517**
- missing evidence span (source_text/text): **80 / 1517**

**Claim types (counts)**

| type                   |   count |
|:-----------------------|--------:|
| INTERVENTION_EFFECT    |     552 |
| OUTCOME_MEASUREMENT    |     465 |
| CONTEXT_MODERATOR      |     259 |
| MECHANISM_EXPLANATION  |     229 |
| <INTERVENTION_EFFECT   |       4 |
| COMPARATOR             |       4 |
| <CONTEXT_MODERATOR     |       3 |
| <MECHANISM_EXPLANATION |       1 |

**Sample claims (spot-check)**

| subject_id                                  | object_id                      | type                  | covariate_type   | status   | description                                                                                                                                                           | source_text                                                                                                                                                                        | text_unit_id                                                                                                                     |
|:--------------------------------------------|:-------------------------------|:----------------------|:-----------------|:---------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------|
| MEDICAL STUDENTS                            | DIAGNOSTIC COMPETENCE          | INTERVENTION_EFFECT   | claim            | TRUE     | This case-based clinical reasoning seminar intervention improved aspects of diagnostic competence.                                                                    | This case-based clinical reasoning seminar intervention, designed to bring students insight into cognitive features of their reasoning, improved aspects of diagnostic competence. | 391c7b5d79db439034c81f94da0d2622bec728fe85667ae24b0ed5ba165674948a771b0a8a814762ee78de03eb32037438c79e2fc43dff4a1bc70c6afb58f1cf |
| CASE-BASED CLINICAL REASONING SEMINAR       | COGNITIVE FEATURES             | MECHANISM_EXPLANATION | claim            | TRUE     | The intervention was designed to bring students insight into cognitive features of their reasoning.                                                                   | This case-based clinical reasoning seminar intervention, designed to bring students insight into cognitive features of their reasoning, improved aspects of diagnostic competence. | 391c7b5d79db439034c81f94da0d2622bec728fe85667ae24b0ed5ba165674948a771b0a8a814762ee78de03eb32037438c79e2fc43dff4a1bc70c6afb58f1cf |
| CASE-BASED CLINICAL REASONING SEMINAR       | NONE                           | OUTCOME_MEASUREMENT   | claim            | TRUE     | The intervention improved aspects of diagnostic competence.                                                                                                           | This case-based clinical reasoning seminar intervention, designed to bring students insight into cognitive features of their reasoning, improved aspects of diagnostic competence. | 391c7b5d79db439034c81f94da0d2622bec728fe85667ae24b0ed5ba165674948a771b0a8a814762ee78de03eb32037438c79e2fc43dff4a1bc70c6afb58f1cf |
| ACQUISITION OF VISUAL INTERPRETATION SKILLS | NONANALYTIC REASONING          | MECHANISM_EXPLANATION | claim            | TRUE     | Nonanalytic reasoning may expedite the acquisition of visual interpretation skills in cytopathology training programs by allowing for faster recognition of patterns. | To what extent does nonanalytic reasoning contribute to visual learning in cytopathology? [PAGE 1]                                                                                 | 268f766045579cc2bd4a2edf59a25d7cdc57bb8432aabfcdec8fb2e925f07d8270f8b1b4b317a80074b3adc70f793f341a91e3695ac3ff8486131e9d535b7473 |
| TRAINING IN BASIC CERVICAL CYTOMORPHOLOGY   | DIAGNOSTIC ACCURACY            | INTERVENTION_EFFECT   | claim            | TRUE     | Training in basic cervical cytomorphology improved diagnostic accuracy significantly between tests 1 and 2.                                                           | To what extent does nonanalytic reasoning contribute to visual learning in cytopathology? [PAGE 1]                                                                                 | 268f766045579cc2bd4a2edf59a25d7cdc57bb8432aabfcdec8fb2e925f07d8270f8b1b4b317a80074b3adc70f793f341a91e3695ac3ff8486131e9d535b7473 |
| NONANALYTIC GROUP                           | SPEED OF RESPONSE              | INTERVENTION_EFFECT   | claim            | TRUE     | Participants in the nonanalytic group responded faster to test images compared to the analytic group.                                                                 | To what extent does nonanalytic reasoning contribute to visual learning in cytopathology? [PAGE 1]                                                                                 | 268f766045579cc2bd4a2edf59a25d7cdc57bb8432aabfcdec8fb2e925f07d8270f8b1b4b317a80074b3adc70f793f341a91e3695ac3ff8486131e9d535b7473 |
| COMBINED ANALYTIC/NONANALYTIC STRATEGY      | DIAGNOSTIC ACCURACY            | CONTEXT_MODERATOR     | claim            | TRUE     | Combining analytic and nonanalytic reasoning does not appear to be effective in improving diagnostic accuracy.                                                        | To what extent does nonanalytic reasoning contribute to visual learning in cytopathology? [PAGE 1]                                                                                 | 268f766045579cc2bd4a2edf59a25d7cdc57bb8432aabfcdec8fb2e925f07d8270f8b1b4b317a80074b3adc70f793f341a91e3695ac3ff8486131e9d535b7473 |
| ANALYTIC STRATEGIES                         | TIME-CONSUMING AND INEFFICIENT | MECHANISM_EXPLANATION | claim            | TRUE     | Analytic strategies are time-consuming and inefficient, which may hinder the learning process in cytopathology.                                                       | To what extent does nonanalytic reasoning contribute to visual learning in cytopathology? [PAGE 1]                                                                                 | 268f766045579cc2bd4a2edf59a25d7cdc57bb8432aabfcdec8fb2e925f07d8270f8b1b4b317a80074b3adc70f793f341a91e3695ac3ff8486131e9d535b7473 |
| NONANALYTIC LEARNING                        | EFFICIENT ALTERNATIVE          | MECHANISM_EXPLANATION | claim            | TRUE     | Nonanalytic learning serves as an efficient alternative to analytic training in cytopathology.                                                                        | To what extent does nonanalytic reasoning contribute to visual learning in cytopathology? [PAGE 1]                                                                                 | 268f766045579cc2bd4a2edf59a25d7cdc57bb8432aabfcdec8fb2e925f07d8270f8b1b4b317a80074b3adc70f793f341a91e3695ac3ff8486131e9d535b7473 |
| CYTOPATHOLOGY TRAINING PROGRAMS             | VISUAL INTERPRETATION SKILLS   | OUTCOME_MEASUREMENT   | claim            | TRUE     | The study evaluated the role of nonanalytic learning in cytopathology as a means to improve visual interpretation skills.                                             | To what extent does nonanalytic reasoning contribute to visual learning in cytopathology? [PAGE 1]                                                                                 | 268f766045579cc2bd4a2edf59a25d7cdc57bb8432aabfcdec8fb2e925f07d8270f8b1b4b317a80074b3adc70f793f341a91e3695ac3ff8486131e9d535b7473 |
| CYTOLOGY NOVICE PARTICIPANTS                | BASELINE DIAGNOSTIC ACCURACY   | OUTCOME_MEASUREMENT   | claim            | TRUE     | Forty-nine cytology novice participants undertook an initial image interpretation test to obtain baseline diagnostic accuracy.                                        | To what extent does nonanalytic reasoning contribute to visual learning in cytopathology? [PAGE 1]                                                                                 | 268f766045579cc2bd4a2edf59a25d7cdc57bb8432aabfcdec8fb2e925f07d8270f8b1b4b317a80074b3adc70f793f341a91e3695ac3ff8486131e9d535b7473 |
| PARTICIPANTS IN BOTH GROUPS                 | RETESTED DIAGNOSTIC ACCURACY   | OUTCOME_MEASUREMENT   | claim            | TRUE     | Both groups were retested for diagnostic accuracy after training, showing significant improvement.                                                                    | To what extent does nonanalytic reasoning contribute to visual learning in cytopathology? [PAGE 1]                                                                                 | 268f766045579cc2bd4a2edf59a25d7cdc57bb8432aabfcdec8fb2e925f07d8270f8b1b4b317a80074b3adc70f793f341a91e3695ac3ff8486131e9d535b7473 |

### Community structure

- communities rows: **111**

### Community report quality (principle-level heuristics)

- community_reports rows: **111**
- generic/too-short titles (heuristic): **0 / 111**

**Community report headers (sample)**

|   community |   level | title                                                             |   rank |   size |
|------------:|--------:|:------------------------------------------------------------------|-------:|-------:|
|         104 |       2 | Control Group and Delayed Improvement in Diagnostic Accuracy      |    6.5 |      2 |
|         105 |       2 | Novice Diagnosticians and Similarity-Based Processes              |    6   |      2 |
|         106 |       2 | Contrastive Learning and Diagnostic Accuracy Community            |    7.5 |     71 |
|         107 |       2 | Self-Explanation in Medical Education Community                   |    8.5 |     50 |
|         108 |       2 | Cognitive Involvement and Passive Listening                       |    6   |      2 |
|         109 |       2 | Clinical Reasoning Community                                      |    7.5 |     37 |
|         110 |       2 | Case Conference Method and Cognitive Restructuring                |    7.5 |      2 |
|          29 |       1 | Combined Reasoning Condition and Analytic Approaches              |    7.5 |      2 |
|          30 |       1 | Case Complexity and Analytic Strategies Community                 |    6.5 |      3 |
|          31 |       1 | Enhanced Analytic Reasoning Community                             |    7.5 |      4 |
|          32 |       1 | Combined Reasoning Strategy and Diagnostic Capability             |    7.5 |      5 |
|          33 |       1 | Contrastive Learning and Diagnostic Accuracy in Medical Education |    8.5 |     75 |
|          34 |       1 | Pattern Recognition and Perceptual Learning Community             |    7.5 |      2 |
|          35 |       1 | Cognitive Strategies in Diagnostic Decision-Making                |    6.5 |      4 |
|          36 |       1 | Combined Reasoning Instruction in Diagnostic Accuracy             |    7.5 |      3 |

### What to verify against Richmond (next)

- **Search/screening alignment**: overlap with Richmond-28 + explain mismatches.
- **CMO fidelity**: do extracted claims support C→M→O patterns?
- **Concept alignment**: map community titles ↔ Richmond mechanisms/programme theory components.
- **Cross-study synthesis**: identify dominant patterns + contradictions with citations/spans.
