from __future__ import annotations
import streamlit as st
import pandas as pd

PITCH_CSS = r"""
<style>
.pitch { background: #2e7d32; border-radius: 12px; padding: 12px; color: white; width: 100%; border: 2px solid #1b5e20; }
.grid { display: grid; grid-template-rows: repeat(5, 1fr); gap: 10px; }
.row { display: grid; grid-auto-flow: column; gap: 8px; justify-content: center; }
.card { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.25); border-radius: 10px; padding: 6px 8px; text-align: center; min-width: 110px; font-size: 0.9rem; }
.card .name { font-weight: 700; }
.card .meta { font-size: 0.8rem; opacity: 0.9; }
.capt { border-color: gold; box-shadow: 0 0 0 2px gold inset; }
.vice { border-color: silver; box-shadow: 0 0 0 2px silver inset; }
</style>
"""

def render_pitch(df_players: pd.DataFrame, xi_ids, captain_id=None, vice_id=None):
    st.markdown(PITCH_CSS, unsafe_allow_html=True)
    xi = df_players[df_players["id"].isin(xi_ids)].copy()
    gk = xi[xi["position"]=="GK"]
    df = xi[xi["position"]=="DEF"]
    md = xi[xi["position"]=="MID"]
    fw = xi[xi["position"]=="FWD"]
    def cards(rows):
        html = ""
        for _, r in rows.iterrows():
            cls = "card"
            if captain_id and r["id"]==captain_id: cls += " capt"
            if vice_id and r["id"]==vice_id: cls += " vice"
            html += f'<div class="{cls}"><div class="name">{r["web_name"]}</div><div class="meta">{r["team_name"]} · {r["position"]} · £{r["price"]:.1f}</div></div>'
        return html
    html = (
        '<div class="pitch">'
        '<div class="grid">'
        f'<div class="row">{cards(gk)}</div>'
        f'<div class="row">{cards(df)}</div>'
        f'<div class="row">{cards(md)}</div>'
        f'<div class="row">{cards(fw)}</div>'
        '</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
