import streamlit as st
from datetime import date

st.title("My Home Run App")
st.write("Hello! This is a test.")

date_picked = st.date_input("Pick a day", value=date.today())
st.write("You picked:", date_picked)

st.write("If you see this message, it works!")
