import streamlit as st
import pandas as pd
from app.state import load_state, save_state, default_state
from app.optimizer import solve_squad, choose_starting_xi, suggest_transfers
from app.pitch import render_pitch

st.title("Team Builder — Optimizer, Transfers & Chips (Free)")

@st.cache_data(show_spinner=False)
def load_proj():
    p1 = pd.read_csv("data/cache/projections_next_gw.csv").rename(columns={"ep_total":"ep_1"}) if (pd.io.common.file_exists("data/cache/projections_next_gw.csv")) else None
    p3 = pd.read_csv("data/cache/projections_next_3gws.csv").rename(columns={"ep_total":"ep_3"}) if (pd.io.common.file_exists("data/cache/projections_next_3gws.csv")) else None
    p5 = pd.read_csv("data/cache/projections_next_5gws.csv").rename(columns={"ep_total":"ep_5"}) if (pd.io.common.file_exists("data/cache/projections_next_5gws.csv")) else None
    if p1 is None:
        st.error("Missing projections. Run: `python pipeline\\fetch_fpl_data.py all` then `python pipeline\\compute_phase3.py`.")
        st.stop()
    df = p1
    if p3 is not None: df = df.merge(p3[["id","ep_3"]], on="id", how="left")
    if p5 is not None: df = df.merge(p5[["id","ep_5"]], on="id", how="left")
    # Backfills if 3/5 files are absent
    for col in ("ep_3","ep_5"):
        if col not in df.columns:
            df[col] = df.get("ep_1", df.get("ep_total", 0.0))
    # Ensure price column is consistent
    if "price" not in df.columns and "price_m" in df.columns:
        df["price"] = df["price_m"]
    return df

df = load_proj()
state = load_state()

st.sidebar.subheader("Budget & Rules")
budget = st.sidebar.number_input("Squad budget (£)", min_value=80.0, max_value=120.0, value=float(state.get("budget",100.0)), step=0.5)
bank = st.sidebar.number_input("Bank (£)", min_value=0.0, max_value=20.0, value=float(state.get("bank",0.0)), step=0.1)
free_transfers = st.sidebar.number_input("Free Transfers", min_value=0, max_value=3, value=int(state.get("free_transfers",1)))

colA, colB, colC, colD = st.columns(4)
with colA:
    if st.button("💾 Save Team"):
        state["budget"]=float(budget); state["bank"]=float(bank); state["free_transfers"]=int(free_transfers)
        save_state(state); st.success("Team & settings saved.")
with colB:
    if st.button("🗑 Reset Team"):
        state = default_state(); save_state(state); st.warning("State reset.")
with colC:
    if st.button("⭐ Optimize (15-man)"):
        chosen = solve_squad(df, budget=budget, max_per_team=3)
        state["squad"] = chosen
        xi, c, v = choose_starting_xi(df, chosen)
        state["starters"]=xi; state["captain"]=c; state["vice"]=v
        save_state(state); st.success("Optimized squad selected.")
with colD:
    if st.button("🔁 Suggest 1 transfer"):
        if not state.get("squad"):
            st.error("No current squad. Optimize first or pick players.")
        else:
            sug = suggest_transfers(df, state["squad"], bank=float(bank), transfers_allowed=1, budget=float(budget))
            st.session_state["last_suggestion"]=sug
            if sug["out"]:
                st.info(f"Suggested OUT: {sug['out']} → IN: {sug['in']} | ΔEP1={sug['delta_ep1']:.2f}")

st.subheader("Pick Your Squad (15)")
pos_groups = {"GK":2,"DEF":5,"MID":5,"FWD":3}
for pos, need in pos_groups.items():
    pool = df[df["position"]==pos].sort_values("ep_3", ascending=False)
    options = ["-- none --"] + (pool["web_name"] + " (" + pool["team_name"] + ", £" + pool["price"].round(1).astype(str) + ")").tolist()
    picks = []
    for i in range(need):
        key=f"pick_{pos}_{i}"
        prelabel = None
        if state.get("squad"):
            ids_pos = [pid for pid in state["squad"] if df[df["id"]==pid]["position"].iloc[0]==pos]
            if i < len(ids_pos):
                row = pool[pool["id"]==ids_pos[i]]
                if not row.empty:
                    prelabel = row["web_name"].iloc[0] + " (" + row["team_name"].iloc[0] + ", £" + str(round(row["price"].iloc[0],1)) + ")"
        choice = st.selectbox(f"{pos} {i+1}", options=options, index=(options.index(prelabel) if prelabel in options else 0), key=key)
        if choice!="-- none --":
            idx = options.index(choice)-1
            picks.append(int(pool.iloc[idx]["id"]))
    state_ids = state.get("squad", [])
    state_ids = [pid for pid in state_ids if df[df["id"]==pid]["position"].iloc[0] != pos]
    state_ids += picks
    state["squad"]=state_ids

if len(state["squad"])==15:
    st.subheader("Starting XI & Captain")
    xi, c, v = choose_starting_xi(df, state["squad"])
    state["starters"]=xi; state["captain"]=c; state["vice"]=v
    save_state(state)
    render_pitch(df, xi_ids=xi, captain_id=c, vice_id=v)
else:
    st.info("Select 15 players to render the pitch.")

st.subheader("Chip Suggestions")
c1, c2 = st.columns(2)
with c1:
    if st.button("🎯 Best Free Hit (Next GW)"):
        chosen = solve_squad(df.assign(obj=df.get("ep_1", df.get("ep_total", 0.0))), budget=100.0, max_per_team=3)
        xi, cpt, vce = choose_starting_xi(df, chosen)
        st.success("Suggested Free Hit XI (Next GW):")
        render_pitch(df, xi_ids=xi, captain_id=cpt, vice_id=vce)
with c2:
    if st.button("🃏 Best Wildcard (Next 3 GWs)"):
        chosen = solve_squad(df, budget=budget, max_per_team=3)
        xi, cpt, vce = choose_starting_xi(df, chosen)
        st.success("Suggested Wildcard XI:")
        render_pitch(df, xi_ids=xi, captain_id=cpt, vice_id=vce)
