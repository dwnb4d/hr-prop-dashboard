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

st.subheader("Home Run Value Plays")
if pyb:
    try:
        with st.spinner("Loading real-time stats..."):
            end = date.today()
            start = end - pd.Timedelta(days=30)
            df = pyb.statcast(start_dt=start.isoformat(), end_dt=end.isoformat())
            
            if not df.empty:
                st.write("Data loaded!")
                
                player_stats = df.groupby('player_name').agg({
                    'events': 'count'
                }).reset_index()
                
                player_stats.rename(columns={'player_name': 'Name'}, inplace=True)
                
                # Placeholder Model (we'll improve with real metrics)
                player_stats['Model%'] = 0.18
                player_stats['Score'] = 65
                
                sort_by = st.selectbox("Sort by", ["Score", "Model%"])
                player_stats = player_stats.sort_values(sort_by, ascending=False)
                
                st.dataframe(player_stats[['Name', 'Model%', 'Score']].head(20))
            else:
                st.write("No data yet.")
    except Exception as e:
        st.error("Statcast error")
        st.write(str(e)[:300])
else:
    st.write("pybaseball not installed")

st.caption("Type 'add checklist' for full 12 criteria + better Model%.")
