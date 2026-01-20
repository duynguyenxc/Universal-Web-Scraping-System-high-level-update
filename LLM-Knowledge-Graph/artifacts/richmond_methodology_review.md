# Methodology Review: Richmond et al. (2020)
**"The student is key: A realist review of educational interventions to develop analytical and non-analytical clinical reasoning ability"**

## 1. Overview & Objective
Richmond et al. conducted a **Realist Review** (not a standard systematic review) to understand *how* and *why* educational interventions work to improve clinical reasoning.
*   **Goal:** To move beyond "does it work?" to "what works, for whom, in what circumstances?"
*   **Core Question:** What mechanisms are triggered by different interventions (context) to produce improved reasoning (outcome)?

## 2. Methodology: The Realist Cycle
The authors followed the RAMESES quality standards for realist synthesis. Their process was **iterative**, not linear.

### Step 1: Search Strategy (Theory-Driven)
*   **Approach:** Instead of one fixed search, they used "cluster searching". They started with a broad search, then refined it as they developed their theory.
*   **Databases:** PubMed, Scopus, ERIC, PsycINFO.
*   **Key Distinction:** They didn't just look for "high quality RCTs". They looked for "nuggets of evidence" that could explain *mechanisms*.

### Step 2: Selection & Screening (Relevance > Rigor)
*   **Relevance:** Does this paper validly test or clarify a part of our programme theory? associated with the intervention?
*   **Rigor:** Is the data credible? (Not just specific study design hierarchy).
*   **Result:** They selected **28 studies** that provided the "thickest" description of how students reason.

### Step 3: Data Extraction (The CMO Configuration)
This is the most critical step for our automated verification. The authors manually extracted data into **Context-Mechanism-Outcome (CMO)** configurations.
*   **Context (C):** Who are the students? (Novice vs Expert). What is the setting? (Simulation vs Bedside).
*   **Mechanism (M):** What happened in the student's head?
    *   *Examples identified:* "Knowledge encapsulation", "Illness script formation", "Self-explanation", "Contrastive thinking".
*   **Outcome (O):** Did diagnostic accuracy improve? Did confidence increase?

### Step 4: Synthesis (Programme Theories)
They synthesized the extracted CMOs into 3 main **Programme Theories**:
1.  **Knowledge Organization:** Interventions that help students structure knowledge (e.g., schemas) reduce cognitive load and improve analytic reasoning.
2.  **Repetitive Practice:** High-volume practice (e.g., vps) builds "illness scripts" (non-analytic reasoning).
3.  **Metacognition:** Reflection and feedback help students switch between analytic and non-analytic modes.

## 3. Implications for AI Verification
To verify our **Agentic GraphRAG** against this work, we must demonstrate that the AI can:
1.  **Retrieve:** Find the same 28 studies (or explain why not - e.g., newer database state).
2.  **Extract:** Identify the same **Mechanisms** (e.g., capturing "Illness script" as a Concept, not just a keyword).
3.  **Synthesize:** Group these mechanisms into Communities that resemble the 3 Programme Theories above.

## 4. Conclusion
Richmond et al. (2020) represents a High-Human-Cognitive-Load task. They manually inferred mechanisms that were often implicit in the text.
*   **Challenge for AI:** Can GraphRAG infer "Cognitive Load" even if the paper doesn't explicitly measure it, but describes "students feeling overwhelmed"?
*   **Success Metric:** If GraphRAG's "Community Reports" mention "Illness Scripts" or "Schema formation" as key themes, we have achieved replication.
