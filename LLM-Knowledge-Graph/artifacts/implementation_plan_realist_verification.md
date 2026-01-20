# Implementation Plan: Agentic GraphRAG for Realist Review Verification

## Goal
Configure and run a professional, domain-adapted GraphRAG system to perform a "Realist Synthesis" on 28 educational studies. The output must successfully identify "Community-defined conceptual entities" that match the human-derived mechanisms in Richmond et al. (2020).

## 1. The "Big Idea": Realist Ontology (The Entity Problem)
**STATUS: SUCCESS (Verified in `subset5`)**
The Professor's requirement for "Community-defined conceptual entities" is **ALREADY IMPLEMENTED** in your `subset5` run.
Current Ontology found in `subset5`:
*   `INTERVENTION` (e.g., "Contrastive Learning")
*   `MECHANISM` (e.g., "Analogical Transfer")
*   `OUTCOME` (e.g., "Diagnostic Accuracy")
*   `LEARNER_POPULATION` (e.g., "Naïve Students")

**Our Strategy:** We will NOT delete this. We will **refine** it to be "Publication-Ready".
1.  **Clean up:** Remove empty types and ambiguous types (e.g., merge `CONTEXT` and `SETTING_CONTEXT`).
2.  **Enrich:** Ensure definitions in `extract_graph.txt` compel the LLM to be precise about *Mechanism* vs *Intervention*.

## 2. Technical Implementation Steps

### Step 1: Configuration Refinement (Fine-tuning `subset5`)
The `subset5` configuration is 90% there. We will make it 100%:
*   **Action:** Audit `prompts/extract_graph.txt` used in `subset5`.
*   **Action:** Add strict definitions for "Mechanism" to prevent it from being confused with "Intervention".
*   **Action:** Ensure `max_gleanings` is set to captured "missed" entities in complex paragraphs.

### Step 2: Verification Protocol (The "Proof" for RRE)
We need to prove this works for the paper.
*   **Action:** Create a **"Traceability Table"**:
    *   Show a snippet of text from Richmond.
    *   Show the Entities/Claims GraphRAG extracted.
    *   Show the Community Summary.
    *   *Why:* This proves "Auditable logic" (a key requirement in the User's text).

### Step 3: Drafting the Paper (Feb Deadline)
We will use the User's provided text as the **Core Architecture**.
*   **Section 4.1 (Architecture):** We simply describe what `subset5` is doing.
*   **Section 5 (Verification):** We use the `inspect_parquet` data as the "Results".
*   **Comparison:** We manually map GraphRAG Communities to Richmond's 3 Program Theories.

### Step 4: Verification Output
We will generate a **Comparison Table** for the paper:
*   **Column A (Human):** Mechanisms identified by Richmond (e.g., "Knowledge encapsulation").
*   **Column B (AI):** Communities identified by GraphRAG (e.g., "Community #3: Structuring knowledge for retrieval").
*   **Match:** Analysis of alignment.

## 3. Verification & Manuscript Support
This implementation directly supports the **"Methodological Innovation"** claim in the RRE paper:
> "We demonstrate that by defining a 'Realist Ontology', GraphRAG can automatically surface the same conceptual mechanisms as expert reviewers."

## Next Steps
1.  Read `settings.yaml` to assess current state.
2.  Create the custom Prompt for Realist Extraction.
3.  Execute a test run on a subset of data.
