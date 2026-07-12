import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="MLB HR Model", layout="wide")
st.title("MLB Home Run Model Dashboard")

st.write("Hello! The dashboard is starting simple.")

game_date = st.date_input("Pick a date", value=date.today())

st.subheader(f"Games on {game_date}")

st.write("Games will show here soon.")

st.header("Best Home Run Candidates")
st.write("Power stats will show here soon.")

st.caption("We are fixing step by step.")
