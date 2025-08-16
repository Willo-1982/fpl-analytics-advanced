import streamlit as st
import os
st.set_page_config(page_title="FPL Analytics Advanced", layout="wide")
try:
    import requests
    RAW_URL = "https://raw.githubusercontent.com/Willo-1982/fpl-analytics-advanced/main/data/cache/xgxa_players.csv"
    os.makedirs("data/cache", exist_ok=True)
    r = requests.get(RAW_URL, timeout=8, headers={"User-Agent":"Mozilla/5.0"})
    if r.status_code == 200 and len(r.content) > 1000:
        open("data/cache/xgxa_players.csv","wb").write(r.content)
except Exception:
    pass
st.sidebar.title("Navigation")
st.sidebar.markdown("- Picks\n- Captaincy\n- Fixtures\n- Team Planner\n- Exports and Share")
st.title("FPL Analytics Advanced")
st.success("Use the sidebar. Projections exist for Next 1/3/5 GWs.")
