
from __future__ import annotations
import httpx
BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
FIXTURES_URL = "https://fantasy.premierleague.com/api/fixtures/"
class FPLClient:
    def __init__(self, timeout=25, headers=None):
        self.client = httpx.Client(timeout=timeout, headers=headers or {"User-Agent":"FPL-Analytics"})
    def get_json(self, url):
        r = self.client.get(url); r.raise_for_status(); return r.json()
    def get_bootstrap(self): return self.get_json(BOOTSTRAP_URL)
    def get_fixtures(self): return self.get_json(FIXTURES_URL)
