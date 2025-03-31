import requests
import random
import string
import json

API_URL = "http://localhost:8000"
NUM_USERS = 100
NUM_LINKS_PER_USER = 2
PASSWORD = "123456"

users = []
aliases = []

def random_email():
    return f"user_{''.join(random.choices(string.ascii_lowercase, k=6))}@test.com"

def register_user(email):
    r = requests.post(f"{API_URL}/auth/register", json={
        "email": email,
        "password": PASSWORD
    })
    if r.status_code == 200:
        print(f"Registered: {email}")
        return r.json()["access_token"]
    elif r.status_code == 400 and "registered" in r.text:
        r = requests.post(f"{API_URL}/auth/login", data={
            "username": email,
            "password": PASSWORD
        })
        if r.status_code == 200:
            print(f"Logged in: {email}")
            return r.json()["access_token"]
    print(f"Failed for: {email}")
    return None

def create_links(token):
    headers = {"Authorization": f"Bearer {token}"}
    links = []
    for _ in range(NUM_LINKS_PER_USER):
        long_url = "https://example.com/" + ''.join(random.choices(string.ascii_lowercase, k=10))
        r = requests.post(f"{API_URL}/links/shorten", json={"url": long_url}, headers=headers)
        if r.status_code == 200:
            alias = r.json()["url"]
            links.append(alias)
            aliases.append(alias)
    return links

# Шаг 1: регистрация пользователей и генерация ссылок
for _ in range(NUM_USERS):
    email = random_email()
    token = register_user(email)
    if token:
        links = create_links(token)
        users.append({"email": email, "password": PASSWORD, "aliases": links})

# Шаг 2: сохранение в JSON
with open("tests/load/users.json", "w") as f:
    json.dump(users, f, indent=2)

with open("tests/load/aliases.json", "w") as f:
    json.dump(aliases, f, indent=2)

print(f"\n Created {len(users)} users and {len(aliases)} links.")
