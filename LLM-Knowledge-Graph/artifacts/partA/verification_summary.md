## Part A (Education) - Verification Snapshot (this week)

### Corpus coverage

- **records (Richmond-28 target)**: 28
- **PDF-backed**: 20
- **URL-only**: 8
- **with DOI**: 27
- **with abstract** (used for URL-only ingestion): 20

### GraphRAG indexing artifacts

- output dir: `graphrag-project/output_partA`
- documents.parquet: YES
- text_units.parquet: YES
- entities.parquet: YES
- relationships.parquet: YES
- communities.parquet: YES
- community_reports.parquet: YES
- claims.parquet: NO
- covariates.parquet: YES

### stats.json (raw)

```json
{
  "total_runtime": 5761.824764728546,
  "num_documents": 28,
  "update_documents": 0,
  "input_load_time": 0,
  "workflows": {
    "load_input_documents": {
      "overall": 0.3582332134246826
    },
    "create_base_text_units": {
      "overall": 0.4307527542114258
    },
    "create_final_documents": {
      "overall": 0.051291704177856445
    },
    "extract_graph": {
      "overall": 2446.320554494858
    },
    "finalize_graph": {
      "overall": 0.14610767364501953
    },
    "extract_covariates": {
      "overall": 1889.661578655243
    },
    "create_communities": {
      "overall": 0.18398761749267578
    },
    "create_final_text_units": {
      "overall": 0.1439054012298584
    },
    "create_community_reports": {
      "overall": 1355.1443281173706
    },
    "generate_text_embeddings": {
      "overall": 69.38402509689331
    }
  }
}
```
