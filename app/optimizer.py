# app/optimizer.py
from __future__ import annotations
import pandas as pd
from typing import List, Dict, Tuple

_POS_NEED = {"GK": 2, "DEF": 5, "MID": 5, "FWD": 3}
_START_NEED = {"GK": 1, "DEF": 3, "MID": 4, "FWD": 3}  # baseline 3-4-3

def _price_col(df: pd.DataFrame) -> str:
    return "price" if "price" in df.columns else ("price_m" if "price_m" in df.columns else "now_cost")

def _obj_cols(df: pd.DataFrame) -> Tuple[str, str, str]:
    o1 = "ep_1" if "ep_1" in df.columns else ("ep_total" if "ep_total" in df.columns else None)
    o3 = "ep_3" if "ep_3" in df.columns else (o1 or "ep_total")
    o5 = "ep_5" if "ep_5" in df.columns else (o3 or o1 or "ep_total")
    return o1 or "ep_total", o3, o5

def _mins_scale(row: pd.Series) -> float:
    # If pipeline filled minutes_scale, use it; otherwise infer from flags/status/news
    if "minutes_scale" in row and pd.notna(row["minutes_scale"]):
        try:
            return float(row["minutes_scale"])
        except Exception:
            pass
    f = f"{row.get('status','')} {row.get('news','')} {row.get('flags','')}".lower()
    if any(x in f for x in ["susp", "suspended", "red", "inj", "out", "0%", "25%"]):
        return 0.55
    if any(x in f for x in ["orange", "75%", "doubt"]):
        return 0.8
    return 1.0

def _team_col(df: pd.DataFrame) -> str:
    return "team_name" if "team_name" in df.columns else "team"

def _name_col(df: pd.DataFrame) -> str:
    return "web_name" if "web_name" in df.columns else ("name" if "name" in df.columns else "id")

def solve_squad(df: pd.DataFrame, *, budget: float = 100.0, max_per_team: int = 3) -> List[int]:
    """Greedy value-for-money 15-man squad under FPL rules."""
    price_c = _price_col(df)
    team_c = _team_col(df)
    o1, o3, _ = _obj_cols(df)

    work = df.copy()
    work["mins_scale"] = work.apply(_mins_scale, axis=1)
    work["obj"] = work.get(o3, work.get(o1, 0.0)).fillna(0.0) * work["mins_scale"]
    work["price"] = work[price_c].astype(float)
    work["team"] = work[team_c].astype(str)
    work["pos"] = work["position"].astype(str)

    pools: Dict[str, pd.DataFrame] = {}
    for pos in _POS_NEED:
        sub = work[work["pos"] == pos].copy()
        sub["vfm"] = sub["obj"] / sub["price"].clip(lower=0.1)
        pools[pos] = sub.sort_values(["vfm", "obj"], ascending=[False, False]).reset_index(drop=True)

    remaining = float(budget)
    chosen: List[int] = []
    per_team: Dict[str, int] = {}

    # Position picking sequence to balance spend
    order = ["GK","DEF","DEF","MID","MID","FWD","DEF","MID","FWD","DEF","MID","FWD","GK","MID"]
    need_left = {k: v for k, v in _POS_NEED.items()}
    rounds: List[str] = []
    for pos in order:
        if need_left[pos] > 0:
            rounds.append(pos)
            need_left[pos] -= 1
    for pos in ["GK","DEF","MID","FWD"]:
        rounds += [pos] * max(0, _POS_NEED[pos] - rounds.count(pos))

    for pos in rounds:
        pool = pools[pos]
        picked = False
        # best value first
        for _, r in pool.iterrows():
            pid = int(r["id"])
            if pid in chosen:
                continue
            tm = r["team"]
            if per_team.get(tm, 0) >= max_per_team:
                continue
            if r["price"] > remaining + 1e-9:
                continue
            chosen.append(pid)
            remaining -= float(r["price"])
            per_team[tm] = per_team.get(tm, 0) + 1
            picked = True
            break
        if not picked:
            # fallback: cheapest viable
            cheap = pool.sort_values("price")
            for _, r in cheap.iterrows():
                pid = int(r["id"])
                if pid in chosen:
                    continue
                tm = r["team"]
                if per_team.get(tm, 0) >= max_per_team:
                    continue
                if r["price"] <= remaining + 1e-9:
                    chosen.append(pid)
                    remaining -= float(r["price"])
                    per_team[tm] = per_team.get(tm, 0) + 1
                    picked = True
                    break
    return chosen[:15]

