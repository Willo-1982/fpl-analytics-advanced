import streamlit as st
import pandas as pd
from pathlib import Path

st.title("Captaincy")

# Locations produced by the pipeline
CAP_PATH = Path("data/cache/captaincy_rankings.csv")
PROJ1_PATH = Path("data/cache/projections_next_gw.csv")

def load_normalised_dataframe() -> pd.DataFrame:
    """
    Loads captaincy rankings if present; otherwise falls back to next-GW projections.
    Normalises column names so legacy pages that expect EP/price_m continue to work.
    """
    if CAP_PATH.exists():
        df = pd.read_csv(CAP_PATH)
    else:
        if not PROJ1_PATH.exists():
            st.error(
                "No projections found. Please run:\n\n"
                "`python pipeline\\fetch_fpl_data.py all` then `python pipeline\\compute_phase3.py`"
            )
            st.stop()
        df = pd.read_csv(PROJ1_PATH)

    # Normalise to expected schema
    # EP: prefer existing 'EP', else map from 'ep_total'
    if "EP" not in df.columns:
        if "ep_total" in df.columns:
            df["EP"] = df["ep_total"]
        elif "ep_1" in df.columns:
            df["EP"] = df["ep_1"]

    # price_m (millions): derive from 'price' if needed
    if "price_m" not in df.columns and "price" in df.columns:
        df["price_m"] = df["price"]

    # Ensure the core identifier columns exist (best effort)
    for fallback_col, alts in {
        "web_name": ["web_name", "name", "player_name"],
        "team_name": ["team_name", "team", "team_short"],
        "position": ["position", "pos"],
    }.items():
        if fallback_col not in df.columns:
            for c in alts:
                if c in df.columns:
                    df = df.rename(columns={c: fallback_col})
                    break

    return df

df = load_normalised_dataframe()

# Controls
topn = st.slider("Show top N", min_value=5, max_value=50, value=20, step=5)

# Sort by EP if present
if "EP" in df.columns:
    df = df.sort_values("EP", ascending=False)

# Display
wanted = ["web_name", "team_name", "position", "price_m", "EP"]
cols = [c for c in wanted if c in df.columns]
if not cols:
    st.error("No usable columns available after normalisation.")
    st.stop()

st.dataframe(df.head(topn)[cols], use_container_width=True)
