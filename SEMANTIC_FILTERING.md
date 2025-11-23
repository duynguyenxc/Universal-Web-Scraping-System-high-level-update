## Semantic Filtering in the UWSS Web Crawler

This document explains how the **semantic filtering** layer in the UWSS web crawler works, and how it fits into the overall architecture. It is written for readers who are comfortable with the idea of machine learning / AI, but do not need low-level mathematical details.

---

## 1. Motivation

The original Scrapy crawler filtered pages **only by keywords**:

- If a page contained words like *“corrosion”*, *“durability”*, *“reinforced concrete”*, etc., it was considered relevant.  
- If not, it was discarded.

This works, but has limitations:

- It can miss pages that talk about the right topic using **different wording** (synonyms, paraphrases).  
- It sometimes keeps pages that only mention the keywords **superficially** (e.g., in a menu or in a long list), not in the main content.  
- The filter has no sense of “how close” a page is to the research topic, only a yes/no decision.

The semantic filtering layer adds a second step that asks:

> “How similar is the **meaning** of this page to the topic we care about?”

The result is a numeric score `semantic_score ∈ [0, 1]`, where higher scores mean “more semantically related”.

---

## 2. High‑level architecture

The web crawler now has two layers:

- **Layer 1 – Scrapy + keyword filter (unchanged core):**
  - Input: one **seed URL** (lab or department website).
  - Scrapy follows links within the same domain (`allowed_domains`), obeying `robots.txt`, and respecting `max_depth` and `max_pages`.
  - Each page is converted to text and checked with a **keyword-based relevance function**.
  - Pages that pass this keyword filter are turned into items with metadata (title, abstract, year, emails, group, etc.).

- **Layer 2 – Semantic filtering (new):**
  - Takes the items produced by Layer 1.
  - Builds a **topic representation** from the corrosion/durability keywords.
  - Computes a **semantic similarity score** between each page and the topic.
  - Discards pages whose `semantic_score` is below a threshold, and removes duplicates per URL.
  - Outputs a final JSONL file with the **best pages for that topic**.

This design keeps Scrapy as the main crawling engine, and uses ML only as a “smart filter” on top of what the crawler already finds.

---

## 3. Technology used

We **do not train a model from scratch**. Instead, we reuse a well‑known open‑source library:

- **Sentence Transformers** (`sentence-transformers` Python package), on top of HuggingFace Transformers.
- Model: `sentence-transformers/all-MiniLM-L6-v2`.

What this model does:

- It converts a sentence or paragraph into a **fixed‑size vector** (embedding), e.g. a 384‑dimensional vector of real numbers.  
- Sentences with **similar meaning** end up with embeddings that are **close together** in this vector space.

In UWSS, we wrap this in a small helper:

- `src/uwss/semantic/embedding.py`  
  - Function: `compute_semantic_score(text, topic_text, model_name=...)`  
  - Returns a scalar value in \([0, 1]\) representing how similar `text` is to `topic_text`.

---

## 4. How semantic scoring works

At a high level, semantic scoring follows these steps:

1. **Construct the topic text**

   We start from the corrosion/durability keywords in the config file (for example):

   - “reinforced concrete corrosion”
   - “concrete durability”
   - “chloride diffusion”
   - “service life prediction”

   We concatenate them into a short paragraph, such as:

   > *"Research about corrosion and long-term durability of reinforced concrete, chloride ingress, concrete durability experiments, and service life prediction."*

   This paragraph is called `topic_text`.

2. **Compute the topic embedding**

   We call the Sentence Transformers model to embed this text:

   \[
   v_{\text{topic}} = \text{encode}(topic\_text)
   \]

   The result is a numerical vector that represents the **meaning** of the topic.

3. **Compute the page embedding**

   For each crawled page (item), we build a representative text:

   - Concatenate `title`, `abstract`, and the main body `content` (which we now extract using `trafilatura` to avoid navigation noise).  
   - Pass this combined text to the same model:

   \[
   v_{\text{page}} = \text{encode}(page\_text)
   \]

4. **Compute semantic similarity**

   We then compute the **cosine similarity** between the two embeddings:

   \[
   \text{semantic\_score} = \cos\left(v_{\text{topic}}, v_{\text{page}}\right)
   \]

   For normalized embeddings, this score lies between \(-1\) and \(1\), but in our usage it is effectively in \([0, 1]\) and can be interpreted as:

   - 0.0  → unrelated,  
   - 0.5  → moderately related,  
   - 0.8+ → strongly related.

5. **Filter and deduplicate**

   In the CLI command `web-crawler-semantic-discover`:

   - If `semantic_score` is below a user‑defined threshold (e.g. 0.3 or 0.4), we **discard** the page.  
   - For each `source_url` (or `landing_url`), we keep **only the item with the highest `semantic_score`** to avoid duplicates.  
   - The remaining items are sorted by `semantic_score` (descending) and written to a JSONL file.

The final JSONL output therefore contains the **top pages in that website that are most semantically aligned with the corrosion/durability topic**, not just those that happen to contain certain keywords.

---

## 5. Why this design (and not something heavier)?

We purposefully chose a **lightweight and modular** design:

- **No custom training**:  
  - Training a new model would require large labeled datasets and much more time.  
  - By using a pre‑trained Sentence Transformers model, we benefit from a strong semantic representation “out of the box”.

- **Separation of concerns**:
  - Scrapy + pipelines handle **what to crawl** and how to extract metadata, obey robots.txt, etc.  
  - The semantic module is a **pure post‑processing step**:
    - It takes text as input and returns a score.
    - It does not change how the crawler behaves at the network level.

- **Reproducibility and clarity**:
  - All logic is contained in a small number of files (`spider.py`, pipelines, `embedding.py`, and CLI glue code).  
  - The semantic behavior can be controlled via CLI flags and config:
    - `--topic` (override topic description),  
    - `--semantic-model` (which embedding model to use),  
    - `--semantic-threshold` (how strict the filter should be).

This makes the system more intelligent than a pure keyword filter, while still being **transparent, reproducible, and realistic** for a research project.

---

## 6. Limitations and future work

Current limitations:

- The semantic filter currently runs **after** the crawl (as a post‑processing stage). It does not yet influence which links Scrapy chooses to follow (i.e., the frontier selection is not semantic‑aware).  
- The quality depends on:
  - The choice of `topic_text` (how well it describes the desired research area).  
  - The threshold selected (`semantic_threshold`), which may need tuning per website.

Possible future improvements:

- Use `semantic_score` to **prioritize which links to follow deeper** (true semantic focused crawling).  
- Add small evaluation experiments:
  - Manually label a sample of pages as relevant / not relevant.  
  - Compute precision/recall for different thresholds to justify the chosen operating point.

Even with these limitations, the current semantic filtering layer already makes the crawler more selective and better aligned with the research topic than a simple keyword-based approach.



