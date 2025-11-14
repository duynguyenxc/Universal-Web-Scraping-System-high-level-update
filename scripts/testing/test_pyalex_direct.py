"""Test pyalex directly to understand API"""
from pyalex import Works, config

# Set email
config.email = "test@example.com"

# Test simple search
works = Works()
results = works.search("reinforced concrete").get()

print(f"Type of results: {type(results)}")
print(f"Is iterator: {hasattr(results, '__iter__')}")

count = 0
for work in results:
    print(f"Work {count+1}: {work.get('title', 'N/A')[:60]}")
    count += 1
    if count >= 3:
        break

print(f"\nTotal found: {count}")

