"""Show OpenAlex education test results."""

import json

def show_results():
    print("=== OPENALEX EDUCATION TEST RESULTS ===\n")

    try:
        with open('data/openalex_education_results.jsonl', 'r', encoding='utf-8') as f:
            records = []
            for line in f:
                records.append(json.loads(line))

        print(f"Total records: {len(records)}\n")

        # Statistics
        abstracts = sum(1 for r in records if r.get('abstract'))
        pdfs = sum(1 for r in records if r.get('pdf_url'))
        dois = sum(1 for r in records if r.get('doi'))

        print("Statistics:")
        print(f"  Records with abstracts: {abstracts} ({abstracts/len(records)*100:.1f}%)")
        print(f"  Records with PDF URLs: {pdfs} ({pdfs/len(records)*100:.1f}%)")
        print(f"  Records with DOIs: {dois} ({dois/len(records)*100:.1f}%)")
        print()

        # Sample records
        print("Sample Records:")
        for i, record in enumerate(records[:5], 1):
            print(f"\n{i}. Title: {record.get('title', 'N/A')[:80]}...")
            print(f"   DOI: {record.get('doi', 'N/A')}")
            print(f"   Year: {record.get('year', 'N/A')}")
            print(f"   Abstract: {'Yes' if record.get('abstract') else 'No'}")
            print(f"   PDF URL: {'Yes' if record.get('pdf_url') else 'No'}")
            print(f"   Source: {record.get('source', 'N/A')}")

    except FileNotFoundError:
        print("❌ File not found: data/openalex_education_results.jsonl")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    show_results()
