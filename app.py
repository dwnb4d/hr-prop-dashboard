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
st.write("Find good home run bets today")

date_picked = st.date_input("Pick a day", value=date.today())

st.subheader("Today's Games")
try:
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_picked.strftime('%Y-%m-%d')}&hydrate=probablePitcher,team,venue"
    data = requests.get(url).json()
    
    games = []
    for d in data.get("dates", []):
        for g in d.get("games", []):
            away = g["teams"]["away"]["team"].get("abbreviation", "N/A")
            home = g["teams"]["home"]["team"].get("abbreviation", "N/A")
            venue = g.get("venue", {}).get("name", "N/A")
            away_p = g["teams"]["away"].get("probablePitcher", {}).get("fullName", "TBD")
            home_p = g["teams"]["home"].get("probablePitcher", {}).get("fullName", "TBD")
            games.append({"Game": f"{away} @ {home}", "Venue": venue, "Pitchers": f"{away_p} vs {home_p}"})
    
    if games:
        st.dataframe(pd.DataFrame(games))
    else:
        st.write("No games today.")
except:
    st.error("Could not load games")

st.subheader("Home Run Candidates (All Players)")
if pyb:
    try:
        with st.spinner("Pulling all available data..."):
            batting = pyb.batting_stats_range(start_dt=(date.today() - pd.Timedelta(days=30)).isoformat())
            st.write(f"Batters loaded: {len(batting)}")
            
            if not batting.empty:
                cols = [c for c in ['Name', 'Team', 'Barrel%', 'HardHit%', 'ISO', 'xSLG', 'maxEV'] if c in batting.columns]
                display = batting[cols].copy()
                display['Model%'] = 0.20
                display['Score'] = 70
                
                sort_by = st.selectbox("Sort by", ["Score", "Model%", "Barrel%"])
                display = display.sort_values(sort_by, ascending=False)
                
                st.dataframe(display.head(100))
    except Exception as e:
        st.error("Data error")
        st.write(str(e)[:200])
else:
    st.write("pybaseball not installed")

st.caption("Full model + 12 criteria next.")