def choose_starting_xi(df: pd.DataFrame, squad_ids: List[int]) -> Tuple[List[int], int, int]:
    """Pick a 3-4-3 XI and captain/vice by next-GW expected points × minutes scale."""
    o1, _, _ = _obj_cols(df)
    work = df[df["id"].isin(squad_ids)].copy()
    work["mins_scale"] = work.apply(_mins_scale, axis=1)
    work["obj1"] = work.get(o1, work.get("ep_total", 0.0)).fillna(0.0) * work["mins_scale"]

    xi: List[int] = []
    def top(pos: str, n: int) -> List[int]:
        sub = work[work["position"] == pos].sort_values("obj1", ascending=False)
        return [int(x) for x in sub["id"].head(n).tolist()]

    xi += top("GK", _START_NEED["GK"])
    xi += top("DEF", _START_NEED["DEF"])
    xi += top("MID", _START_NEED["MID"])
    xi += top("FWD", _START_NEED["FWD"])
    xi = xi[:11]

    starters = work[work["id"].isin(xi)].sort_values("obj1", ascending=False)
    captain = int(starters["id"].iloc[0]) if not starters.empty else (xi[0] if xi else -1)
    vice = int(starters["id"].iloc[1]) if len(starters) > 1 else (xi[0] if xi else -1)
    return xi, captain, vice

def _squad_cost(df: pd.DataFrame, ids: List[int]) -> float:
    price_c = _price_col(df)
    return float(df[df["id"].isin(ids)][price_c].astype(float).sum())

def suggest_transfers(
    df: pd.DataFrame,
    squad_ids: List[int],
    *,
    bank: float,
    transfers_allowed: int = 1,
    budget: float = 100.0,
    max_per_team: int = 3
) -> Dict[str, object]:
    """One-transfer suggestion (like-for-like by position), respecting bank & team limits."""
    price_c = _price_col(df)
    team_c = _team_col(df)
    o1, _, _ = _obj_cols(df)

    base = df.copy()
    base["mins_scale"] = base.apply(_mins_scale, axis=1)
    base["obj1"] = base.get(o1, base.get("ep_total", 0.0)).fillna(0.0) * base["mins_scale"]
    base["price"] = base[price_c].astype(float)
    base["team"] = base[team_c].astype(str)

    remaining_bank = float(bank)
    team_counts = base[base["id"].isin(squad_ids)]["team"].value_counts().to_dict()

    best = {"out": None, "in": None, "delta_ep1": 0.0}
    in_squad = set(squad_ids)

    for out_id in squad_ids:
        prow = base[base["id"] == out_id]
        if prow.empty:
            continue
        pos = prow["position"].iloc[0]
        price_out = float(prow["price"].iloc[0])
        team_out = prow["team"].iloc[0]
        max_afford = price_out + remaining_bank + 1e-9

        cand = base[(base["position"] == pos)].copy()
        cand = cand[~cand["id"].isin(in_squad - {out_id})]
        cand = cand[cand["price"] <= max_afford]

        def ok_team(tm: str) -> bool:
            cnt = team_counts.get(tm, 0)
            if tm == team_out:
                cnt -= 1  # we're removing one from this team
            return cnt < max_per_team

        cand = cand[cand["team"].apply(ok_team)]
        cand = cand.sort_values("obj1", ascending=False)
        if cand.empty:
            continue

        best_in_row = cand.iloc[0]
        delta = float(best_in_row["obj1"] - prow["obj1"].iloc[0])
        if delta > best["delta_ep1"]:
            best = {"out": int(out_id), "in": int(best_in_row["id"]), "delta_ep1": float(delta)}

    return best
