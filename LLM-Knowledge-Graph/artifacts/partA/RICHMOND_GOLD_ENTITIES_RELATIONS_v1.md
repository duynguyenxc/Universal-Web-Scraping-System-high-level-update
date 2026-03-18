## Richmond (2020) — Gold Entities & Relations Specification v1 (CMOC Graph Targets)

This document defines the **gold standard entity families and relationship templates** implied by Richmond et al. (2020), using the paper’s own conceptual definitions (Methods) and Figures (PRISMA + CMOC diagrams).
It is intended as the **verification reference** for judging whether our extracted `entities` + `relationships` are “sát / khớp Richmond”.

---

## 1) Gold “entity types” (conceptual, Richmond-native)

Richmond defines realist elements explicitly:
- **Context (C)**: conditions separate from the intervention that affect how it is received.
- **Mechanism (M)**: conceptualised as **resources and responses**:
  - **Mresource**: resources offered by the intervention into a context
  - **Mresponse**: cognitive/emotional response in participants, leading to outcomes
- **Outcome (O)**: measured effect(s) (short-term and longer-term)

### 1.1 Gold Context entities (student-level; the backbone)
From Figure 2 (and Results 3.2.*), the five key student-level contexts are:
1. **LOW KNOWLEDGE / LOW DOMAIN-SPECIFIC KNOWLEDGE / INABILITY TO APPLY KNOWLEDGE IN A REASONING SITUATION**
2. **HIGH CLINICAL DOMAIN-SPECIFIC KNOWLEDGE STUDENT**
3. **POSITIVE STUDENT COPING STRATEGIES OR APPROPRIATE SELF-CONFIDENCE / SELF-EFFICACY**
4. **NEGATIVE STUDENT COPING STRATEGIES OR LACKING SELF-CONFIDENCE / SELF-EFFICACY**
5. **DIFFERENT LEVELS OF KNOWLEDGE WITHIN A GROUP**

### 1.2 Gold Mechanism Resource entities (intervention resources, as shown in Figures)
From Figure 2:
- **INSTRUCTIONS TO USE ANALYTICAL REASONING ALONE** (especially with low difficulty cases)
- **TEACHING STRATEGIES THAT PROMOTE “OVERTHINKING”**
- **REASONING PROCESSES AND OUTPUTS IDENTIFIED AND DISCUSSED WITH FACILITATOR**
- **SIMULATED ENVIRONMENTS THAT REPLICATE AUTHENTIC REAL-LIFE SITUATIONS** / teaching that enables making mistakes / teaching in real world
- **TEACHING APPROACH DESIGNED AROUND EFFECTIVE LEARNING STRATEGIES TO INCREASE LONG-TERM KNOWLEDGE RETENTION**
- **COMPREHENSIVE FEEDBACK RECEIVED IN A TIMELY MANNER FOLLOWING REASONING TASK**
- **INSUFFICIENT OR INCOMPLETE FEEDBACK (INCLUDING INCORRECT OR ERRONEOUS IN NATURE)**

From Figure 3 (Context 1 expanded):
Facilitators to learning positive outcomes:
- **LISTEN TO NEAR-PEER “THINK ALOUD” REASONING** with prompts and examples
- **INSTRUCTIONS TO USE BOTH “NON-ANALYTICAL” (PATTERN RECOGNITION) AND ANALYTICAL / STEP-WISE APPROACH**
- **ACCURATE FEEDBACK IN A TIMELY MANNER**
- **EXPLICIT AND CLEAR EXPLANATION OF EXPERT’S REASONING**
- **PROMOTION OF ANALYTICAL OR STEP-WISE APPROACH AS REASONING SCAFFOLD**

Barriers to learning negative outcomes:
- **INDUCING OR IMPOSING TIME CONSTRAINT TO FORCE NON-ANALYTICAL REASONING**
- **PASSIVE OBSERVATION OF EXPERTS WITHOUT EXPLANATION OF THEIR REASONING PROCESSES**
- **LISTENING TO EXPERTS EXPLAIN THEIR REASONING** (with many steps / pattern recognition) in a way that creates discordance for novices
- **INCREASED CASE DIFFICULTY / SIGNIFICANT REASONING CHALLENGE**
- **LISTENING TO PEER REASONING AS PASSIVE RECIPIENT WHEN SELF-EXPLANATION INCLUDES MISTAKES**

