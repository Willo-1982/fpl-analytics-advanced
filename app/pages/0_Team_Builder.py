import streamlit as st
import pandas as pd
import pathlib, sys, importlib.util

# ---------- robust imports from absolute paths ----------
APP_DIR = pathlib.Path(__file__).resolve().parents[1]   # .../app

def _import_from_app(mod_name: str):
    file = APP_DIR / f"{mod_name}.py"
    spec = importlib.util.spec_from_file_location(mod_name, file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod

state = _import_from_app("state")
optimizer = _import_from_app("optimizer")
pitch = _import_from_app("pitch")
# --------------------------------------------------------

st.title("Team Builder — Optimizer, Transfers & Chips")

DATA_DIR = pathlib.Path("data/cache")

# ---------------------------- Helpers ----------------------------
def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize common columns and types."""
    if "team_name" not in df.columns and "team" in df.columns:
        df["team_name"] = df["team"]

    # unify EP columns
    if "ep_1" not in df.columns and "ep_total" in df.columns:
        df = df.rename(columns={"ep_total": "ep_1"})
    for col in ("ep_3", "ep_5"):
        if col not in df.columns:
            df[col] = df.get("ep_1", 0.0)

    # price
    if "price" not in df.columns:
        if "price_m" in df.columns:
            df["price"] = df["price_m"]
        else:
            df["price"] = 0.0

    # types
    for c in ("id","price","ep_1","ep_3","ep_5"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # nice label for pickers
    df["label"] = (
        df["web_name"].astype(str)
        + " (" + df["team_name"].astype(str)
        + ", £" + df["price"].round(1).astype(str) + ")"
    )
    return df

def _minutes_probability(df: pd.DataFrame) -> pd.Series:
    """
    Return a 0..1 probability a player meaningfully features next GW using whatever we can find:
    - chance_of_playing_next_round (0..100)
    - starts_prob / xMinsProb (0..1)
    - pred_minutes (0..90) → /90
    Default 1.0 if no columns exist.
    """
    if "chance_of_playing_next_round" in df.columns:
        return pd.to_numeric(df["chance_of_playing_next_round"], errors="coerce").fillna(100) / 100.0
    for c in ("starts_prob","xMinsProb"):
        if c in df.columns:
            return pd.to_numeric(df[c], errors="coerce").fillna(1.0).clip(0,1)
    if "pred_minutes" in df.columns:
        return (pd.to_numeric(df["pred_minutes"], errors="coerce").fillna(90) / 90.0).clip(0,1)
    return pd.Series(1.0, index=df.index)

def _bookmaker_mult(df: pd.DataFrame, strength: float) -> pd.Series:
    """
    Build a 0..∞ multiplier using optional bookmaker-like columns (if present).
    We keep it conservative and bounded around 1.0.
    - For GK/DEF, CS (clean sheet) is most impactful.
    - For MID/FWD, goals scored probability is most impactful.
    Expected columns (optional, any subset):
      team_cs_prob (0..1), team_gs_prob (0..1)  [goals conceded clean-sheet / goals scored]
    Multiplier = (1 - strength) + strength * factor(pos)
    """
    strength = max(0.0, min(1.0, float(strength)))
    base = pd.Series(1.0, index=df.index)
    cs = df.get("team_cs_prob", pd.Series(0.0, index=df.index)).astype(float).clip(0,1)
    gs = df.get("team_gs_prob", pd.Series(0.5, index=df.index)).astype(float).clip(0,1)
    pos = df["position"].astype(str)

    # pos-specific factor:
    # GK/DEF: 0.7 weight on CS; MID/FWD: 0.7 weight on Goals; all have small bias to 1.0
    factor = pd.Series(1.0, index=df.index)
    factor = factor.where(~pos.isin(["GK","DEF"]), 0.3 + 0.7*cs)      # ~[0.3..1.0]
    factor = factor.where(~pos.isin(["MID","FWD"]), 0.3 + 0.7*gs)     # ~[0.3..1.0]

    return (1 - strength) + strength * factor

def _make_objective(df: pd.DataFrame, w1: float, w3: float, w5: float,
                    minutes_gate: float, minutes_scale: float,
                    bm_strength: float, hide_nonstarters: bool) -> pd.DataFrame:
    """
    Compute 'obj_1' (next GW objective) and 'obj_3' (selection objective for 15-man) with:
      - form horizon weights (w1/w3/w5)
      - minutes gating & scaling
      - bookmaker multiplier
    """
    w_sum = max(1e-9, (w1 + w3 + w5))
    w1, w3, w5 = w1 / w_sum, w3 / w_sum, w5 / w_sum

    df = df.copy()
    play_prob = _minutes_probability(df)  # 0..1
    # Hard hide under gate?
    if hide_nonstarters:
        df = df[play_prob >= minutes_gate].copy()
        play_prob = play_prob.loc[df.index]

    # Scale EP by (minutes_scale*play_prob + (1-minutes_scale)*1.0)
    # minutes_scale=1 → fully scaled by probability; 0 → ignore minutes in scaling
    minutes_mult = (1.0 - minutes_scale) + minutes_scale * play_prob

    # Bookmaker multiplier (optional columns)
    bm_mult = _bookmaker_mult(df, bm_strength)

    # Next GW (obj_1) uses ep_1
    obj_1 = df["ep_1"].astype(float) * minutes_mult * bm_mult

    # 15-man selection (obj_3) uses horizon blend
    obj_3 = (w1 * df["ep_1"].astype(float) + w3 * df["ep_3"].astype(float) + w5 * df["ep_5"].astype(float))
    obj_3 = obj_3 * minutes_mult * bm_mult

    df["obj_1"] = obj_1
    df["obj_3"] = obj_3
    # keep label possibly stale after filtering
    if "label" not in df.columns and {"web_name","team_name","price"}.issubset(df.columns):
        df["label"] = (
            df["web_name"].astype(str) + " ("
            + df["team_name"].astype(str) + ", £"
            + df["price"].round(1).astype(str) + ")"
        )
    return df

# ---------------------------- Load & adjust projections ----------------------------
@st.cache_data(show_spinner=False)
def load_proj():
    p1_path = DATA_DIR / "projections_next_gw.csv"
    p3_path = DATA_DIR / "projections_next_3gws.csv"
    p5_path = DATA_DIR / "projections_next_5gws.csv"

    def _read(path):
        return pd.read_csv(path) if path.exists() else None

    p1, p3, p5 = _read(p1_path), _read(p3_path), _read(p5_path)

    if p1 is None:
        st.error(
            "Missing projections.\n\nRun:\n"
            "  1) `python pipeline\\fetch_fpl_data.py all`\n"
            "  2) `python pipeline\\compute_phase3.py --next_n 5`"
        )
        st.stop()

    df = _ensure_columns(p1)
    if p3 is not None:
        p3 = _ensure_columns(p3)
        df = df.merge(p3[["id", "ep_3"]], on="id", how="left")
    if p5 is not None:
        p5 = _ensure_columns(p5)
        df = df.merge(p5[["id", "ep_5"]], on="id", how="left")
    df = _ensure_columns(df)
    return df

df_raw = load_proj()

# ---------------------------- Sidebar controls ----------------------------
st.sidebar.header("Model settings (free & optional)")
col_w1, col_w3, col_w5 = st.sidebar.columns(3)
w1 = col_w1.number_input("w₁ (next GW)", min_value=0.0, max_value=1.0, value=0.6, step=0.05)
w3 = col_w3.number_input("w₃ (next 3)",   min_value=0.0, max_value=1.0, value=0.3, step=0.05)
w5 = col_w5.number_input("w₅ (next 5)",   min_value=0.0, max_value=1.0, value=0.1, step=0.05)

hide_nonstarters = st.sidebar.checkbox("Hide likely non-starters (minutes gate)", value=True)
minutes_gate   = st.sidebar.slider("Minutes gate (prob must be ≥ this)", 0.0, 1.0, 0.5, 0.05)
minutes_scale  = st.sidebar.slider("Minutes scaling strength", 0.0, 1.0, 0.8, 0.05)
bm_strength    = st.sidebar.slider("Bookmaker adjustment strength", 0.0, 1.0, 0.4, 0.05,
                                   help="Uses optional columns: team_cs_prob, team_gs_prob (if present)")

df_view = _make_objective(
    df_raw, w1=w1, w3=w3, w5=w5,
    minutes_gate=minutes_gate, minutes_scale=minutes_scale,
    bm_strength=bm_strength, hide_nonstarters=hide_nonstarters
)

state_dict = state.load_state()

st.sidebar.subheader("Budget & Rules")
budget = st.sidebar.number_input(
    "Budget (£)", min_value=80.0, max_value=120.0, value=float(state_dict.get("budget", 100.0)), step=0.5
)
free_transfers = st.sidebar.number_input(
    "Free Transfers", min_value=0, max_value=3, value=int(state_dict.get("free_transfers", 1))
)

# bank = derived from squad
squad_ids = state_dict.get("squad", [])
squad_value = optimizer.squad_value(df_raw, squad_ids)
bank_left = max(0.0, float(budget) - squad_value) if squad_ids else float(state_dict.get("bank", 0.0))
st.sidebar.metric("Squad value", f"£{squad_value:.1f}")
st.sidebar.metric("Bank (auto)", f"£{bank_left:.1f}")
if squad_ids and squad_value > budget + 1e-6:
    st.sidebar.error("Over budget. Make transfers to get under budget.")

# ---------------------------- Actions ----------------------------
colA, colB, colC = st.columns(3)
with colA:
    if st.button("💾 Save Team"):
        state_dict["budget"] = float(budget)
        state_dict["free_transfers"] = int(free_transfers)
        state.save_state(state_dict)
        st.success("Saved.")

with colB:
    if st.button("🗑 Reset Team"):
        state_dict = state.default_state()
        state.save_state(state_dict)
        st.warning("State reset. Pick a new squad below.")

with colC:
    if st.button("🔁 Suggest 1 transfer (obeys bank & rules)"):
        if len(squad_ids) < 1:
            st.error("No current squad. Pick players or rebuild first.")
        else:
            sug = optimizer.suggest_transfers(
                df_view,                # uses obj_1 for the delta
                current_squad=squad_ids,
                budget=float(budget),
                bank_left=float(bank_left),
            )
            st.session_state["last_suggestion"] = sug
            if sug["out_name"]:
                st.info(f"Suggested OUT: **{sug['out_name']}** → IN: **{sug['in_name']}** | ΔEP1={sug['delta_ep1']:.2f}")
            else:
                st.warning("No legal single-transfer improvement found within your bank/budget.")

st.divider()

left, mid, right = st.columns(3)
with left:
    if st.button("⭐ Optimize Starters (keep your 15)"):
        if len(squad_ids) != 15:
            st.error("You need 15 players picked to optimize starters.")
        else:
            xi, c, v, bench = optimizer.choose_starting_xi(df_view, squad_ids, return_bench=True)
            state_dict["starters"], state_dict["captain"], state_dict["vice"] = xi, c, v
            state.save_state(state_dict)
            st.success("Starting XI optimized.")

with mid:
    if st.button("🧱 Rebuild Best 15 (under budget)"):
        chosen = optimizer.solve_squad_15(df_view, budget=float(budget), max_per_team=3)
        state_dict["squad"] = chosen
        xi, c, v, bench = optimizer.choose_starting_xi(df_view, chosen, return_bench=True)
        state_dict["starters"], state_dict["captain"], state_dict["vice"] = xi, c, v
        state.save_state(state_dict)
        st.success("New 15-man squad built.")

with right:
    st.caption("Tune the sliders in the sidebar to influence selections.")

# ---------------------------- Pickers by position ----------------------------
st.subheader("Pick Your Squad (15)")
pos_groups = {"GK": 2, "DEF": 5, "MID": 5, "FWD": 3}

for pos, need in pos_groups.items():
    pool = df_view[df_view["position"] == pos].sort_values("obj_3", ascending=False).reset_index(drop=True)
    labels = ["-- none --"] + pool["label"].tolist()
    picks = []
    for i in range(need):
        key = f"pick_{pos}_{i}"
        # prefill from state
        prelabel = None
        if state_dict.get("squad"):
            ids_pos = [pid for pid in state_dict["squad"] if df_raw.loc[df_raw["id"] == pid, "position"].iloc[0] == pos]
            if i < len(ids_pos):
                row = pool[pool["id"] == ids_pos[i]]
                if not row.empty:
                    prelabel = row["label"].iloc[0]
        idx_default = labels.index(prelabel) if prelabel in labels else 0
        choice = st.selectbox(f"{pos} {i+1}", options=labels, index=idx_default, key=key)
        if choice != "-- none --":
            idx = labels.index(choice) - 1
            picks.append(int(pool.iloc[idx]["id"]))

    # replace picks of that position in the saved squad
    existing = state_dict.get("squad", [])
    existing = [pid for pid in existing if df_raw.loc[df_raw["id"] == pid, "position"].iloc[0] != pos]
    state_dict["squad"] = existing + picks

# recompute bank/value after picks
squad_ids = state_dict.get("squad", [])
squad_value = optimizer.squad_value(df_raw, squad_ids)
bank_left = max(0.0, float(budget) - squad_value) if squad_ids else 0.0
if squad_ids and squad_value > budget + 1e-6:
    st.error(f"Over budget by £{(squad_value - budget):.1f}.")
else:
    st.success(f"Squad value £{squad_value:.1f} | Bank £{bank_left:.1f}")

# ---------------------------- Pitch ----------------------------
if len(squad_ids) == 15:
    xi, c, v, bench = optimizer.choose_starting_xi(df_view, squad_ids, return_bench=True)
    state_dict["starters"], state_dict["captain"], state_dict["vice"] = xi, c, v
    state.save_state(state_dict)
    pitch.render_pitch(df_view, xi_ids=xi, bench_ids=bench, captain_id=c, vice_id=v)
else:
    st.info("Select 15 players to render the pitch.")
# ---------------------------- Captaincy helper ----------------------------
st.subheader("Captaincy Helper — Top 10 (next GW)")

if "obj_1" in df_view.columns:
    tmp = df_view.copy()

    # Minutes uncertainty drives a simple risk band:
    #   EP_high = obj_1 (already scaled)
    #   EP_low  = obj_1 * (0.5 + 0.5 * minutes_prob)  -> lower if minutes_prob is small
    pmin = tmp["minutes_prob_flag"].astype(float).clip(0, 1)
    ep_hi = tmp["obj_1"].astype(float)
    ep_lo = ep_hi * (0.5 + 0.5 * pmin)

    view = pd.DataFrame({
        "id": tmp["id"].astype(int),
        "Player": tmp["web_name"],
        "Team": tmp.get("team_name", tmp.get("team", "")),
        "Pos": tmp["position"],
        "Price": tmp["price"].astype(float).round(1),
        "EP (next GW)": ep_hi.round(2),
        "EP low": ep_lo.round(2),
        "EP high": ep_hi.round(2),
        "EO %": tmp.get("selected_by_percent", pd.Series([""]*len(tmp))),
    })

    # Rank by EP (next GW), show top 10
    view = view.sort_values("EP (next GW)", ascending=False).head(10).reset_index(drop=True)

    # Small helper to show +/- band beside EP
    view["Risk band"] = (view["EP low"].astype(str) + " – " + view["EP high"].astype(str))

    st.dataframe(
        view[["Player","Team","Pos","Price","EP (next GW)","Risk band","EO %"]],
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "Risk band factors in minutes uncertainty from FPL flags/news; "
        "EO = Selected-by-% from FPL. Consider captaining within your risk comfort."
    )
else:
    st.info("No next-GW objective available (obj_1). Recompute projections.")

# ---------------------------- Footer ----------------------------
st.divider()
st.caption(
    "Minutes model uses FPL flags/news (incl. suspensions) + your what-if overrides. "
    "Opponent difficulty and (optional) bookmaker nudges are applied to projections. "
    "Transfers respect budget/bank, formation, and 3-per-club rules."
)

