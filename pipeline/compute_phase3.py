from __future__ import annotations
import argparse, json, os
import pandas as pd, numpy as np

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
            return e["id"]
    unfinished = [e["id"] for e in evs if not e.get("finished")]
    return min(unfinished) if unfinished else 1

def elements_df(bs):
    df = pd.DataFrame(bs["elements"])
    teams = pd.DataFrame(bs["teams"])[["id","name"]].rename(columns={"id":"team","name":"team_name"})
    df = df.merge(teams, left_on="team", right_on="team", how="left")
    pos_map = {1:"GK",2:"DEF",3:"MID",4:"FWD"}
    df["position"] = df["element_type"].map(pos_map)
    df = df.rename(columns={"id":"id","web_name":"web_name","now_cost":"price"})
    df["price"] = df["price"].astype(float)/10.0
    return df

def build_fixture_matrix(bs, fx, horizon):
    ev = current_event(bs)
    f = pd.DataFrame(fx)
    f = f[(f["event"].fillna(0) >= ev) & (f["event"].fillna(0) < ev + horizon)]
    f = f[["event","team_h","team_a","team_h_difficulty","team_a_difficulty"]]
    home = f.rename(columns={"team_h":"team","team_h_difficulty":"diff"}).assign(home=1)[["event","team","diff","home"]]
    away = f.rename(columns={"team_a":"team","team_a_difficulty":"diff"}).assign(home=0)[["event","team","diff","home"]]
    ft = pd.concat([home, away], ignore_index=True)
    return ft

def expected_minutes_simple(players: pd.DataFrame, fixtures_team: pd.DataFrame):
    base = players[["id","minutes"]].copy()
    base["start_rate"] = (base["minutes"].fillna(0)/900).clip(0,1)
    base["exp_minutes_per_fixture"] = 50 + 40*base["start_rate"]
    team_fixture_counts = fixtures_team.groupby("team").size().rename("fixtures_n")
    players2 = players.merge(team_fixture_counts, left_on="team", right_index=True, how="left").fillna({"fixtures_n":0})
    em = players2.merge(base[["id","exp_minutes_per_fixture"]], on="id", how="left")
    em["exp_minutes_total"] = em["fixtures_n"] * em["exp_minutes_per_fixture"].fillna(0)
    return em[["id","exp_minutes_total","fixtures_n"]]

def simple_points_engine(players: pd.DataFrame, fixtures_team: pd.DataFrame, horizon: int, xgxa: pd.DataFrame):
    df = players.copy()
    if "fpl_id" in xgxa.columns:
        df = df.merge(xgxa.rename(columns={"fpl_id":"id"}), on="id", how="left")
    else:
        df = df.merge(xgxa.rename(columns={"fpl_name":"web_name"}), on="web_name", how="left")
    for c in ["xg_per90","xa_per90"]:
        if c not in df.columns: df[c]=0.0
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    ft = fixtures_team.copy()
    if "diff" in ft.columns:
        ft["cs_prob"] = (6 - ft["diff"].fillna(3)).clip(1,5) / 10.0
    else:
        ft["cs_prob"] = 0.3
    cs_by_team = ft.groupby("team")["cs_prob"].sum().rename("cs_prob_sum")
    df = df.merge(cs_by_team, left_on="team", right_index=True, how="left")
    df["cs_prob_sum"] = df["cs_prob_sum"].fillna(0.0)
    em = expected_minutes_simple(df, ft)
    df = df.merge(em, on="id", how="left").fillna({"exp_minutes_total":0,"fixtures_n":0})
    df["appearance_pts"] = np.where(df["fixtures_n"]>0, 2.0*df["fixtures_n"], 0.0)
    pos_cs = {"GK":4.0,"DEF":4.0,"MID":1.0,"FWD":0.0}
    pos_goal = {"GK":0.0,"DEF":6.0,"MID":5.0,"FWD":4.0}
    pos_ast = {"GK":3.0,"DEF":3.0,"MID":3.0,"FWD":3.0}
    df["cs_pts"] = df.apply(lambda r: pos_cs.get(r["position"],0.0)*r["cs_prob_sum"], axis=1)
    factor = (df["exp_minutes_total"]/90.0).clip(lower=0.0)
    df["goals_exp"] = factor * df["xg_per90"]
    df["assists_exp"] = factor * df["xa_per90"]
    df["att_pts"] = df.apply(lambda r: r["goals_exp"]*pos_goal.get(r["position"],0.0) + r["assists_exp"]*pos_ast.get(r["position"],3.0), axis=1)
    df["ep_total"] = (df["appearance_pts"] + df["cs_pts"] + df["att_pts"]).round(2)
    return df[["id","web_name","team_name","position","price","ep_total","exp_minutes_total"]].rename(
        columns={"exp_minutes_total":"exp_minutes"})

def build_projection_for_range(bs, fx, xgxa, n: int):
    players = elements_df(bs)
    ft = build_fixture_matrix(bs, fx, horizon=n)
    proj = simple_points_engine(players, ft, n, xgxa)
    return proj

def write_captaincy(out_next: pd.DataFrame):
    cap = out_next.sort_values("ep_total", ascending=False).head(50).copy()
    cap = cap[["id","web_name","team_name","position","price","ep_total"]]
    cap.to_csv("data/cache/captaincy_rankings.csv", index=False)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--next_n", type=int, default=None, help="If set, writes only that horizon (1/3/5). Otherwise writes all.")
    args=ap.parse_args()
    bs, fx, xgxa = load_inputs()
    if args.next_n:
        out = build_projection_for_range(bs, fx, xgxa, n=args.next_n)
        if args.next_n == 1:
            out.to_csv("data/cache/projections_next_gw.csv", index=False); write_captaincy(out)
        elif args.next_n == 3:
            out.to_csv("data/cache/projections_next_3gws.csv", index=False)
        elif args.next_n == 5:
            out.to_csv("data/cache/projections_next_5gws.csv", index=False)
        else:
            out.to_csv(f"data/cache/projections_next_{args.next_n}gws.csv", index=False)
        print("Projections & captaincy written to data/cache/."); return
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
