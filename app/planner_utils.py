from __future__ import annotations
import pandas as pd
VALID_FORMATIONS=[(3,4,3),(3,5,2),(4,4,2),(4,5,1),(4,3,3),(5,3,2),(5,4,1)]
def best_xi(df_next: pd.DataFrame, squad_ids: list[int]):
    pool=df_next[df_next['id'].isin(squad_ids)].copy()
    gk=pool[pool['position']=='GK'].sort_values('EP',ascending=False).head(1)
    if gk.empty: return pd.DataFrame(),(0,0,0)
    gk_id=set(gk['id'].tolist())
    defs=pool[(pool['position']=='DEF')&(~pool['id'].isin(gk_id))].sort_values('EP',ascending=False)
    mids=pool[(pool['position']=='MID')&(~pool['id'].isin(gk_id))].sort_values('EP',ascending=False)
    fwds=pool[(pool['position']=='FWD')&(~pool['id'].isin(gk_id))].sort_values('EP',ascending=False)
    best_total=-1.0; best_team=None; form=None
    for d,m,f in VALID_FORMATIONS:
        if len(defs)<d or len(mids)<m or len(fwds)<f: continue
        team=pd.concat([gk,defs.head(d),mids.head(m),fwds.head(f)],ignore_index=True)
        total=team['EP'].sum()
        if total>best_total: best_total=float(total); best_team=team.copy(); form=(d,m,f)
    return best_team,form
