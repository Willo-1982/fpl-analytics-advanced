import streamlit as st
import pandas as pd
from pathlib import Path

st.title("Exports & Share")

PROJ1_PATH = Path("data/cache/projections_next_gw.csv")

def load_normalised_proj() -> pd.DataFrame:
    if not PROJ1_PATH.exists():
        st.error(
            "No projections found. Please run:\n\n"
            "`python pipeline\\fetch_fpl_data.py all` then `python pipeline\\compute_phase3.py`"
        )
        st.stop()

    df = pd.read_csv(PROJ1_PATH)

    # Normalise columns so the page logic keeps working
    if "EP" not in df.columns:
        if "ep_total" in df.columns:
            df["EP"] = df["ep_total"]
        elif "ep_1" in df.columns:
            df["EP"] = df["ep_1"]

    if "price_m" not in df.columns and "price" in df.columns:
        df["price_m"] = df["price"]

    # Ensure identifiers exist
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

df = load_normalised_proj()

required_for_logic = ["web_name", "team_name", "position", "EP"]
missing = [c for c in required_for_logic if c not in df.columns]
if missing:
    st.error(f"Required columns missing from projections after normalisation: {missing}")
    st.stop()

# Build a simple XI (4-4-2) by EP
gk  = df[df["position"] == "GK"].sort_values("EP", ascending=False).head(1)
defs = df[df["position"] == "DEF"].sort_values("EP", ascending=False).head(4)
mids = df[df["position"] == "MID"].sort_values("EP", ascending=False).head(4)
fwds = df[df["position"] == "FWD"].sort_values("EP", ascending=False).head(2)

xi = pd.concat([gk, defs, mids, fwds], ignore_index=True)

display_cols = [c for c in ["id", "web_name", "team_name", "position", "price_m", "EP"] if c in xi.columns]
st.subheader("Suggested XI (EP-optimised, 4-4-2)")
st.dataframe(xi[display_cols], use_container_width=True)

# CSV export
st.download_button(
    label="Download Suggested XI (CSV)",
    data=xi[display_cols].to_csv(index=False).encode("utf-8"),
    file_name="suggested_xi.csv",
    mime="text/csv",
)