### 1.3 Gold Mechanism Reaction entities (learner cognitive/emotional responses)
From Figure 2 and Figure 3:
- **ASSUME SIMILAR PRIOR KNOWLEDGE → FEELING AT EASE**
- **EMPOWERED TO TRUST “SENSE OF FAMILIARITY” AND DEVELOPING ABILITY**
- **SENSE OF CLARITY → DEVELOP UNDERSTANDING** (affirming adequate knowledge)
- **RELIEVES TENSION; KNOWLEDGE ANSWERED; FEEL COMFORTABLE, SUPPORTED**
- **SPONTANEOUS OUTPUTS FROM NON-ANALYTICAL REASONING (GUESSING) → FRUSTRATION / DISTRESS**
- **RESENTMENT OR PANIC AT NOT RECALLING OR “KNOWING” IMMEDIATELY**
- **DIFFICULTY UNDERSTANDING NON-ANALYTICAL THOUGHT PROCESS; DISCORDANCE BETWEEN ILLNESS SCRIPTS**
- **FRUSTRATION**
- **CONFUSION**
- **GRATEFUL FOR LEARNING EXPERIENCE / FEEL “SAFE” TO MAKE MISTAKES**
- **FEAR / STRESS / ANXIETY**
- **INCREASED COGNITIVE LOAD**
- **CONTINUED DEVELOPMENT AND UNDERSTANDING ABOUT THE PROCESS OF CLINICAL REASONING**
- **NEW UNDERSTANDING ABOUT THE PROCESS OF CLINICAL REASONING**

### 1.4 Gold Outcome entities (what changes)
From Figures:
- **INCREASE IN LEARNING GAIN / OUTCOMES OR INCREASE IN DIAGNOSTIC ACCURACY**
- **DECREASE IN LEARNING GAIN / OUTCOMES OR DECREASE IN DIAGNOSTIC ACCURACY**
- **POSITIVE IMPACT ON LEARNING OUTCOMES** (including building/refinement of illness scripts)
- **NEGATIVE IMPACT ON LEARNING OUTCOMES** (including faulty illness script development)
- **NO IMPROVEMENT IN DIAGNOSTIC ACCURACY / LIMITED OR NO INCREASE IN OUTCOMES**

---

## 2) Gold relationship templates (what edges should exist)

Richmond’s CMOC logic is generative causation:

### 2.1 Primary CMOC chain (the default)
\[
Context \;\rightarrow\; Mechanism\ Resource \;\rightarrow\; Mechanism\ Reaction \;\rightarrow\; Outcome
\]

### 2.2 Allowed edge families (for our KG)
- **C → Mresource**: context conditions which resources “work”
- **Mresource → Mreaction**: resource triggers learner response
- **Mreaction → O**: response produces outcomes (positive/negative)
- **C → Mreaction**: context directly shapes response (e.g., low knowledge → panic)
- **C → O**: context moderates outcomes even for same resource (Matthew effect / expertise reversal)

### 2.3 Directionality constraints (verification-friendly)
- Outcomes are **sinks** (do not use outcome as a causal source edge).
- Relationships should be short predicates (enables / inhibits / triggers / moderates / leads_to).

---

## 3) Gold selection “reasons” (PRISMA as selection-layer targets)
From the PRISMA diagram (Figure 1):
- Duplicates removed: **530**
- Titles/abstracts screened: **7097**
- Removed as irrelevant during title/abstract screening: **6958**
- Full texts retrieved/reviewed: **149**
- Added from supplementary search: **10**
- Full texts removed for reasons (n=124):
  - Unable to obtain full text: **11**
  - Investigated neurochemical / neurostructural aspects only: **1**
  - Didn’t describe an educational intervention: **59**
  - Didn’t specifically target dual processing theory: **64**
  - Assessment of reasoning only: **1**
  - Postgraduate education only and no specific dual process intervention: **12**
  - Decision support tools/checklists only: **5**
  - Other: **7**
  - Removed during data extraction as lacked methodological rigour: **2**
  - Removed during data extraction as not contributing to developing theory: **2**
- Added from reference lists: **2**
- Added from later search on learning strategies/retention: **1**
- Included: **28**

