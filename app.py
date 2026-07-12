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

st.subheader("Home Run Candidates")
if pyb:
    try:
        with st.spinner("Loading power stats..."):
            end = date.today()
            start = end - pd.Timedelta(days=30)
            df = pyb.statcast(start_dt=start.isoformat(), end_dt=end.isoformat())
            
            if not df.empty:
                st.write("Debug: Columns found -", list(df.columns)[:15])
                
                agg_dict = {}
                if 'barrel' in df.columns:
                    agg_dict['barrel'] = 'mean'
                if 'launch_speed' in df.columns:
                    agg_dict['launch_speed'] = 'max'
                agg_dict['events'] = 'count'
                
                player_stats = df.groupby('player_name').agg(agg_dict).reset_index()
                
                player_stats.rename(columns={
                    'player_name': 'Name',
                    'barrel': 'Barrel%',
                    'launch_speed': 'Max EV'
                }, inplace=True)
                
                if 'Barrel%' in player_stats.columns:
                    player_stats['Model%'] = (player_stats['Barrel%'] * 2.5).clip(upper=0.45)
                else:
                    player_stats['Model%'] = 0.15
                
                player_stats = player_stats.sort_values('Model%', ascending=False).head(20)
                st.dataframe(player_stats)
            else:
                st.write("No Statcast data yet.")
    except Exception as e:
        st.error("Statcast error")
        st.write(str(e)[:200])
else:
    st.write("pybaseball not installed")

st.caption("Tell me what to add next (12 criteria, weather, etc.)")
