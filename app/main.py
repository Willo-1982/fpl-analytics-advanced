# app/main.py  — safe Streamlit entrypoint

import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent  # .../app

import streamlit as st

# Basic layout (you can customize later)
st.set_page_config(page_title="FPL Analytics", layout="wide")
st.title("FPL Analytics Home")
st.write(
    "Use the sidebar to open **Team Builder**, **Captaincy**, **Fixtures**, etc. "
    "If Team Builder errors, double-check that projections CSVs exist in `data/cache/`."
)
st.sidebar.title("Navigation")
st.sidebar.info("Pages appear in the sidebar automatically (0_Team_Builder, Captaincy, Fixtures, ...)")
