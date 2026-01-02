## REPORT W49 — Microsoft GraphRAG local run + LLM-Knowledge-Graph integration (week wrap-up)

## (VI) Báo cáo tuần (W49) — Microsoft GraphRAG local run + LLM-Knowledge-Graph integration (week wrap-up)

### 1) Tuần này chúng ta đã làm được gì? (tóm tắt ngắn gọn)
- **Đã tải/cài và chạy được Microsoft GraphRAG trên máy local** (end-to-end indexing).
- **Đã tích hợp dữ liệu thu thập (JSONL theo ngày)** vào GraphRAG bằng cách chuyển đổi sang corpus text `*.txt`.
- **Đã chạy test thành công và tạo được output để demo**, đặc biệt là **Community Reports** (tóm tắt theo cụm/cluster) — đúng tinh thần GraphRAG.
- **Đã chuẩn hóa cách xem output**: xuất các file kỹ thuật (parquet) sang **Markdown dễ đọc** để trình bày/đánh giá nhanh.
- **Đã push code lên GitHub**, và tạo riêng một nhánh demo có kèm output để tiện “show” (nhánh `graphrag-output-demo`).

> Lưu ý: đây là **smoke test/feasibility test** để chứng minh “runnable + có output”, chưa phải đánh giá chất lượng khoa học cuối cùng.

---

### 2) Microsoft GraphRAG là gì? (paper/repo) và làm được gì?
**Microsoft GraphRAG** (theo paper “From Local to Global: A Graph RAG Approach to Query-Focused Summarization”, Edge et al., 2024) là một workflow RAG dựa trên **graph**:

- **Local (graph construction)**: từ văn bản → trích xuất **entities (nodes)** và **relationships (edges)**.
- **Global (hierarchical synthesis)**: chạy **community detection (Leiden)** để gom các node/edge thành **communities/clusters** (các “topic”), sau đó LLM viết **Community Reports** (tóm tắt cho từng cluster).
- **Query**: hỗ trợ kiểu truy vấn “big picture” (global search) dựa vào community reports + map/reduce, ngoài ra còn local/basic/drift search.

**Điểm nổi trội (so với KG phẳng / triple extraction thuần):**
- Không chỉ “pathfinding A→B”, mà có **cấu trúc chủ đề (clusters)** và **tóm tắt theo cụm** để trả lời câu hỏi “mơ hồ / tổng hợp”.
- Thích hợp để tìm **themes / contradictions / research gaps** ở mức toàn cục.

**Giới hạn thực tế (cần nói rõ):**
- Chất lượng phụ thuộc mạnh vào **ontology + prompt** (entity types/rules). Nếu chưa domain-specific thì sẽ có noise.
- Dễ gặp **rate-limit (429 TPM)** và chi phí tăng khi scale lên nhiều papers.
- Corpus quá nhỏ hoặc chạy chế độ “fast/NLP” có thể cho graph thưa và/hoặc fail ở một số bước.
- Output mặc định thiên về artefact kỹ thuật (`.parquet`, cache, vector store) → cần export ra dạng dễ đọc để review nhanh.

---

### 3) Cách tải/cài và tích hợp Microsoft GraphRAG vào local (chúng ta đã làm như thế nào)
Trong repo này, GraphRAG được chạy như một tool độc lập (CLI), không viết lại từ đầu.

- **Cài GraphRAG** (Python package `graphrag`).
- **Thiết lập API key** qua `.env`/biến môi trường `OPENAI_API_KEY` (file mẫu: `LLM-Knowledge-Graph/graphrag-project/env.example`).
- **Chuẩn bị input**:
  - Dữ liệu gốc: `LLM-Knowledge-Graph/data-from-S3-bucket/<YY-MM-DD>/corrosion_papers_<YY-MM-DD>.jsonl`
  - Chuyển đổi sang GraphRAG corpus: `LLM-Knowledge-Graph/graphrag-project/input/*.txt`
  - Script dùng để chuyển đổi: `LLM-Knowledge-Graph/scripts/graphrag_prepare_input.py`
- **Chạy indexing** bằng GraphRAG project config:
  - `LLM-Knowledge-Graph/graphrag-project/settings.yaml` (mặc định)
  - `LLM-Knowledge-Graph/graphrag-project/settings.lowrate.yaml` (giảm concurrency để ổn định, tránh 429)

