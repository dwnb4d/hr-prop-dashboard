import streamlit as st
from datetime import date

st.title("Test Dashboard")
st.write("If you see this, Streamlit works!")

game_date = st.date_input("Pick a date", value=date.today())
st.write(f"Selected date: {game_date}")
