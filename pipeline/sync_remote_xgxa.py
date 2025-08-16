from __future__ import annotations
import os, sys, requests

RAW_URL = os.environ.get("XGXA_REMOTE_CSV",
    "https://raw.githubusercontent.com/Willo-1982/fpl-analytics-advanced/main/data/cache/xgxa_players.csv"
)
OUT_PATH = "data/cache/xgxa_players.csv"

def main():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    print(f"Downloading: {RAW_URL}")
    r = requests.get(RAW_URL, timeout=30, headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    with open(OUT_PATH, "wb") as f:
        f.write(r.content)
    print(f"Wrote: {OUT_PATH} ({len(r.content)} bytes)")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Remote sync failed:", e)
        sys.exit(1)
