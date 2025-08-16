import streamlit as st
import pandas as pd

st.title("Picks — Expected Points")

p1 = pd.read_csv("data/cache/projections_next_gw.csv")
p3 = pd.read_csv("data/cache/projections_next_3gws.csv")
p5 = pd.read_csv("data/cache/projections_next_5gws.csv")

p1 = p1.rename(columns={"ep_total":"ep_1"})
p3 = p3.rename(columns={"ep_total":"ep_3"})
p5 = p5.rename(columns={"ep_total":"ep_5"})

df = (
    p1.merge(p3[["id","ep_3"]], on="id", how="left")
      .merge(p5[["id","ep_5"]], on="id", how="left")
)

show_all = st.sidebar.checkbox("Show ALL FPL-registered players (include 0 mins)", value=False)
pos = st.sidebar.multiselect("Positions", options=["GK","DEF","MID","FWD"], default=["GK","DEF","MID","FWD"])

if not show_all:
    df = df[df["exp_minutes"].fillna(0) > 0]

df = df[df["position"].isin(pos)]
df["ep_3_avg"] = (df["ep_3"]/3).round(2)
df["ep_5_avg"] = (df["ep_5"]/5).round(2)

tab1, tab3, tab5 = st.tabs(["Next GW", "Next 3 GWs", "Next 5 GWs"])

with tab1:
    d = df.sort_values("ep_1", ascending=False)
    st.dataframe(d[["web_name","team_name","position","price","ep_1","ep_3","ep_5","ep_3_avg","ep_5_avg"]], hide_index=True)
    st.download_button("Download current view (CSV)", d.to_csv(index=False).encode("utf-8"), "picks_next_gw.csv", "text/csv")

with tab3:
    d = df.sort_values("ep_3", ascending=False)
    st.dataframe(d[["web_name","team_name","position","price","ep_1","ep_3","ep_5","ep_3_avg","ep_5_avg"]], hide_index=True)
    st.download_button("Download current view (CSV)", d.to_csv(index=False).encode("utf-8"), "picks_next_3gws.csv", "text/csv")

with tab5:
    d = df.sort_values("ep_5", ascending=False)
    st.dataframe(d[["web_name","team_name","position","price","ep_1","ep_3","ep_5","ep_3_avg","ep_5_avg"]], hide_index=True)
    st.download_button("Download current view (CSV)", d.to_csv(index=False).encode("utf-8"), "picks_next_5gws.csv", "text/csv")
