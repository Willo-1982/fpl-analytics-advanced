import streamlit as st, pandas as pd, os, matplotlib.pyplot as plt
st.set_page_config(page_title='Captaincy', page_icon='🧢', layout='wide'); st.title('🧢 Captaincy — Next GW')
p='data/cache/captaincy_rankings.csv'
if not os.path.exists(p): st.warning('No captaincy file. Run projections.'); st.stop()
df=pd.read_csv(p); topn=st.slider('Top N',5,30,15)
view=df.head(topn)[['web_name','team_name','position','price_m','EP']]; st.dataframe(view, use_container_width=True)
fig=plt.figure(); plt.bar(view['web_name'].astype(str), view['EP']); plt.xticks(rotation=45, ha='right'); plt.title('Captaincy (EP proxy)'); plt.ylabel('EP'); st.pyplot(fig, clear_figure=True)