---

### 4) Kiến trúc/pipeline/thuật toán của LLM-Knowledge-Graph hiện tại (có phải dùng cốt lõi Microsoft GraphRAG không?)
**Có.** Hiện tại “core pipeline” mà chúng ta chạy chính là **pipeline của Microsoft GraphRAG**.

Trong `LLM-Knowledge-Graph`, phần “của mình” chủ yếu là **wrapper/adapter** để:
- Chuẩn hóa input từ UWSS/JSONL → text corpus mà GraphRAG đọc được.
- Chạy GraphRAG ổn định (low-rate config + script).
- Export output ra dạng dễ đọc để review.

**Pipeline GraphRAG (khái quát):**
1) Load `input/*.txt` → chunking (text units)
2) `extract_graph` (LLM): entities + relationships
3) `create_communities` (Leiden): clustering/community hierarchy
4) `create_community_reports` (LLM): tóm tắt theo community
5) `generate_text_embeddings` (embeddings + vector store) để query

**Cấu trúc file quan trọng (bố cục hệ thống đang có):**
- `LLM-Knowledge-Graph/graphrag-project/`
  - `settings.yaml`: config GraphRAG chuẩn
  - `settings.lowrate.yaml`: config full, concurrency thấp (ổn định khi test)
  - `prompts/`: prompt cho extract graph, community report, query prompts, v.v.
- `LLM-Knowledge-Graph/scripts/`
  - `graphrag_prepare_input.py`: JSONL → `input/*.txt`
  - `graphrag_smoketest.ps1`: chạy nhanh (prepare → index → query). Có tham số `-OutDir` để output self-contained.
  - `graphrag_export_readable.py`: xuất output `.parquet` → `.md` dễ đọc
  - `show_graphrag_output.ps1`: wrapper để tạo `human_readable/*.md`
- `LLM-Knowledge-Graph/src/llm_kg/`: scaffold cho CLI/pipeline tương lai (hiện còn tối giản).

---

### 5) Output: có những file gì, ý nghĩa từng file, và cách xem/đánh giá chất lượng
#### 5.1. Nhấn mạnh: đây là chạy thử để kiểm chứng setup thành công
Output hiện tại là **demo run** (smoke test) với subset nhỏ (ví dụ 3 documents) nhằm chứng minh:
- GraphRAG chạy được local
- Có graph + communities + community reports

#### 5.2. Output nằm ở đâu?
- Output demo: `LLM-Knowledge-Graph/graphrag-project/output_meeting_std/`
- Bản “dễ đọc”: `LLM-Knowledge-Graph/graphrag-project/output_meeting_std/human_readable/`
- Nhánh GitHub demo chứa output để share: `graphrag-output-demo`

#### 5.3. Giải thích từng file output chính (GraphRAG)
Trong `output_meeting_std/` thường có:
- `documents.parquet`: danh sách documents sau khi load/chuẩn hóa
- `text_units.parquet`: các đoạn text sau chunking
- `entities.parquet`: entities (nodes)
- `relationships.parquet`: relationships (edges)
- `communities.parquet`: kết quả community detection (clusters)
- `community_reports.parquet`: **Community Reports** (tóm tắt theo cluster) — artefact quan trọng nhất
- `stats.json`: thống kê run (số doc, thời gian từng workflow)
- `indexing-engine.log`: log chi tiết

#### 5.4. Cách xem output cho người không chuyên (tránh đọc `.parquet`)
Vì `.parquet` khó đọc trực tiếp, ta xuất ra Markdown:
- `human_readable/community_reports.md`: **đọc để hiểu cluster nói về gì**
- `human_readable/entities.md`: xem nhanh entities (nodes)
- `human_readable/relationships.md`: xem nhanh edges
- `human_readable/documents.md`: xem list papers đã ingest
- `human_readable/communities.md`: xem community IDs/size/title
- `human_readable/stats.json`: xem run thành công hay chưa

#### 5.5. Kiểm định chất lượng: nhìn vào đâu để nhận định “ổn hay chưa?”
Vì ta chưa có ground-truth, việc “kiểm định chất lượng” tuần này nên là **qualitative + sanity checks**:

