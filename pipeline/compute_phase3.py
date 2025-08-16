from __future__ import annotations
import argparse, json, os, math
import pandas as pd, numpy as np

# ============================================================
# Data loading
# ============================================================
def load_inputs():
    b=json.load(open("data/cache/bootstrap-static.json","r",encoding="utf-8"))
    fx=json.load(open("data/cache/fixtures.json","r",encoding="utf-8"))
    x_path="data/cache/xgxa_players.csv"
    x=pd.read_csv(x_path) if os.path.exists(x_path) else pd.DataFrame(columns=["fpl_id","fpl_name","xg_per90","xa_per90"])
    return b, fx, x

def current_event(bs):
    evs = bs.get("events", [])
    for e in evs:
        if e.get("is_current") or (e.get("is_next") and not e.get("finished")):
            return int(e["id"])
    unfinished = [int(e["id"]) for e in evs if not e.get("finished")]
    return min(unfinished) if unfinished else 1

# ============================================================
# Core tables
# ============================================================
def elements_df(bs):
    df = pd.DataFrame(bs["elements"])
    teams = pd.DataFrame(bs["teams"])[["id","name"]].rename(columns={"id":"team","name":"team_name"})
    df = df.merge(teams, on="team", how="left")
    pos_map = {1:"GK",2:"DEF",3:"MID",4:"FWD"}
    df["position"] = df["element_type"].map(pos_map)
    df = df.rename(columns={"id":"id","web_name":"web_name","now_cost":"price"})
    df["price"] = df["price"].astype(float)/10.0
    # helpful fields
    for c in ["chance_of_playing_next_round","form","selected_by_percent","status"]:
        if c not in df.columns: df[c] = np.nan
    return df

def build_team_strengths(bs):
    t = pd.DataFrame(bs["teams"]).copy()
    # FPL includes overall strengths; sometimes separate attack/defence H/A exist; if not, fallback
    cols = ["strength", "strength_overall_home","strength_overall_away",
            "strength_attack_home","strength_attack_away","strength_defence_home","strength_defence_away"]
    for c in cols:
        if c not in t.columns: t[c] = np.nan
    # create simple attack/defence ratings on 0..5-ish scale
    t["att_rating"] = t[["strength_attack_home","strength_attack_away","strength"]].mean(axis=1, skipna=True)
    t["def_rating"] = t[["strength_defence_home","strength_defence_away","strength"]].mean(axis=1, skipna=True)
    # normalise to mean 3.0
    for c in ["att_rating","def_rating"]:
        m = t[c].mean(skipna=True)
        if not np.isnan(m) and m>0:
            t[c] = 3.0 * t[c] / m
        else:
            t[c] = 3.0
    return t[["id","att_rating","def_rating"]].rename(columns={"id":"team"})

def build_fixture_rows(bs, fx, horizon):
    """Return per-fixture rows for next N events with team-centric view and difficulty."""
    ev = current_event(bs)
    f = pd.DataFrame(fx)
    f = f[(f["event"].fillna(0) >= ev) & (f["event"].fillna(0) < ev + horizon)].copy()
    # carry difficulty; FPL lower is easier (2 easy .. 5 hard). We map to ease in 0.6..1.4
    def to_ease(d): 
        try:
            d=float(d)
        except:
            d=3.0
        return (6.0 - max(2.0, min(5.0, d))) / 2.5 + 0.6  # 0.6..1.4 approx
        
    f["ease_h"] = f.get("team_h_difficulty", 3).apply(to_ease)
    f["ease_a"] = f.get("team_a_difficulty", 3).apply(to_ease)
    home = f.rename(columns={"team_h":"team","team_a":"opp"})
    away = f.rename(columns={"team_a":"team","team_h":"opp"})
    home_rows = home.assign(home=1, ease=lambda x: x["ease_h"])[["event","team","opp","home","ease"]]
    away_rows = away.assign(home=0, ease=lambda x: x["ease_a"])[["event","team","opp","home","ease"]]
    ft = pd.concat([home_rows, away_rows], ignore_index=True)
    return ft

