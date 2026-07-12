import streamlit as st
from datetime import date
import requests
import pandas as pd

try:
    import pybaseball as pyb
    pyb.cache.enable()
except ImportError:
    pyb = None

st.set_page_config(page_title="MLB HR Model", layout="wide")
st.title("MLB Home Run Model Dashboard")
st.write("Find good home run bets today - Full Data")

date_picked = st.date_input("Pick a day", value=date.today())

# Games
st.subheader("Today's Games")
try:
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_picked.strftime('%Y-%m-%d')}&hydrate=probablePitcher,team,venue,weather"
    data = requests.get(url).json()
    
    games = []
    for d in data.get("dates", []):
        for g in d.get("games", []):
            away = g["teams"]["away"]["team"].get("abbreviation", "N/A")
            home = g["teams"]["home"]["team"].get("abbreviation", "N/A")
            venue = g.get("venue", {}).get("name", "N/A")
            away_p = g["teams"]["away"].get("probablePitcher", {}).get("fullName", "TBD")
            home_p = g["teams"]["home"].get("probablePitcher", {}).get("fullName", "TBD")
            weather = g.get("weather", "Unknown")
            games.append({"Game": f"{away} @ {home}", "Venue": venue, "Pitchers": f"{away_p} vs {home_p}", "Weather": weather})
    
    if games:
        st.dataframe(pd.DataFrame(games))
    else:
        st.write("No games today.")
except:
    st.error("Could not load games")

# Big HR Table
st.subheader("All Home Run Candidates")
if pyb:
    try:
        with st.spinner("Pulling all available Statcast + stats..."):
            # Batting stats (season)
            batting = pyb.batting_stats(date.today().year) if pyb else pd.DataFrame()
            pitching = pyb.pitching_stats(date.today().year) if pyb else pd.DataFrame()
            
            st.write(f"Batters loaded: {len(batting)} | Pitchers loaded: {len(pitching)}")
            
            if not batting.empty:
                batting = batting[['Name', 'Team', 'Barrel%', 'HardHit%', 'ISO', 'xSLG', 'maxEV']].copy()
                batting['Model%'] = 0.20  # placeholder - replace with your math
                batting['Score'] = batting['Barrel%'] * 5 + batting['HardHit%'] * 2  # example
                
                sort_by = st.selectbox("Sort by", ["Score", "Model%", "Barrel%", "HardHit%"])
                batting = batting.sort_values(sort_by, ascending=False)
                
                st.dataframe(batting.head(50))  # show more
                
                st.write("**Pitchers**")
                st.dataframe(pitching[['Name', 'Team', 'HR9']].head(30))
    except Exception as e:
        st.error("Data error")
        st.write(str(e)[:200])
else:
    st.write("pybaseball not installed")

st.caption("Weather, full 12 criteria, Edge, Book odds coming next. Tell me what to add.")
