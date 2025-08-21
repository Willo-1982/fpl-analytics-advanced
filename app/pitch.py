import streamlit as st
import pandas as pd

# Simple pitch: starters in 4 lines (GK, DEF, MID, FWD) and a bench row

def _names(df: pd.DataFrame, ids):
    sub = df[df["id"].isin(ids)].copy()
    sub["nm"] = sub["web_name"].astype(str) + " (" + sub["team_name"].astype(str) + ")"
    # preserve input order
    order = {pid: i for i, pid in enumerate(ids)}
    sub["ord"] = sub["id"].map(order)
    return [t for _, t in sub.sort_values("ord")[["id","nm"]].itertuples(index=False, name=None)]

def render_pitch(df: pd.DataFrame, xi_ids, bench_ids=None, captain_id=None, vice_id=None):
    bench_ids = bench_ids or []
    # bucket starters by position for a clean grid
    pos = df.set_index("id")["position"].to_dict()
    gk = [p for p in xi_ids if pos.get(p) == "GK"]
    de = [p for p in xi_ids if pos.get(p) == "DEF"]
    mi = [p for p in xi_ids if pos.get(p) == "MID"]
    fw = [p for p in xi_ids if pos.get(p) == "FWD"]

    st.subheader("Starting XI")
    for title, arr in [("GK", gk), ("DEF", de), ("MID", mi), ("FWD", fw)]:
        cols = st.columns(max(1, len(arr)))
        for c, (pid, label) in zip(cols, _names(df, arr)):
            badge = ""
            if captain_id == pid: badge = " (C)"
            elif vice_id == pid: badge = " (VC)"
            c.write(f"**{label}{badge}**")

    if bench_ids:
        st.subheader("Bench")
        cols = st.columns(len(bench_ids))
        for c, (pid, label) in zip(cols, _names(df, bench_ids)):
            c.write(label)
