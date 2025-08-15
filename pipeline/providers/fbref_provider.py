from __future__ import annotations
import time
import requests, pandas as pd
from bs4 import BeautifulSoup
from utils import read_toml, utcnow_str, write_json

FBREF_BASE = "https://fbref.com"
EPL_2024_SQUAD_SHOOTING = "/en/comps/9/2024/shooting/players/2024-2025-Premier-League-Stats"
EPL_FALLBACK = "/en/comps/9/shooting/players"  # broader listing; still contains xG/xAG columns

class FBRefProvider:
    def __init__(self, config_path: str = "configs/config.toml"):
        self.cfg = read_toml(config_path)
        ua = self.cfg.get("user_agent", {}).get("value", "Mozilla/5.0")
        self.headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": FBREF_BASE + "/en/",
        }
        self.timeout = int(self.cfg.get("network", {}).get("timeout_seconds", 25))

    def _get_html_with_retry(self, path: str) -> str:
        s = requests.Session()
        s.headers.update(self.headers)
        urls = [FBREF_BASE + path, FBREF_BASE + EPL_FALLBACK]
        last = None
        for url in urls:
            for attempt in range(4):
                r = s.get(url, timeout=self.timeout)
                if r.status_code == 200:
                    return r.text
                if r.status_code == 403:
                    # gentle backoff then retry
                    time.sleep(1.5 * (attempt + 1))
                    continue
                last = r
            # try the next URL if first one kept failing
        if last is not None:
            last.raise_for_status()
        raise RuntimeError("FBref: unable to fetch page")

    def fetch_players(self):
        html = self._get_html_with_retry(EPL_2024_SQUAD_SHOOTING)
        soup = BeautifulSoup(html, "lxml")
        tables = pd.read_html(str(soup), flavor="lxml")

        shoot = None
        for t in tables:
            # flatten multiindex if present and normalize
            if hasattr(t.columns, "get_level_values"):
                cols = [str(c).lower() for c in t.columns.get_level_values(-1)]
            else:
                cols = [str(c).lower() for c in t.columns]
            if "xg" in cols and ("xag" in cols or "xa" in cols):
                shoot = t
                break
        if shoot is None:
            raise RuntimeError("FBref: xG/xAG table not found")

        shoot.columns = ["_".join([str(x) for x in col if str(x) != ""]) if isinstance(col, tuple) else str(col) for col in shoot.columns.values]
        shoot = shoot.rename(columns=lambda c: c.strip().replace(" ", "_").lower())

        data = shoot.to_dict(orient="records")
        ts = utcnow_str(self.cfg.get("caching", {}).get("timestamp_format", "%Y-%m-%dT%H-%M-%SZ"))
        write_json(data, f"data/raw/xgxa_fbref_{ts}.json")
        return {"players": data}
