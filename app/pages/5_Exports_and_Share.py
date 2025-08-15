import streamlit as st, pandas as pd, os
from exporter import df_to_csv_bytes, tables_pdf
st.set_page_config(page_title='Exports & Share', page_icon='📤', layout='wide'); st.title('📤 Exports')
p='data/cache/projections_next_gw.csv'
if not os.path.exists(p): st.warning('No projections.'); st.stop()
df=pd.read_csv(p)
gk=df[df['position']=='GK'].sort_values('EP',ascending=False).head(1)
defs=df[df['position']=='DEF'].sort_values('EP',ascending=False).head(3)
mids=df[df['position']=='MID'].sort_values('EP',ascending=False).head(4)
fwds=df[df['position']=='FWD'].sort_values('EP',ascending=False).head(3)
xi=pd.concat([gk,defs,mids,fwds])
bench=df[~df['id'].isin(xi['id'])].sort_values('EP',ascending=False).head(4)
st.subheader('Best XI (auto) — Next GW'); st.dataframe(xi[['web_name','team_name','position','EP','price_m']], use_container_width=True)
st.subheader('Bench (auto) — Next GW'); st.dataframe(bench[['web_name','team_name','position','EP','price_m']], use_container_width=True)
fname='fpl_plan'
c1,c2,c3=st.columns(3)
with c1: st.download_button('⬇️ Best XI (CSV)', data=df_to_csv_bytes(xi[['web_name','team_name','position','EP','price_m']]), file_name=f'{fname}_best_xi.csv')
with c2: st.download_button('⬇️ Bench (CSV)', data=df_to_csv_bytes(bench[['web_name','team_name','position','EP','price_m']]), file_name=f'{fname}_bench.csv')
with c3:
    pdf=tables_pdf('FPL Plan', {'Best XI — Next GW':xi[['web_name','team_name','position','EP','price_m']], 'Bench — Next GW':bench[['web_name','team_name','position','EP','price_m']]})
    st.download_button('⬇️ Plan (PDF)', data=pdf, file_name=f'{fname}.pdf', mime='application/pdf')
