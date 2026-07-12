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

# Games section
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
            
            games.append({
                "Game": f"{away} @ {home}",
                "Venue": venue,
                "Pitchers": f"{away_p} vs {home_p}"
            })
    
    if games:
        st.dataframe(pd.DataFrame(games))
    else:
        st.write("No games today.")
        
except:
    st.error("Could not load games")

# Power Stats section
st.subheader("Home Run Candidates")
if pyb:
    try:
        with st.spinner("Loading power stats..."):
            end = date.today()
            start = end - pd.Timedelta(days=30)
            df = pyb.statcast(start_dt=start.isoformat(), end_dt=end.isoformat())
            
            if not df.empty:
                player_stats = df.groupby('player_name').agg({
                    'barrel': 'mean',
                    'launch_speed': 'max',
                    'events': 'count'
                }).reset_index()
                
                player_stats.rename(columns={
                    'player_name': 'Name',
                    'barrel': 'Barrel%',
                    'launch_speed': 'Max EV'
                }, inplace=True)
                
                player_stats['Model%'] = (player_stats['Barrel%'] * 2.5).clip(upper=0.45)
                player_stats = player_stats.sort_values('Model%', ascending=False)
                
                st.dataframe(player_stats[['Name', 'Barrel%', 'Max EV', 'Model%']].head(20))
            else:
                st.write("No recent Statcast data yet.")
    except Exception as e:
        st.error("Statcast loading issue")
        st.write(str(e)[:150])
else:
    st.write("pybaseball not installed")

st.caption("This is the foundation. We can now add your 12 criteria, weather, park factors, and odds next.")
