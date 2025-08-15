import streamlit as st, pandas as pd, os, json
from planner_utils import best_xi
st.set_page_config(page_title='Team Planner', page_icon='🧩', layout='wide'); st.title('🧩 Team Planner')
P_NEXT='data/cache/projections_next_gw.csv'; P_N5='data/cache/projections_next_5gws.csv'
if not (os.path.exists(P_NEXT) and os.path.exists(P_N5)): st.warning('Run projections first.'); st.stop()
df_next=pd.read_csv(P_NEXT); df_n5=pd.read_csv(P_N5)
st.sidebar.header('Your Squad (15 players)')
upl=st.sidebar.file_uploader('Upload CSV with column id or web_name', type=['csv']); squad_ids=[]
if upl is not None:
    sdf=pd.read_csv(upl)
    if 'id' in sdf.columns: squad_ids=sdf['id'].astype(int).tolist()
    elif 'web_name' in sdf.columns: lookup=df_next.set_index('web_name')['id'].to_dict(); squad_ids=[int(lookup[n]) for n in sdf['web_name'] if n in lookup]
if not squad_ids:
    st.sidebar.caption('Or pick a quick 15 by position')
    def pick(pos,n):
        opts=df_next[df_next['position']==pos].sort_values('EP',ascending=False)
        ch=st.sidebar.multiselect(f'{pos} ({n})', opts['web_name'].tolist()[:50], max_selections=n, key=f'pick_{pos}')
        return (opts.set_index('web_name').loc[ch]['id'].tolist() if ch else [])
    gks=pick('GK',2); defs=pick('DEF',5); mids=pick('MID',5); fwds=pick('FWD',3); squad_ids=gks+defs+mids+fwds
squad=df_next[df_next['id'].isin(squad_ids)].copy()
if len(squad_ids)!=15: st.error(f'Selected {len(squad_ids)} players; need exactly 15.'); st.stop()
xi,form=best_xi(df_next, squad_ids)
if xi is None or xi.empty: st.error('Could not build a valid XI.'); st.stop()
squad['is_starter']=squad['id'].isin(xi['id'].tolist())
c1,c2,c3=st.columns(3)
with c1: st.metric('Best XI — Next GW EP', f"{xi['EP'].sum():.2f}")
with c2: st.metric('Bench EP — Next GW', f"{squad.loc[~squad['is_starter'],'EP'].sum():.2f}")
with c3: st.metric('Formation', f"{form[0]}-{form[1]}-{form[2]}")
st.subheader('Best XI — Next GW'); st.dataframe(xi[['web_name','team_name','position','price_m','EP','xg_per90','xa_per90','expected_minutes']], use_container_width=True)
st.subheader('Bench — Next GW'); st.dataframe(squad[~squad['is_starter']][['web_name','team_name','position','price_m','EP']], use_container_width=True)
