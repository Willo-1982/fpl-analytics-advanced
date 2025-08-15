import streamlit as st, pandas as pd, os, json, matplotlib.pyplot as plt
st.set_page_config(page_title='Fixtures', page_icon='📅', layout='wide'); st.title('📅 Fixture Difficulty Snapshot')
fx='data/cache/fixtures.json'; bs='data/cache/bootstrap-static.json'
if not (os.path.exists(fx) and os.path.exists(bs)): st.warning('fixtures.json or bootstrap-static.json missing.'); st.stop()
fixtures=json.load(open(fx,'r',encoding='utf-8')); bs=json.load(open(bs,'r',encoding='utf-8'))
teams=pd.DataFrame(bs['teams'])[['id','name']].rename(columns={'id':'team_id','name':'team'}); fx=pd.DataFrame(fixtures)
ev_min,ev_max=int(fx['event'].min()), int(fx['event'].max()); gw=st.slider('Gameweek range', ev_min, ev_max, (ev_min,min(ev_min+4,ev_max)))
mask=(fx['event']>=gw[0])&(fx['event']<=gw[1]); fxr=fx.loc[mask, ['event','team_h','team_a','team_h_difficulty','team_a_difficulty']].copy()
def agg(df):
    easy,hard={},{} 
    for _,r in df.iterrows():
        for side,dcol in [('team_h','team_h_difficulty'),('team_a','team_a_difficulty')]:
            tid=int(r[side]); d=int(r[dcol]); easy[tid]=easy.get(tid,0)+(1 if d in (1,2) else 0); hard[tid]=hard.get(tid,0)+(1 if d in (4,5) else 0)
    return pd.DataFrame([{'team_id':t,'easy_fixtures':easy.get(t,0),'hard_fixtures':hard.get(t,0)} for t in set(list(easy.keys())+list(hard.keys()))])
agg=agg(fxr).merge(teams,on='team_id',how='left'); st.dataframe(agg.sort_values(['easy_fixtures','hard_fixtures'],ascending=[False,True]), use_container_width=True)
fig=plt.figure(); v=agg.sort_values('easy_fixtures',ascending=False); plt.bar(v['team'].astype(str), v['easy_fixtures']); plt.xticks(rotation=45, ha='right'); plt.title('Easy Fixtures (range)'); plt.ylabel('Count'); st.pyplot(fig, clear_figure=True)
