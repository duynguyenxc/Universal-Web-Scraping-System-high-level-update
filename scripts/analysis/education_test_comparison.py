"""Compare OpenAlex performance between corrosion and education topics."""

import sqlite3
import yaml

def compare_topics():
    print("=== OPENALEX TOPIC COMPARISON ===\n")

    # Load both configs
    with open('config/config.yaml', 'r') as f:
        corrosion_config = yaml.safe_load(f)

    with open('config_education.yaml', 'r') as f:
        education_config = yaml.safe_load(f)

    print("Topic Comparison:")
    print(f"Corrosion keywords: {len(corrosion_config.get('domain_keywords', []))}")
    print(f"Education keywords: {len(education_config.get('domain_keywords', []))}")
    print(f"Corrosion year filter: {corrosion_config.get('year_filter', 'None')}")
    print(f"Education year filter: {education_config.get('year_filter', 'None')}")
    print()

    # Check corrosion results
    try:
        conn_corrosion = sqlite3.connect('data/test_new_sources.sqlite')
        cursor_corrosion = conn_corrosion.cursor()
        cursor_corrosion.execute("SELECT COUNT(*) FROM documents WHERE source = 'openalex'")
        corrosion_count = cursor_corrosion.fetchone()[0]
        conn_corrosion.close()
    except:
        corrosion_count = 0

    # Check education results
    try:
        conn_education = sqlite3.connect('data/test_openalex_education.sqlite')
        cursor_education = conn_education.cursor()
        cursor_education.execute("SELECT COUNT(*) FROM documents")
        education_count = cursor_education.fetchone()[0]

        # Get sample education records
        cursor_education.execute("SELECT title, abstract, doi, year FROM documents LIMIT 3")
        education_samples = cursor_education.fetchall()
        conn_education.close()
    except:
        education_count = 0
        education_samples = []

    print("RESULTS:")
    print(f"OpenAlex + Corrosion topic: {corrosion_count} records")
    print(f"OpenAlex + Education topic: {education_count} records")
    print()

    if education_samples:
        print("Sample Education Records:")
        for i, (title, abstract, doi, year) in enumerate(education_samples, 1):
            print(f"\n{i}. Title: {title[:60]}...")
            print(f"   Abstract: {'Yes' if abstract else 'No'}")
            print(f"   DOI: {doi or 'None'}")
            print(f"   Year: {year or 'None'}")

    print("\nCONCLUSION:")
    if education_count > corrosion_count:
        print("[SUCCESS] OpenAlex WORKS with education topic!")
        print("[CONFIRMED] Problem was topic-specific, not API integration")
    else:
        print("[FAIL] OpenAlex still has issues even with education")
        print("[INVESTIGATE] Problem might be broader than topic selection")

if __name__ == "__main__":
    compare_topics()
