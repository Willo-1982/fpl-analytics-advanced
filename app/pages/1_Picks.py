import streamlit as st, pandas as pd, os
st.set_page_config(page_title='Picks', page_icon='🎯', layout='wide'); st.title('🎯 Picks — Next Gameweek')
p='data/cache/projections_next_gw.csv'
if not os.path.exists(p): st.warning('No projections. Run pipeline.'); st.stop()
df=pd.read_csv(p)
positions=sorted(df['position'].dropna().unique().tolist()); teams=sorted(df['team_name'].dropna().unique().tolist())
with st.sidebar:
    st.subheader('Filters')
    pos=st.multiselect('Positions',positions,default=positions)
    team=st.multiselect('Teams',teams,default=teams)
    price=st.slider('Max Price (m)', float(df['price_m'].min()), float(df['price_m'].max()), float(df['price_m'].max()))
    topn=st.slider('Top N',5,50,15)
mask=df['position'].isin(pos)&df['team_name'].isin(team)&(df['price_m']<=price); d=df.loc[mask].copy()
tab1,tab2=st.tabs(['Top EP','Best VFM'])
with tab1: st.dataframe(d.sort_values('EP',ascending=False).head(topn)[['web_name','team_name','position','price_m','EP','xg_per90','xa_per90','expected_minutes']], use_container_width=True)
with tab2: st.dataframe(d.sort_values('VFM',ascending=False).head(topn)[['web_name','team_name','position','price_m','VFM','EP']], use_container_width=True)
