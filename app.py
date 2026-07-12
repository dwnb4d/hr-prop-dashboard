import streamlit as st
from datetime import date
import requests
import pandas as pd

st.set_page_config(page_title="MLB HR Model", layout="wide")
st.title("MLB Home Run Model Dashboard")
st.write("Find good home run bets today")

date_picked = st.date_input("Pick a day", value=date.today())

# Load games
try:
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_picked.strftime('%Y-%m-%d')}&hydrate=probablePitcher,team,venue"
    data = requests.get(url).json()
    
    st.success("Games loaded!")
    
    games = []
    for d in data.get("dates", []):
        for g in d.get("games", []):
            away = g["teams"]["away"]["team"].get("abbreviation", "N/A")
            home = g["teams"]["home"]["team"].get("abbreviation", "N/A")
            venue = g.get("venue", {}).get("name", "N/A")
            away_p = g["teams"]["away"].get("probablePitcher", {}).get("fullName", "TBD")
            home_p = g["teams"]["home"].get("probablePitcher", {}).get("fullName", "TBD")
            
            games.append({
                "Game": f"{away} @ {home}",
                "Venue": venue,
                "Pitchers": f"{away_p} vs {home_p}"
            })
    
    if games:
        st.dataframe(pd.DataFrame(games))
    else:
        st.write("No games on this day.")
        
except:
    st.error("Could not load games")

st.write("---")
st.header("Home Run Candidates")
st.write("Power stats loading... (this part is still basic)")

st.caption("We can make the Model% and 12 criteria better next. Let me know what to improve!")
