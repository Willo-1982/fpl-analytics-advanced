import streamlit as st
import pandas as pd

st.title("Team Planner — Next 1/3/5 GWs")

p1 = pd.read_csv("data/cache/projections_next_gw.csv")[["id","web_name","team_name","position","price","ep_total","exp_minutes"]].rename(columns={"ep_total":"ep_1"})
p3 = pd.read_csv("data/cache/projections_next_3gws.csv")[["id","ep_total"]].rename(columns={"ep_total":"ep_3"})
p5 = pd.read_csv("data/cache/projections_next_5gws.csv")[["id","ep_total"]].rename(columns={"ep_total":"ep_5"})

df = (
    p1.merge(p3, on="id", how="left")
      .merge(p5, on="id", how="left")
      .fillna({"ep_3":0.0,"ep_5":0.0})
)

show_all_planner = st.sidebar.checkbox("Show ALL players in pickers (include 0 mins)", value=False, key="show_all_planner")
if not show_all_planner:
    df = df[df["exp_minutes"].fillna(0) > 0]

st.subheader("Select your Best XI (by names)")
gk_pool = df[df["position"]=="GK"]
def_pool = df[df["position"]=="DEF"]
mid_pool = df[df["position"]=="MID"]
fwd_pool = df[df["position"]=="FWD"]

sel_gk = st.multiselect("Goalkeepers", gk_pool["web_name"].tolist(), max_selections=2, key="sel_gk")
sel_def = st.multiselect("Defenders", def_pool["web_name"].tolist(), max_selections=5, key="sel_def")
sel_mid = st.multiselect("Midfielders", mid_pool["web_name"].tolist(), max_selections=5, key="sel_mid")
sel_fwd = st.multiselect("Forwards", fwd_pool["web_name"].tolist(), max_selections=3, key="sel_fwd")

selected = df[df["web_name"].isin(sel_gk+sel_def+sel_mid+sel_fwd)].copy()

st.dataframe(selected[["web_name","team_name","position","price","ep_1","ep_3","ep_5"]], hide_index=True)

ep1 = selected["ep_1"].sum()
ep3 = selected["ep_3"].sum()
ep5 = selected["ep_5"].sum()

st.subheader("Projected Points (Selected Squad)")
c1, c2, c3 = st.columns(3)
c1.metric("Next GW", f"{ep1:.1f}")
c2.metric("Next 3 GWs", f"{ep3:.1f}")
c3.metric("Next 5 GWs", f"{ep5:.1f}")