- **Sanity check 1 — Pipeline có chạy đủ không?**
  - Mở `stats.json`, kiểm tra `num_documents > 0` và có workflow `create_community_reports`.
- **Sanity check 2 — Community report có on-topic không?**
  - Đọc `human_readable/community_reports.md`:
    - Nếu cluster summaries nói về “corrosion / reinforced concrete / mitigation / test methods…” → on-topic.
    - Nếu ra các cụm kiểu “Crossref”, “publisher”, “metadata platform” → noise.
- **Sanity check 3 — Entities/relationships có hợp lý không?**
  - Mở `entities.md` và `relationships.md`:
    - entity types có đúng domain không hay bị generic (organization/person/event) quá nhiều?
    - quan hệ có “nói đúng ý” hay chỉ nối mơ hồ?

**Nhận định chất lượng hiện tại (đúng với kết quả demo):**
- **Có phần on-topic** (một số community summaries liên quan corrosion/RC).
- **Có noise** (ví dụ “Crossref” xuất hiện như entity/topic) do ontology/entity types đang baseline.

**Cải thiện như thế nào (hướng tuần sau):**
- Tăng số lượng papers (scale dần) để clusters “đủ lớn” và ổn định hơn.
- Thiết kế ontology domain-specific + prompt tuning để giảm noise.
- Thêm rules loại bỏ “data platform/source” (Crossref/OpenAlex/…) khỏi entity types (hoặc hạ trọng số).

---

### 6) Ontology hiện tại đang dùng là gì? Vì sao dùng (và vì sao chưa làm domain-specific ngay)?
Hiện tại ontology đang ở dạng **baseline** theo cấu hình GraphRAG trong `settings.yaml` / `settings.lowrate.yaml`:
- `extract_graph.entity_types: [organization, person, geo, event]`

**Vì sao dùng baseline trước?**
- Mục tiêu tuần này là **make it runnable** và tạo output để chứng minh pipeline hoạt động.
- Ontology domain-specific cần vòng lặp **human-in-the-loop** (đọc community reports → chỉnh prompt/type → chạy lại). Đây là phần thầy nói sẽ làm sau khi runnable.

**Ontology dự kiến (tuần sau) cho domain corrosion/concrete deterioration:**
- Ví dụ entity types: `corrosion_mechanism`, `mitigation_method`, `inhibitor`, `material`, `environment`, `test_method`, `performance_metric`, `structure_component`
- Cần cập nhật prompts và chạy `graphrag prompt-tune` trên subset nhỏ, rồi chỉnh tay.

---

### 7) Hướng dẫn cách chạy (local)
Trong thư mục `LLM-Knowledge-Graph/`:

1) Chuẩn bị input từ dữ liệu theo ngày:
- `python scripts/graphrag_prepare_input.py --day 25-12-06 --max-docs 30 --clean`

2) Chạy GraphRAG indexing (ổn định):
- `graphrag index --root graphrag-project --config graphrag-project/settings.lowrate.yaml --method standard`

3) Xuất output ra Markdown dễ đọc:
- `powershell -ExecutionPolicy Bypass -File scripts/show_graphrag_output.ps1 -OutDir \"graphrag-project/output_meeting_std\" -N 20`

> Tip: dùng `scripts/graphrag_smoketest.ps1` để chạy nhanh một chuỗi (prepare → index → query), có tham số `-OutDir` để output self-contained.

---

### 8) Kết luận: Microsoft GraphRAG có phù hợp với mục tiêu dự án không?
**Kết luận tuần này (feasibility):** Microsoft GraphRAG **phù hợp và khả thi** để làm nền cho dự án LLM-Knowledge-Graph, vì:
- Đã chạy được local và tạo được artefact cốt lõi của GraphRAG (communities + community reports).
- Kiến trúc “local-to-global” đúng với mục tiêu discovery (big-picture synthesis).

**Nhưng chưa thể khẳng định 100% chỉ với 1 demo nhỏ.** Cách trả lời “khôn ngoan”:
- GraphRAG là nền chính để tiếp tục.
- Tuần sau sẽ:
  - scale lên nhiều papers hơn
  - làm ontology/prompt tuning để nâng chất lượng
  - đồng thời tiếp tục quan sát xem có cần thêm tool khác (visualization, evaluation, graph store/query engine, full-text extraction, v.v.) để hoàn thiện platform hay không.

