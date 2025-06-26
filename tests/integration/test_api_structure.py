import requests

# Test possible API structures
test_urls = [
    "https://api.trends.earth/api/v1/",
    "https://api.trends.earth/v1/",
    "https://api.trends.earth/api/",
    "https://trends.earth/api/v1/",
    "https://trends.earth/api/",
]

for url in test_urls:
    try:
        r = requests.get(url, timeout=5)
        print(f"{url}: {r.status_code}")
        if r.status_code == 200:
            content = r.text[:200]
            print(f"  Content preview: {content}")
    except Exception as e:
        print(f"{url}: Error - {e}")

# Test for API documentation or endpoints
doc_urls = [
    "https://api.trends.earth/docs",
    "https://api.trends.earth/swagger",
    "https://api.trends.earth/api/docs",
    "https://api.trends.earth/api/swagger",
]

for url in doc_urls:
    try:
        r = requests.get(url, timeout=5)
        print(f"{url}: {r.status_code}")
    except Exception as e:
        print(f"{url}: Error - {e}")

print("Done.")
