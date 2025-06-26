import requests

print("Testing root domain...")

try:
    r = requests.get("https://api.trends.earth/", timeout=5)
    print(f"Root domain: {r.status_code}")
    if r.status_code == 200:
        print("Response content:", r.text[:500])
except Exception as e:
    print(f"Root domain error: {e}")

# Test different possible auth endpoints
auth_endpoints = [
    "https://api.trends.earth/auth/login",
    "https://api.trends.earth/api/auth/login",
    "https://api.trends.earth/login",
    "https://api.trends.earth/api/login",
    "https://api.trends.earth/api/v1/auth/login",
]

for endpoint in auth_endpoints:
    try:
        r = requests.get(endpoint, timeout=5)
        print(f"{endpoint}: {r.status_code}")
        if r.status_code != 404:
            break
    except Exception as e:
        print(f"{endpoint}: Error - {e}")

print("Done.")
