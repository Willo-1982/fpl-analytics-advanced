
from __future__ import annotations
import argparse, asyncio, json, os
import pandas as pd
import numpy as np
from utils import read_toml
from mapping import build_player_mapping

def load_fpl_cache():
    with open("data/cache/bootstrap-static.json","r",encoding="utf-8") as f:
        bs = json.load(f)
    players = pd.DataFrame(bs["elements"])
    teams = pd.DataFrame(bs["teams"])[["id","name"]].rename(columns={"id":"team","name":"team_name"})
    players = players.merge(teams, on="team", how="left")
    return players

async def fetch_understat(cfg):
    from providers.understat_provider import UnderstatProvider
    prov = UnderstatProvider()
    raw = await prov.fetch_players(cfg.get("xgxa",{}).get("season", 2024))

    rows = []
    if isinstance(raw, dict):
        iterable = raw.values()
    elif isinstance(raw, list):
        iterable = raw
    else:
        raise RuntimeError(f"Understat: unexpected data type {type(raw)}")

    for p in iterable:
        rows.append({
            "provider": "understat",
            "player_name": p.get("player_name") or p.get("PLAYER_NAME") or "",
            "team_name": p.get("team_title") or p.get("TEAM_TITLE") or "",
            "minutes": float(p.get("time", 0) or p.get("TIME", 0) or 0),
            "xg": float(p.get("xG", 0) or p.get("xg", 0) or 0),
            "xa": float(p.get("xA", 0) or p.get("xa", 0) or 0),
            "shots": float(p.get("shots", 0) or p.get("SHOTS", 0) or 0),
        })
    return pd.DataFrame(rows)

def fetch_fbref(cfg):
    from providers.fbref_provider import FBRefProvider
    prov = FBRefProvider()
    raw = prov.fetch_players()
    rows = []
    for rec in raw["players"]:
        rows.append({
            "provider": "fbref",
            "player_name": rec.get("Player", rec.get("player", "")),
            "team_name": rec.get("Squad", rec.get("squad", "")),
            "minutes": float(rec.get("min", rec.get("Min", 0)) or 0),
            "xg": float(rec.get("xg", rec.get("Expected_xG", 0)) or 0),
            "xa": float(rec.get("xag", rec.get("Expected_xAG", 0)) or 0),
            "shots": float(rec.get("sh", rec.get("Sh", 0)) or 0),
        })
    return pd.DataFrame(rows)

def compute_rates(df: pd.DataFrame, min_minutes: int) -> pd.DataFrame:
    df = df.copy()
    df["minutes"] = pd.to_numeric(df["minutes"], errors="coerce").fillna(0)
    df = df[df["minutes"] >= float(min_minutes)]
    per90 = (df["minutes"] / 90.0).replace(0, np.nan)
    df["xg_per90"] = df["xg"] / per90
    df["xa_per90"] = df["xa"] / per90
    return df.replace([np.inf, -np.inf], np.nan).fillna(0.0)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/config.toml")
    ap.add_argument("--season", type=int)
    args = ap.parse_args()

    cfg = read_toml(args.config)
    provider = cfg.get("xgxa", {}).get("provider", "understat").lower()
    if args.season is not None:
        cfg["xgxa"]["season"] = args.season

    df_fpl = load_fpl_cache()

    try:
        if provider == "understat":
            df_prov = asyncio.run(fetch_understat(cfg))
        else:
            df_prov = fetch_fbref(cfg)
    except Exception as e:
        print("Phase 2 warning:", e)
        print("Falling back to an empty xG/xA file so you can proceed.")
        os.makedirs("data/cache", exist_ok=True)
        pd.DataFrame(columns=["fpl_id","fpl_name","xg_per90","xa_per90"]).to_csv("data/cache/xgxa_players.csv", index=False)
        return

    df_prov = compute_rates(df_prov, cfg.get("xgxa", {}).get("min_minutes", 180))

    # Map provider names to FPL players
    df_prov["name"] = df_prov["player_name"].astype(str)
    df_map = build_player_mapping(df_fpl, df_prov.rename(columns={"name":"provider_name"}), "provider_name")

    # Simple join on normalized name
    df_prov["name_norm"] = df_prov["player_name"].str.lower().str.replace("-", " ", regex=False).str.replace(".", "", regex=False).str.strip()
    df_map["provider_match_name_norm"] = df_map["provider_match_name"].str.lower().str.strip()
    joined = df_map.merge(df_prov, left_on="provider_match_name_norm", right_on="name_norm", how="left")

    out = joined[["fpl_id","fpl_name","xg_per90","xa_per90","match_score"]].copy().fillna(0.0)
    os.makedirs("data/cache", exist_ok=True)
    out.to_csv("data/cache/xgxa_players.csv", index=False)
    print("Wrote data/cache/xgxa_players.csv using provider:", provider)

if __name__ == "__main__":
    main()
