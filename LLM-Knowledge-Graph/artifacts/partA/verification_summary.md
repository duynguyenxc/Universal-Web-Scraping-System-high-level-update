## Part A (Education) - Verification Snapshot (this week)

### Corpus coverage

- **records (Richmond-28 target)**: 28
- **PDF-backed**: 20
- **URL-only**: 8
- **with DOI**: 27
- **with abstract** (used for URL-only ingestion): 20

### GraphRAG indexing artifacts

- output dir: `LLM-Knowledge-Graph/graphrag-project/output_partA_v2`
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
  "total_runtime": 75499.63916039467,
  "num_documents": 28,
  "update_documents": 0,
  "input_load_time": 0,
  "workflows": {
    "load_input_documents": {
      "overall": 0.09464025497436523
    },
    "create_base_text_units": {
      "overall": 0.3613717555999756
    },
    "create_final_documents": {
      "overall": 0.04265427589416504
    },
    "extract_graph": {
      "overall": 70811.71358704567
    },
    "finalize_graph": {
      "overall": 0.17974400520324707
    },
    "extract_covariates": {
      "overall": 3594.673085451126
    },
    "create_communities": {
      "overall": 0.2330927848815918
    },
    "create_final_text_units": {
      "overall": 0.09177827835083008
    },
    "create_community_reports": {
      "overall": 968.6127045154572
    },
    "generate_text_embeddings": {
      "overall": 123.63417887687683
    }
  }
}
```
