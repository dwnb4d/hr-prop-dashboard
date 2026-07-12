import math
from datetime import date, datetime
import pandas as pd
import requests
import streamlit as st

try:
    import pybaseball as pyb
    pyb.cache.enable()
except ImportError:
    pyb = None
    st.error("Install pybaseball: pip install pybaseball")

st.set_page_config(page_title="MLB HR Model", layout="wide")

MLB_BASE = "https://statsapi.mlb.com/api/v1"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# Park and dome data (you already had this)
PARK_HR_FACTOR = {
    "COL": 1.25, "CIN": 1.18, "NYY": 1.12, "BAL": 1.10, "PHI": 1.09,
    "TEX": 1.07, "BOS": 1.05, "CWS": 1.05, "MIL": 1.04, "HOU": 1.03,
    "TOR": 1.02, "MIN": 1.00, "ATL": 1.00, "WSH": 0.99, "CHC": 0.99,
    "LAA": 0.98, "STL": 0.97, "ARI": 0.96, "KC": 0.95, "CLE": 0.95,
    "TB": 0.94, "LAD": 0.94, "NYM": 0.92, "PIT": 0.92, "DET": 0.91,
    "SD": 0.88, "SF": 0.85, "SEA": 0.90, "MIA": 0.87, "OAK": 0.90,
}

DOME_TEAMS = {"TB", "TOR", "ARI", "HOU", "MIL", "SEA", "MIA", "TEX"}

st.title("MLB Home Run Model Dashboard")

st.write("This shows good home run hitters today using real power stats.")

game_date = st.date_input("Pick a date", value=date.today())

@st.cache_data(ttl=3600)
def get_games(game_date_str):
    url = f"{MLB_BASE}/schedule"
    params = {"sportId": 1, "date": game_date_str, "hydrate": "probablePitcher,venue"}
    resp = requests.get(url, params=params, headers=HEADERS)
    data = resp.json()
    games = []
    for d in data.get("dates", []):
        for g in d.get("games", []):
            games.append({
                "away": g["teams"]["away"]["team"]["abbreviation"],
                "home": g["teams"]["home"]["team"]["abbreviation"],
                "venue": g["venue"]["name"],
                "away_pitcher": g["teams"]["away"].get("probablePitcher", {}).get("fullName", "TBD"),
                "home_pitcher": g["teams"]["home"].get("probablePitcher", {}).get("fullName", "TBD"),
            })
    return pd.DataFrame(games)

games_df = get_games(game_date.isoformat())

st.subheader(f"Games on {game_date}")
for _, g in games_df.iterrows():
    with st.expander(f"{g['away']} @ {g['home']} - {g['venue']}"):
        st.write(f"Pitchers: {g['away_pitcher']} (away) vs {g['home_pitcher']} (home)")

# === NEW PART: Get real power stats ===
@st.cache_data(ttl=1800)
def get_power_stats():
    if not pyb:
        return pd.DataFrame()
    try:
        # Get recent games (last 30 days)
        end = date.today()
        start = end - pd.Timedelta(days=30)
        df = pyb.statcast(start_dt=start.isoformat(), end_dt=end.isoformat())
        
        if df.empty:
            return pd.DataFrame()
        
        # Group by batter to make player stats
        player_stats = df.groupby(['batter', 'player_name']).agg({
            'barrel': 'mean',
            'launch_speed': 'max',           # Max EV
            'hit_distance_sc': 'mean',
            'launch_angle': 'mean',
            'events': 'count'
        }).reset_index()
        
        player_stats.rename(columns={
            'player_name': 'Name',
            'barrel': 'Barrel%',
            'launch_speed': 'Max_EV'
        }, inplace=True)
        
        player_stats['HardHit%'] = 0.5  # placeholder
        player_stats['Model%'] = player_stats['Barrel%'] * 2 + 0.1  # very simple for now
        
        return player_stats.sort_values('Model%', ascending=False)
        
    except Exception as e:
        st.error(f"Error getting stats: {str(e)[:100]}")
        return pd.DataFrame()

st.header("Best Home Run Candidates Today")
power_df = get_power_stats()

if not power_df.empty:
    st.dataframe(power_df[['Name', 'Barrel%', 'Max_EV', 'Model%']].head(25))
else:
    st.info("Waiting for stats... First time can take a minute.")

st.caption("This is a simple version. We will make the Model% smarter later with your 12 rules.")