---

## (EN) REPORT W49 — Microsoft GraphRAG local run + LLM-Knowledge-Graph integration (week wrap-up)

### 1) What we accomplished this week (short summary)
- **Installed and ran Microsoft GraphRAG locally** (end-to-end indexing).
- **Integrated our harvested data (daily JSONL exports)** into GraphRAG by converting them into a `*.txt` text corpus.
- **Completed a successful test run and produced demo outputs**, especially **Community Reports** (cluster/community summaries) — the key GraphRAG artifact.
- **Standardized output review** by exporting technical artifacts (parquet) into **human-readable Markdown** for quick inspection/presentation.
- **Pushed code to GitHub**, and created a dedicated demo branch that includes outputs for easy sharing (branch `graphrag-output-demo`).
> Note: this is a **smoke/feasibility test** to prove “runnable + outputs exist”, not a final scientific-quality evaluation.

---

### 2) What is Microsoft GraphRAG (paper/repo) and what can it do?
**Microsoft GraphRAG** (based on the paper “From Local to Global: A Graph RAG Approach to Query-Focused Summarization”, Edge et al., 2024) is a graph-based RAG workflow:

- **Local (graph construction)**: from text → extract **entities (nodes)** and **relationships (edges)**.
- **Global (hierarchical synthesis)**: apply **Leiden community detection** to group the graph into **communities/clusters (topics)**, then use an LLM to write **Community Reports** (summaries per cluster).
- **Query**: supports “big picture” global search using community reports + map/reduce, in addition to local/basic/drift search.

**Key advantages (vs. flat KG / triple extraction only):**
- Not just pathfinding (A→B), but **topic structure (clusters)** and **cluster-level summaries** for vague/high-level questions.
- Better suited for **themes / contradictions / research gaps** at a corpus level.

**Practical limitations:**
- Quality depends heavily on **ontology + prompts** (entity types/rules). Without domain-specific tuning, noise appears.
- **Rate limits (429 TPM)** and cost increase when scaling to large corpora.
- Very small corpora or “fast/NLP” mode can yield sparse graphs and/or fail in some steps.
- Default outputs are technical artifacts (`.parquet`, cache, vector store), so exporting to readable formats is necessary for review.

---

### 3) How we installed and integrated GraphRAG locally
In this repo, GraphRAG is used as an external tool (CLI); we are not rebuilding it from scratch.

- **Install GraphRAG** (Python package `graphrag`).
- **Set API key** via `.env` / `OPENAI_API_KEY` (template: `LLM-Knowledge-Graph/graphrag-project/env.example`).
- **Prepare inputs**:
  - Source data: `LLM-Knowledge-Graph/data-from-S3-bucket/<YY-MM-DD>/corrosion_papers_<YY-MM-DD>.jsonl`
  - Convert to GraphRAG corpus: `LLM-Knowledge-Graph/graphrag-project/input/*.txt`
  - Conversion script: `LLM-Knowledge-Graph/scripts/graphrag_prepare_input.py`
- **Run indexing** with GraphRAG configs:
  - `LLM-Knowledge-Graph/graphrag-project/settings.yaml` (default)
  - `LLM-Knowledge-Graph/graphrag-project/settings.lowrate.yaml` (low concurrency for stability)

---

### 4) Current architecture/pipeline/algorithm of LLM-Knowledge-Graph (are we using GraphRAG core?)
**Yes.** The “core pipeline” we are executing is **the Microsoft GraphRAG pipeline**.

Our custom work in `LLM-Knowledge-Graph` is mainly an **adapter/wrapper layer**:
- convert UWSS/JSONL → GraphRAG-readable text corpus
- run GraphRAG stably (low-rate config + scripts)
- export outputs into readable files

**GraphRAG pipeline (high level):**
1) Load `input/*.txt` → chunking (text units)
2) `extract_graph` (LLM): entities + relationships
3) `create_communities` (Leiden): community detection
4) `create_community_reports` (LLM): community summaries
5) `generate_text_embeddings` (embeddings + vector store) for query

