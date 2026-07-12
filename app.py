import streamlit as st
from datetime import date
import requests

st.title("MLB Home Run Model")
st.write("Simple version working!")

date_picked = st.date_input("Pick a day", value=date.today())

try:
    url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=" + date_picked.strftime("%Y-%m-%d")
    data = requests.get(url).json()
    
    st.success("✅ Schedule loaded!")
    
    games_list = []
    for d in data.get("dates", []):
        for g in d.get("games", []):
            away_team = g["teams"]["away"]["team"].get("abbreviation", "N/A")
            home_team = g["teams"]["home"]["team"].get("abbreviation", "N/A")
            games_list.append(f"{away_team} @ {home_team}")
    
    st.write("**Games today:**")
    for game in games_list:
        st.write("• " + game)
        
except Exception as e:
    st.error("Error loading games")
    st.write(str(e)[:300])

st.write("---")
st.write("Next: We will add the home run power stats!")
