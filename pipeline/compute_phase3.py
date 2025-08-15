
from __future__ import annotations
import argparse, json, os, pandas as pd, numpy as np
from metrics import POSITION_MAP, expected_minutes, get_attack_multiplier, get_cs_prob, compute_fixture_ep

def load_inputs():
    b=json.load(open("data/cache/bootstrap-static.json","r",encoding="utf-8"))
    f=json.load(open("data/cache/fixtures.json","r",encoding="utf-8"))
    x=pd.read_csv("data/cache/xgxa_players.csv")
    return b,f,x

def completed_events(bootstrap): return sum(1 for e in bootstrap['events'] if e.get('finished'))

def current_event(bootstrap):
    cur=[e for e in bootstrap['events'] if e.get('is_current')]
    if cur: return int(cur[0]['id'])
    nxt=[e for e in bootstrap['events'] if e.get('is_next')]
    if nxt: return int(nxt[0]['id'])
    return 1

def build_players_df(bs):
    p=pd.DataFrame(bs['elements'])
    pos=pd.DataFrame(bs['element_types'])[['id','singular_name_short']].rename(columns={'id':'element_type','singular_name_short':'pos_short'})
    t=pd.DataFrame(bs['teams'])[['id','name']].rename(columns={'id':'team','name':'team_name'})
    p=p.merge(pos,on='element_type').merge(t,on='team')
    p['position']=p['element_type'].map(POSITION_MAP)
    p['price_m']=p['now_cost']/10.0
    return p

def fixtures_for_event(fixtures,ev):
    import pandas as pd
    df=pd.DataFrame(fixtures); return df[df['event']==ev].copy()

def project_event(bs,fixtures,dfx,ev):
    players=build_players_df(bs); df_ev=fixtures_for_event(fixtures,ev)
    if 'fpl_id' in dfx.columns:
        dfx['fpl_id']=pd.to_numeric(dfx['fpl_id'],errors='coerce')
        m=players.merge(dfx,left_on='id', right_on='fpl_id', how='left')
    else:
        players['merge_name']=(players['first_name'].str.lower()+' '+players['second_name'].str.lower()).str.strip()
        dfx['merge_name']=dfx.get('fpl_name', dfx.get('provider_match_name')).astype(str).str.lower().str.strip()
        m=players.merge(dfx,on='merge_name',how='left')
    for c in ['xg_per90','xa_per90']:
        if c not in m.columns: m[c]=0.0
        m[c]=m[c].fillna(0.0)
    comp=completed_events(bs)
    atk_map, cs_map = {}, {}
    for _,fx in df_ev.iterrows():
        hd=int(fx.get('team_h_difficulty',3)); ad=int(fx.get('team_a_difficulty',3))
        atk_map[int(fx['team_h'])]=get_attack_multiplier(ad)
        atk_map[int(fx['team_a'])]=get_attack_multiplier(hd)
        cs_map[int(fx['team_h'])]=get_cs_prob(hd); cs_map[int(fx['team_a'])]=get_cs_prob(ad)
    m['chance_of_playing_next_round']=pd.to_numeric(m['chance_of_playing_next_round'],errors='coerce')
    m['expected_minutes']=m.apply(lambda r: expected_minutes(r.get('minutes',0.0), comp, r.get('chance_of_playing_next_round', None)), axis=1)
    m['attack_mult']=m['team'].map(lambda tid: atk_map.get(int(tid),1.0))
    m['cs_prob']=m['team'].map(lambda tid: cs_map.get(int(tid),0.30))
    m['EP']=m.apply(lambda r: compute_fixture_ep(r, r['position']), axis=1)
    m['VFM']=m['EP']/m['price_m'].replace(0,np.nan)
    keep=['id','web_name','first_name','second_name','team','team_name','position','price_m','xg_per90','xa_per90','expected_minutes','attack_mult','cs_prob','EP','VFM']
    return m[keep].sort_values('EP',ascending=False)

def project_next_n(bs,fixtures,dfx,start,n):
    out=None
    for ev in range(start, start+n):
        d=project_event(bs,fixtures,dfx,ev).rename(columns={'EP':f'EP_ev{ev}'})
        d=d[['id','web_name','team','team_name','position','price_m',f'EP_ev{ev}']]
        out=d if out is None else out.merge(d, on=['id','web_name','team','team_name','position','price_m'], how='outer')
    epcols=[c for c in out.columns if c.startswith('EP_ev')]
    out['EP_sum']=out[epcols].sum(axis=1, skipna=True); out['VFM_sum']=out['EP_sum']/out['price_m'].replace(0,np.nan)
    return out.sort_values('EP_sum',ascending=False)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--next_n",type=int,default=5); args=ap.parse_args()
    bs,fx,dx=load_inputs(); ev=current_event(bs)
    os.makedirs("data/cache",exist_ok=True)
    d1=project_event(bs,fx,dx,ev); d1.to_csv("data/cache/projections_next_gw.csv",index=False)
    dN=project_next_n(bs,fx,dx,ev,args.next_n); dN.to_csv("data/cache/projections_next_5gws.csv",index=False)
    cap=d1[d1['position'].isin(['MID','FWD'])].copy(); cap['ceiling_proxy']=(cap['xg_per90']+cap['xa_per90'])*cap['attack_mult']; cap.sort_values('EP',ascending=False).to_csv("data/cache/captaincy_rankings.csv",index=False)
    print("Projections & captaincy written to data/cache/.")

if __name__=="__main__": main()
