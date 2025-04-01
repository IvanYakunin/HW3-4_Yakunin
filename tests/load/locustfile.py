from locust import HttpUser, task, between, events
import random
import json
import requests

# Глобальный список ссылок, доступный всем пользователям
global_aliases = []


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("Generating links")

    for i in range(10):
        payload = {
            "url": f"https://example.com/test-{i}",
            "alias": f"alias{i}"
        }

        try:
            response = requests.post("http://localhost:8000/links/shorten", json=payload)
            if response.status_code == 200:
                alias = response.json()["url"]
                global_aliases.append(alias)
            elif response.status_code == 409:
                # Если alias уже существует, всё равно добавляем его
                alias = payload["alias"]
                global_aliases.append(alias)
                print(f"Alias '{alias}' already exists, added anyway.")
            else:
                print(f"Failed to create alias{i}: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error while creating alias{i}: {e}")

    print(f"Prepared aliases: {global_aliases}")


class UrlShortenerUser(HttpUser):
    wait_time = between(1, 3)

    @task(1)
    def test_redirect(self):
        if global_aliases:
            short_code = random.choice(global_aliases)
            with self.client.get(f"/links/{short_code}", allow_redirects=False, catch_response=True) as resp:
                if resp.status_code != 302:
                    resp.failure(f"Expected 302 but got {resp.status_code}: {resp.text}")


    @task(1)
    def test_stats(self):
        if global_aliases:
            short_code = random.choice(global_aliases)
            self.client.get(f"/links/{short_code}/stats")

    @task(1)
    def test_search(self):
        idx = random.randint(0, 9)
        original_url = f"https://example.com/test-{idx}"
        self.client.get(f"/links/search", params={"original_url": original_url})
