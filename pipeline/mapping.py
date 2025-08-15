
from __future__ import annotations
import pandas as pd
from rapidfuzz import process, fuzz

def normalize_name(s: str) -> str:
    if not isinstance(s, str): return ""
    return " ".join(s.lower().replace("-", " ").replace(".", "").split())

def build_player_mapping(df_fpl: pd.DataFrame, df_provider: pd.DataFrame, provider_name_col: str) -> pd.DataFrame:
    prov_names = df_provider[provider_name_col].fillna("").astype(str).map(normalize_name).tolist()
    rows = []
    for _, r in df_fpl.iterrows():
        nm = normalize_name(f"{r.get('first_name','')} {r.get('second_name','')}")
        match = process.extractOne(nm, prov_names, scorer=fuzz.WRatio, score_cutoff=86)
        rows.append({
            "fpl_id": r["id"],
            "fpl_name": f"{r.get('first_name','')} {r.get('second_name','')}".strip(),
            "provider_match_name": match[0] if match else "",
            "match_score": match[1] if match else 0,
        })
    return pd.DataFrame(rows)
