from __future__ import annotations
import pandas as pd
from typing import List, Tuple, Dict, Optional
from collections import Counter

# ----- helpers -----
def _row(df: pd.DataFrame, pid: int) -> pd.Series:
    r = df[df["id"] == pid]
    return r.iloc[0] if not r.empty else pd.Series()

def price_of(df: pd.DataFrame, pid: int) -> float:
    r = _row(df, pid);  return float(r.get("price", 0.0)) if not r.empty else 0.0

def label_of(df: pd.DataFrame, pid: int) -> str:
    r = _row(df, pid)
    if r.empty: return f"[{pid}]"
    return f"{r.get('web_name','')} ({r.get('team_name','')}, £{float(r.get('price',0.0)):.1f})"

def ep1_of(df: pd.DataFrame, pid: int) -> float:
    # Prefer adjusted objective if present; fallback to ep_1
    r = _row(df, pid)
    if not r.empty:
        if "obj_1" in r: return float(r["obj_1"])
        return float(r.get("ep_1", r.get("ep_total", 0.0)))
    return 0.0

def pos_of(df: pd.DataFrame, pid: int) -> str:
    r = _row(df, pid);  return str(r.get("position","")) if not r.empty else ""

def team_of(df: pd.DataFrame, pid: int) -> str:
    r = _row(df, pid);  return str(r.get("team_name","")) if not r.empty else ""

def squad_value(df: pd.DataFrame, squad: List[int]) -> float:
    return round(sum(price_of(df, pid) for pid in squad), 1)

# ----- rule checks -----
POS_QUOTAS = {"GK": 2, "DEF": 5, "MID": 5, "FWD": 3}
XI_MIN = {"GK": 1, "DEF": 3, "MID": 2, "FWD": 1}

def legal_15(df: pd.DataFrame, squad: List[int]) -> bool:
    if len(squad) != 15: return False
    c = Counter(pos_of(df, pid) for pid in squad)
    for p, need in POS_QUOTAS.items():
        if c[p] != need: return False
    tc = Counter(team_of(df, pid) for pid in squad)
    return all(n <= 3 for n in tc.values())

def legal_xi(df: pd.DataFrame, xi: List[int]) -> bool:
    if len(xi) != 11: return False
    c = Counter(pos_of(df, pid) for pid in xi)
    if c["GK"] != 1: return False
    if c["DEF"] < 3 or c["MID"] < 2 or c["FWD"] < 1: return False
    return True

# ----- choose starting XI (greedy rule-aware) -----
def choose_starting_xi(df: pd.DataFrame, squad: List[int], return_bench: bool=False) -> Tuple[List[int], int, int, Optional[List[int]]]:
    pool = df[df["id"].isin(squad)].copy()
    # objective for picking XI: prefer next GW
    pool["ep"] = pool.get("obj_1", pool.get("ep_1", pool.get("ep_total", 0.0)))
    by_pos = {p: pool[pool["position"] == p].sort_values("ep", ascending=False)["id"].tolist()
              for p in ("GK","DEF","MID","FWD")}
    xi: List[int] = []
    xi += by_pos["GK"][:1]
    xi += by_pos["DEF"][:3]
    xi += by_pos["MID"][:2]
    xi += by_pos["FWD"][:1]

    chosen = set(xi)
    remaining = [pid for pid in pool.sort_values("ep", ascending=False)["id"].tolist() if pid not in chosen]
    while len(xi) < 11 and remaining:
        xi.append(remaining.pop(0))
    xi = xi[:11]

    starters = df[df["id"].isin(xi)].copy()
    starters["ep"] = starters.get("obj_1", starters.get("ep_1", starters.get("ep_total", 0.0)))
    order = starters.sort_values("ep", ascending=False)["id"].tolist()
    cpt = order[0] if order else (xi[0] if xi else 0)
    vce = order[1] if len(order) > 1 else (order[0] if order else 0)

    bench = None
    if return_bench:
        bench_candidates = [pid for pid in squad if pid not in xi]
        bench_gk = [p for p in bench_candidates if pos_of(df, p) == "GK"]
        bench_of = [p for p in bench_candidates if pos_of(df, p) != "GK"]
        bench_of = sorted(bench_of, key=lambda p: ep1_of(df, p), reverse=True)
        bench_gk = sorted(bench_gk, key=lambda p: ep1_of(df, p), reverse=True)
        bench = (bench_gk[:1] + bench_of[:3])[:4]
    return (xi, cpt, vce, bench) if return_bench else (xi, cpt, vce, None)

