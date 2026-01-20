import pandas as pd
import os

base_dir = r"d:\Universal-Web-Scraping-System-high-level-update\Universal-Web-Scraping-System-high-level-update-main\LLM-Knowledge-Graph\graphrag-project\output_partA_subset5"

path = os.path.join(base_dir, "community_reports.parquet")
try:
    df = pd.read_parquet(path)
    print("--- FIRST COMMUNITY REPORT ---")
    print("TITLE:", df.iloc[0]['title'])
    print("SUMMARY:", df.iloc[0]['summary'])
except Exception as e:
    print(e)
