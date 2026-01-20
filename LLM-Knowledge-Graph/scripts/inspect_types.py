import pandas as pd
import os

base_dir = r"d:\Universal-Web-Scraping-System-high-level-update\Universal-Web-Scraping-System-high-level-update-main\LLM-Knowledge-Graph\graphrag-project\output_partA_subset5"

def inspect_entities_type():
    path = os.path.join(base_dir, "entities.parquet")
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
    
    try:
        df = pd.read_parquet(path)
        print(f"\n--- Entity Types Distribution ---")
        print(df['type'].value_counts().to_string())
        
        print(f"\n--- Top 10 Entities ---")
        print(df[['title', 'type']].head(10).to_string())
    except Exception as e:
        print(f"Error reading entities: {e}")

inspect_entities_type()
