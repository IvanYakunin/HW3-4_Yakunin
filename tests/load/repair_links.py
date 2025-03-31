import requests
import json
import random
import string

API_URL = "http://localhost:8000"
HEADERS = {}  # Анонимно

with open("tests/load/aliases.json") as f:
    aliases = json.load(f)

def is_alias_alive(alias: str) -> bool:
    r = requests.get(f"{API_URL}/links/{alias}/stats")
    return r.status_code == 200

def random_url():
    return "https://testsite.com/" + ''.join(random.choices(string.ascii_lowercase, k=10))

restored = 0

for alias in aliases:
    if is_alias_alive(alias):
        print(f"Alias exists: {alias}")
        continue

    print(f"🔁 Restoring alias: {alias}")

    r = requests.post(f"{API_URL}/links/shorten", json={
        "url": random_url(),
        "alias": alias
    }, headers=HEADERS)

    if r.status_code == 200:
        print(f"  Created: {alias}")
        restored += 1
    elif r.status_code == 409:
        print(f"  Already exists (race?): {alias}")
    else:
        print(f"  Failed to create {alias}: {r.status_code} — {r.text}")

print(f"\n🔧 Total restored: {restored} of {len(aliases)}")