**Project file layout (what each part does):**
- `LLM-Knowledge-Graph/graphrag-project/`
  - `settings.yaml`, `settings.lowrate.yaml`
  - `prompts/` (GraphRAG prompts)
- `LLM-Knowledge-Graph/scripts/`
  - `graphrag_prepare_input.py`
  - `graphrag_smoketest.ps1` (supports `-OutDir` for self-contained outputs)
  - `graphrag_export_readable.py`
  - `show_graphrag_output.ps1`
- `LLM-Knowledge-Graph/src/llm_kg/`: minimal scaffold for future pipeline/CLI.

---

### 5) Outputs: what files exist, what they mean, and how to review quality
#### 5.1. Reminder: this is a setup validation run
The current outputs are from a **demo run** (smoke test) on a small subset (e.g., 3 documents) to prove:
- GraphRAG runs locally
- graph + communities + community reports are generated

#### 5.2. Where are outputs stored?
- Demo output: `LLM-Knowledge-Graph/graphrag-project/output_meeting_std/`
- Readable exports: `LLM-Knowledge-Graph/graphrag-project/output_meeting_std/human_readable/`
- GitHub demo branch containing outputs: `graphrag-output-demo`

#### 5.3. Meaning of key output files
- `documents.parquet`: normalized document table
- `text_units.parquet`: chunked text units
- `entities.parquet`: extracted entities (nodes)
- `relationships.parquet`: extracted relations (edges)
- `communities.parquet`: Leiden communities (clusters)
- `community_reports.parquet`: **community summaries** (key artifact)
- `stats.json`: run statistics
- `indexing-engine.log`: detailed logs

#### 5.4. How to read outputs (avoid direct parquet inspection)
Use the exported Markdown files:
- `human_readable/community_reports.md` (primary)
- `human_readable/entities.md`
- `human_readable/relationships.md`
- `human_readable/documents.md`
- `human_readable/communities.md`
- `human_readable/stats.json`

#### 5.5. Quality checks (how to judge “good or not” without ground truth)
- **Check 1 — Did the pipeline complete?** (`stats.json`: `num_documents > 0` and `create_community_reports` present)
- **Check 2 — Are community summaries on-topic?** (read `community_reports.md`)
- **Check 3 — Are entities/relations reasonable?** (`entities.md`, `relationships.md`)

Current qualitative result:
- partially on-topic communities exist
- noise exists (e.g., “Crossref”) due to baseline ontology

Next improvements:
- scale up corpus size gradually
- implement domain-specific ontology + prompt tuning
- downweight/filter data-platform entities

---

### 6) Current ontology and why we used it
Current baseline ontology in config:
- `extract_graph.entity_types: [organization, person, geo, event]`

Reason for baseline first:
- this week’s goal was **runnable validation**
- domain ontology requires **human-in-the-loop** iterations (review reports → tune prompts/types → re-index)

Planned domain ontology (next week):
- e.g., `corrosion_mechanism`, `mitigation_method`, `inhibitor`, `material`, `environment`, `test_method`, `performance_metric`, `structure_component`

---

### 7) How to run (local)
From `LLM-Knowledge-Graph/`:

1) Prepare input:
- `python scripts/graphrag_prepare_input.py --day 25-12-06 --max-docs 30 --clean`

2) Index:
- `graphrag index --root graphrag-project --config graphrag-project/settings.lowrate.yaml --method standard`

3) Export readable output:
- `powershell -ExecutionPolicy Bypass -File scripts/show_graphrag_output.ps1 -OutDir \"graphrag-project/output_meeting_std\" -N 20`

---

### 8) Conclusion: is GraphRAG suitable for our project?
**This week’s feasibility conclusion:** Microsoft GraphRAG is **suitable and viable** as the base framework because:
- it runs locally and produces the key GraphRAG artifacts (communities + community reports)
- the local-to-global design aligns with our “discovery” goal

However, we should not claim 100% final success from a small demo:
- keep GraphRAG as the primary base
- next week: scale up, design domain ontology, tune prompts, re-index
- continue to evaluate whether additional tools are needed later (visualization, evaluation, full-text extraction, etc.)
