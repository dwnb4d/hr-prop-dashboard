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

# Games section (kept)
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

# Main HR Model
st.subheader("Home Run Value Plays")
if pyb:
    try:
        with st.spinner("Loading real-time power stats..."):
            end = date.today()
            start = end - pd.Timedelta(days=30)
            df = pyb.statcast(start_dt=start.isoformat(), end_dt=end.isoformat())
            
            if not df.empty:
                # Aggregate
                player_stats = df.groupby('player_name').agg({
                    'barrel_rate': 'mean',
                    'launch_speed': 'max',
                    'events': 'count'
                }).reset_index()
                
                player_stats.rename(columns={
                    'player_name': 'Name',
                    'barrel_rate': 'Barrel%',
                    'launch_speed': 'Max EV'
                }, inplace=True)
                
                # Simple Model% (expand with full formula later)
                player_stats['Model%'] = (player_stats['Barrel%'] * 2.5).clip(upper=0.45)
                player_stats['Score'] = player_stats['Model%'] * 100  # placeholder
                
                # Sort options
                sort_by = st.selectbox("Sort by", ["Score", "Model%", "Barrel%", "Max EV"])
                player_stats = player_stats.sort_values(sort_by, ascending=False)
                
                st.dataframe(player_stats[['Name', 'Barrel%', 'Max EV', 'Model%', 'Score']].head(15))
                
                # 12 Criteria (placeholder for now)
                st.write("12 Criteria checklist coming in next update.")
            else:
                st.write("No data yet.")
    except Exception as e:
        st.error("Statcast error")
        st.write(str(e)[:200])
else:
    st.write("pybaseball not installed")

st.caption("Real-time data + sorting added. Type 'add checklist' for the 12 criteria + full model.")