# ============================================================
# Minutes model (free, heuristic)
# ============================================================
def expected_minutes_model(players: pd.DataFrame, fixtures_team: pd.DataFrame) -> pd.DataFrame:
    """
    Heuristic EM:
      - base minutes per fixture by position: GK 90, DEF 85, MID 78, FWD 78
      - availability factor from chance_of_playing_next_round (0..1)
      - form bump (0.9..1.1) from 'form'
      - selected_by bump small (0.98..1.02)
      - multiply by number of fixtures in horizon
    """
    base_pos = {"GK":90.0, "DEF":85.0, "MID":78.0, "FWD":78.0}
    p = players[["id","position","chance_of_playing_next_round","form","selected_by_percent"]].copy()
    p["base_min"] = p["position"].map(base_pos).fillna(75.0)
    # availability (if NaN, assume 0.9)
    p["avail"] = pd.to_numeric(p["chance_of_playing_next_round"], errors="coerce").fillna(90.0)/100.0
    p["avail"] = p["avail"].clip(0.0,1.0)
    # form bump (FPL form is roughly 0..12). Map to 0.9..1.1
    f = pd.to_numeric(p["form"], errors="coerce").fillna(3.0)
    p["form_bump"] = (0.9 + (f.clip(0,12)/12.0)*0.2)
    # selected_by bump 0..60% -> 0.98..1.02
    sb = pd.to_numeric(p["selected_by_percent"], errors="coerce").fillna(5.0)
    p["sel_bump"] = 0.98 + (sb.clip(0,60)/60.0)*0.04
    p["exp_per_fixture"] = p["base_min"] * p["avail"] * p["form_bump"] * p["sel_bump"]
    # fixtures count
    team_counts = fixtures_team.groupby("team").size().rename("fixtures_n")
    out = players[["id","team"]].merge(team_counts, left_on="team", right_index=True, how="left").fillna({"fixtures_n":0})
    out = out.merge(p[["id","exp_per_fixture"]], on="id", how="left")
    out["exp_minutes_total"] = out["fixtures_n"] * out["exp_per_fixture"].fillna(0.0)
    return out[["id","exp_minutes_total","fixtures_n"]]

# ============================================================
# Opponent-strength adjustment
# ============================================================
def per_fixture_attack_multiplier(fixtures_team: pd.DataFrame, team_strengths: pd.DataFrame) -> pd.DataFrame:
    """Compute an attack multiplier for each (team, fixture) vs opponent defence & ease."""
    st = team_strengths.set_index("team")
    ft = fixtures_team.copy()
    ft = ft.merge(st[["def_rating"]], left_on="opp", right_index=True, how="left").rename(columns={"def_rating":"opp_def"})
    # lower opponent def => higher multiplier; normalise around 1.0
    # also factor in FDR ease (0.6..1.4). Use 50/50 blend.
    ft["opp_def"] = ft["opp_def"].fillna(3.0)
    mul_def = 3.0 / ft["opp_def"].replace(0,3.0)
    ft["att_mult"] = 0.5*mul_def + 0.5*ft["ease"].fillna(1.0)
    # sum across fixtures per team (if two fixtures, the multipliers add)
    agg = ft.groupby("team")["att_mult"].sum().rename("att_mult_sum")
    return agg

def clean_sheet_points_proxy(fixtures_team: pd.DataFrame, team_strengths: pd.DataFrame, position_series: pd.Series) -> pd.Series:
    """Estimate CS points using team defence vs opp attack & home flag via ease already captured."""
    st = team_strengths.set_index("team")
    ft = fixtures_team.copy()
    ft = ft.merge(st[["def_rating"]], left_on="team", right_index=True, how="left").rename(columns={"def_rating":"team_def"})
    ft = ft.merge(st[["att_rating"]], left_on="opp", right_index=True, how="left").rename(columns={"att_rating":"opp_att"})
    ft["team_def"] = ft["team_def"].fillna(3.0)
    ft["opp_att"] = ft["opp_att"].fillna(3.0)
    # logistic on def - opp_att, nudged by ease (already 0.6..1.4 -> map to -0.2..+0.2)
    z = 0.9*(ft["team_def"] - ft["opp_att"]) + (ft["ease"]-1.0)*0.4
    cs_prob = 1/(1+np.exp(-z))
    # sum CS probs per team (DGW adds)
    cs_sum = cs_prob.groupby(ft["team"]).sum().rename("cs_prob_sum")
    # map to points by position
    pos_cs = {"GK":4.0,"DEF":4.0,"MID":1.0,"FWD":0.0}
    pos_pts = position_series.map(pos_cs).fillna(0.0)
    # will add later per player by merging cs_sum
    return cs_sum, pos_pts