# ----- rebuild best 15 under budget (greedy, rule & 3/club aware) -----
def solve_squad_15(df: pd.DataFrame, budget: float, max_per_team: int=3) -> List[int]:
    frame = df.copy()
    # use longer-horizon objective for squad building
    frame["obj"] = frame.get("obj_3", frame.get("ep_3", frame.get("ep_1", 0.0)))
    chosen: List[int] = []
    team_count: Dict[str, int] = Counter()
    spent = 0.0

    for pos, need in POS_QUOTAS.items():
        pos_pool = frame[frame["position"] == pos].sort_values(["obj","price"], ascending=[False, True])
        for _ in range(need):
            picked = None
            for _, row in pos_pool.iterrows():
                pid = int(row["id"]); team = str(row["team_name"]); price = float(row["price"])
                if team_count[team] >= max_per_team: continue
                if spent + price > budget + 1e-6: continue
                picked = pid
                spent += price
                team_count[team] += 1
                chosen.append(pid)
                pos_pool = pos_pool[pos_pool["id"] != pid]
                break
            if picked is None:
                # relax: cheapest that fits budget (still respects 15 slots)
                pos_pool2 = frame[frame["position"] == pos].sort_values(["price","obj"], ascending=[True, False])
                for _, row in pos_pool2.iterrows():
                    pid = int(row["id"]); price = float(row["price"])
                    if pid in chosen: continue
                    if spent + price > budget + 1e-6: continue
                    chosen.append(pid); spent += price
                    break
    return chosen[:15]

# ----- single-transfer suggestion obeying bank/budget/3-per-team/position quotas -----
def suggest_transfers(
    df: pd.DataFrame,
    current_squad: List[int],
    budget: float,
    bank_left: float,
    transfers_allowed: int = 1,
) -> Dict[str, object]:
    """
    Returns dict with out_id, in_id, out_name, in_name, delta_ep1.
    Uses 'obj_1' (adjusted next-GW objective) if present for delta.
    """
    if len(current_squad) != 15:
        return {"out_id": None, "in_id": None, "out_name": "", "in_name": "", "delta_ep1": 0.0}

    cur_value = squad_value(df, current_squad)
    # delta uses obj_1 fallback ep_1
    def _obj1(pid: int) -> float:
        r = _row(df, pid)
        return float(r.get("obj_1", r.get("ep_1", r.get("ep_total", 0.0)))) if not r.empty else 0.0

    best = {"delta_ep1": 0.0, "out_id": None, "in_id": None, "out_name": "", "in_name": ""}

    team_count = Counter(team_of(df, pid) for pid in current_squad)
    all_ids = df["id"].astype(int).tolist()

    for out_id in current_squad:
        out_pos = pos_of(df, out_id)
        out_team = team_of(df, out_id)
        out_price = price_of(df, out_id)

        # Candidate IN must match position to keep quotas intact
        candidates = [pid for pid in all_ids if pos_of(df, pid) == out_pos and pid not in current_squad]

        # Free up one slot for the OUT team
        team_count[out_team] -= 1

        for in_id in candidates:
            in_team = team_of(df, in_id)
            in_price = price_of(df, in_id)

            # 3-per-team rule
            if team_count[in_team] >= 3: 
                continue

            # Bank/budget checks
            new_value = cur_value - out_price + in_price
            if in_price - out_price > bank_left + 1e-9:
                continue
            if new_value > budget + 1e-9:
                continue

            delta = _obj1(in_id) - _obj1(out_id)
            if delta > best["delta_ep1"]:
                best = {
                    "delta_ep1": round(delta, 3),
                    "out_id": out_id,
                    "in_id": in_id,
                    "out_name": label_of(df, out_id),
                    "in_name": label_of(df, in_id),
                }

        team_count[out_team] += 1

    return best

# Exported for UI
__all__ = [
    "squad_value",
    "choose_starting_xi",
    "solve_squad_15",
    "suggest_transfers",
]
