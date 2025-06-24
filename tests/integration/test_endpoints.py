import requests

print("Testing API endpoints...")

# Test auth endpoint
try:
    r = requests.get("https://api.trends.earth/auth/login", timeout=5)
    print(f"Auth endpoint GET: {r.status_code}")
except Exception as e:
    print(f"Auth endpoint error: {e}")

# Test API base
try:
    r = requests.get("https://api.trends.earth/api/v1", timeout=5)
    print(f"API base: {r.status_code}")
except Exception as e:
    print(f"API base error: {e}")

print("Done.")