# ============================================================
# EP engine
# ============================================================
def ep_engine(players: pd.DataFrame, fixtures_team: pd.DataFrame, n: int, xgxa: pd.DataFrame, team_strengths: pd.DataFrame):
    df = players.copy()
    # Merge xg/xa
    if "fpl_id" in xgxa.columns:
        df = df.merge(xgxa.rename(columns={"fpl_id":"id"}), on="id", how="left")
    else:
        df = df.merge(xgxa.rename(columns={"fpl_name":"web_name"}), on="web_name", how="left")
    for c in ["xg_per90","xa_per90"]:
        if c not in df.columns: df[c]=0.0
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    # Minutes
    em = expected_minutes_model(df, fixtures_team)
    df = df.merge(em, on="id", how="left").fillna({"exp_minutes_total":0,"fixtures_n":0})

    # Opponent adjustment (attack)
    att_mult = per_fixture_attack_multiplier(fixtures_team, team_strengths)
    df = df.merge(att_mult, left_on="team", right_index=True, how="left").fillna({"att_mult_sum":0.0})

    # Clean sheet proxy
    cs_sum, pos_pts = clean_sheet_points_proxy(fixtures_team, team_strengths, df["position"])
    df = df.merge(cs_sum, left_on="team", right_index=True, how="left").fillna({"cs_prob_sum":0.0})

    # Appearance points
    df["appearance_pts"] = np.where(df["fixtures_n"]>0, 2.0*df["fixtures_n"], 0.0)

    # Attacking points
    factor = (df["exp_minutes_total"]/90.0).clip(lower=0.0)
    # average attack multiplier per fixture -> if zero fixtures keep zero
    avg_att_mult = np.where(df["fixtures_n"]>0, df["att_mult_sum"]/df["fixtures_n"].clip(lower=1), 0.0)
    goals_exp = factor * df["xg_per90"] * avg_att_mult
    assists_exp = factor * df["xa_per90"] * avg_att_mult
    pos_goal = {"GK":0.0,"DEF":6.0,"MID":5.0,"FWD":4.0}
    pos_ast = {"GK":3.0,"DEF":3.0,"MID":3.0,"FWD":3.0}
    df["att_pts"] = goals_exp*df["position"].map(pos_goal).fillna(0.0) + assists_exp*df["position"].map(pos_ast).fillna(0.0)

    # CS points
    df["cs_pts"] = df["cs_prob_sum"] * pos_pts

    df["ep_total"] = (df["appearance_pts"] + df["cs_pts"] + df["att_pts"]).round(2)
    return df[["id","web_name","team_name","position","price","ep_total","exp_minutes_total"]].rename(
        columns={"exp_minutes_total":"exp_minutes"}
    )

# ============================================================
# Public functions
# ============================================================
def build_projection_for_range(bs, fx, xgxa, n: int):
    players = elements_df(bs)
    ft = build_fixture_rows(bs, fx, horizon=n)
    team_str = build_team_strengths(bs)
    proj = ep_engine(players, ft, n, xgxa, team_str)
    return proj

def write_captaincy(out_next: pd.DataFrame):
    cap = out_next.sort_values("ep_total", ascending=False).head(50).copy()
    cap = cap[["id","web_name","team_name","position","price","ep_total"]]
    cap.to_csv("data/cache/captaincy_rankings.csv", index=False)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--next_n", type=int, default=None)
    args=ap.parse_args()

    bs, fx, xgxa = load_inputs()

    if args.next_n:
        out = build_projection_for_range(bs, fx, xgxa, n=args.next_n)
        if args.next_n == 1:
            out.to_csv("data/cache/projections_next_gw.csv", index=False)
            write_captaincy(out)
        elif args.next_n == 3:
            out.to_csv("data/cache/projections_next_3gws.csv", index=False)
        elif args.next_n == 5:
            out.to_csv("data/cache/projections_next_5gws.csv", index=False)
        else:
            out.to_csv(f"data/cache/projections_next_{args.next_n}gws.csv", index=False)
        print("Projections & captaincy written to data/cache/.")
        return

    out1 = build_projection_for_range(bs, fx, xgxa, n=1)
    out3 = build_projection_for_range(bs, fx, xgxa, n=3)
    out5 = build_projection_for_range(bs, fx, xgxa, n=5)

    out1.to_csv("data/cache/projections_next_gw.csv", index=False)
    out3.to_csv("data/cache/projections_next_3gws.csv", index=False)
    out5.to_csv("data/cache/projections_next_5gws.csv", index=False)

    write_captaincy(out1)
    print("Projections & captaincy written to data/cache/.")

if __name__=="__main__":
    main()
