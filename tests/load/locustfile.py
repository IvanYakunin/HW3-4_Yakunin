from locust import HttpUser, task, between
import random
import json

with open("tests/load/aliases.json") as f:
    ALIASES = json.load(f)

with open("tests/load/users.json") as f:
    USERS = json.load(f)

def random_url():
    return "https://example.com/" + ''.join(random.choices("abcdefghijklmnopqrstuvwxyz", k=10))

def safe_json(response):
    try:
        return response.json()
    except Exception:
        return {}

class BaseUser(HttpUser):
    wait_time = between(0.5, 2)

    @task(2)
    def visit_link(self):
        alias = random.choice(ALIASES)
        self.client.get(f"/links/{alias}")

    @task(1)
    def get_stats(self):
        alias = random.choice(ALIASES)
        self.client.get(f"/links/{alias}/stats")

class AnonymousUser(BaseUser):
    @task(2)
    def create_short_url(self):
        url = random_url()
        self.client.post("/links/shorten", json={"url": url})

class AuthUser(BaseUser):
    def on_start(self):
        user = random.choice(USERS)
        r = self.client.post("/auth/login", data={
            "username": user["email"],
            "password": user["password"]
        })
        data = safe_json(r)
        token = data.get("access_token")
        self.headers = {"Authorization": f"Bearer {token}"}
        self.own_aliases = user["aliases"]

    @task(2)
    def create_short_url(self):
        url = random_url()
        r = self.client.post("/links/shorten", json={"url": url}, headers=self.headers)
        if r.status_code == 200:
            self.own_aliases.append(r.json()["url"])

    @task(1)
    def delete_link(self):
        if self.own_aliases:
            alias = random.choice(self.own_aliases)
            r = self.client.delete(f"/links/{alias}", headers=self.headers)

            if r.status_code == 200:
                print(f"🗑️ Deleted: {alias}")
                self.own_aliases.remove(alias)
                if alias in ALIASES:
                    ALIASES.remove(alias)
            else:
                print(f"Failed to delete {alias}: {r.status_code}")
