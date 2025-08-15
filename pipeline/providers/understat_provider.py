
from __future__ import annotations
import asyncio, aiohttp, json, re
from utils import read_toml, utcnow_str, write_json

UNDERSTAT_LEAGUE_URL = "https://understat.com/league/EPL/{season}"
PLAYERS_RE = re.compile(r"var\s+playersData\s*=\s*JSON.parse\('([^']+)'\);", re.MULTILINE)

class UnderstatProvider:
    def __init__(self, config_path: str = "configs/config.toml"):
        self.cfg = read_toml(config_path)
        self.headers = {"User-Agent": self.cfg.get("user_agent", {}).get("value", "FPL-Analytics/Advanced")}

    async def _fetch_text(self, session: aiohttp.ClientSession, url: str) -> str:
        async with session.get(url, headers=self.headers, timeout=self.cfg.get("network", {}).get("timeout_seconds", 25)) as r:
            r.raise_for_status()
            return await r.text()

    async def fetch_players(self, season: int):
        url = UNDERSTAT_LEAGUE_URL.format(season=season)
        timeout = aiohttp.ClientTimeout(total=self.cfg.get("network", {}).get("timeout_seconds", 25))
        async with aiohttp.ClientSession(timeout=timeout) as session:
            html = await self._fetch_text(session, url)
        m = PLAYERS_RE.search(html)
        if not m:
            raise RuntimeError("Understat: playersData not found")
        encoded = m.group(1)
        decoded = encoded.encode("utf-8").decode("unicode_escape")
        data = json.loads(decoded)
        # cache raw
        ts = utcnow_str(self.cfg.get("caching", {}).get("timestamp_format", "%Y-%m-%dT%H-%M-%SZ"))
        write_json(data, f"data/raw/xgxa_understat_{ts}.json")
        return data
