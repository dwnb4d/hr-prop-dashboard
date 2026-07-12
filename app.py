import streamlit as st
from datetime import date
import pandas as pd
import requests

st.title("MLB Home Run Model")
st.write("Simple version - let's see if games load")

date_picked = st.date_input("Pick a day", value=date.today())

# Try to load games
try:
    url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=" + date_picked.strftime("%Y-%m-%d")
    data = requests.get(url).json()
    
    st.write("✅ Schedule loaded!")
    games = []
    for d in data.get("dates", []):
        for g in d.get("games", []):
            away = g["teams"]["away"]["team"]["abbreviation"]
            home = g["teams"]["home"]["team"]["abbreviation"]
            games.append(f"{away} @ {home}")
    
    st.write("Today's games:")
    for game in games:
        st.write("• " + game)
        
except Exception as e:
    st.error("Could not load games")
    st.write(str(e)[:200])

st.write("---")
st.write("Power stats coming soon!")
