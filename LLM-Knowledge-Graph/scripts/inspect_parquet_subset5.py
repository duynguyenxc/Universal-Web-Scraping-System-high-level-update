import pandas as pd
import os

base_dir = r"d:\Universal-Web-Scraping-System-high-level-update\Universal-Web-Scraping-System-high-level-update-main\LLM-Knowledge-Graph\graphrag-project\output_partA_subset5"

def inspect_parquet(filename, columns=None):
    path = os.path.join(base_dir, filename)
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
    
    try:
        df = pd.read_parquet(path)
        print(f"\n--- Inspecting {filename} ---")
        print(f"Shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")
        if columns:
            # Check if columns exist
            valid_cols = [c for c in columns if c in df.columns]
            print(df[valid_cols].head(10).to_string())
        else:
            print(df.head(5).to_string())
    except Exception as e:
        print(f"Error reading {filename}: {e}")

print("STARTING INSPECTION...")

# Inspect Entities
# Note: 'title' is usually the name in GraphRAG outputs, sometimes 'name'
inspect_parquet("entities.parquet", ["title", "type", "description"])

# Inspect Community Reports
inspect_parquet("community_reports.parquet", ["title", "summary", "rating"])

# Inspect Relationships
inspect_parquet("relationships.parquet", ["source", "target", "description"])
