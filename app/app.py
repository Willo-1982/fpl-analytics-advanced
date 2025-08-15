
import streamlit as st, os
st.set_page_config(page_title="FPL Analytics", page_icon="⚽", layout="wide")
st.title("FPL Analytics — Advanced")
files={'bootstrap':'data/cache/bootstrap-static.json','fixtures':'data/cache/fixtures.json','next_gw':'data/cache/projections_next_gw.csv','next_5':'data/cache/projections_next_5gws.csv','captaincy':'data/cache/captaincy_rankings.csv'}
cols=st.columns(len(files))
for i,(k,p) in enumerate(files.items()):
    with cols[i]: st.metric(k.replace('_',' ').title(), "✅" if os.path.exists(p) else "—")
st.write("Use the pages: Picks, Captaincy, Fixtures, Team Planner, Exports.")
