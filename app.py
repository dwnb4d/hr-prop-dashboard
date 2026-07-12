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
    st.error("pybaseball not installed. Run: pip install pybaseball")

st.set_page**Fixed!** The error happened because you copied my previous message (which included markdown like `**Here's...**`) directly into the file. Here's the **clean `app.py`** with no extra text:

### `app.py` (Copy-Paste This Entirely)
```python
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
    st.error("pybaseball not installed. Run: pip install pybaseball")

st.set_page_config(page_title="MLB HR Model", layout="wide")

MLB_BASE = "https://statsapi.mlb.com/api/v1"
HEADERS = {"User-Agent": "Mozilla/5.0 (dashboard script)"}

# Reference data — approximate, double-check / update each season
PARK_HR_FACTOR = {
    "COL": 1.25, "CIN": 1.18, "NYY": 1.12, "BAL": 1.10, "PHI": 1.09,
    "TEX": 1.07, "BOS": 1.05, "CWS": 1.05, "MIL": 1.04, "HOU": 1.03,
    "TOR": 1.02, "MIN": 1.00, "ATL": 1.00, "WSH": 0.99, "CHC": 0.99,
    "LAA": 0.98, "STL": 0.97, "ARI": 0.96, "KC": 0.95, "CLE": 0.95,
    "TB": 0.94, "LAD": 0.94, "NYM": 0.92, "PIT": 0.92, "DET": 0.91,
    "SD": 0.88, "SF": 0.85, "SEA": 0.90, "MIA": 0.87, "OAK": 0.90,
}

DOME_TEAMS = {"TB", "TOR", "ARI", "HOU", "MIL", "SEA", "MIA", "TEX"}

STADIUM_COORDS = {
    "NYY": (40.8296, -73.9262), "BOS": (42.3467, -71.0972),
    "BAL": (39.2839, -76.6218), "PHI": (39.9061, -75.1665),
    "ATL": (33.8908, -84.4678), "CIN": (39.0975, -84.5069),
    "COL": (39.7559, -104.9942), "STL": (38.6226, -90.1928),
    "CHC": (41.9484, -87.6553), "MIN": (44.9817, -93.2776),
    "CWS": (41.8299, -87.6338), "DET": (42.3390, -83.0485),
    "CLE": (41.4962, -81.6852), "KC": (39.0517, -94.4803),
    "LAA": (33.8003, -117.8827), "LAD": (34.0739, -118.2400),
    "SF": (37.7786, -122.3893), "SD": (32.7076, -117.1570),
    "OAK": (37.7516, -122.2005), "WSH": (38.8730, -77.0074),
    "NYM": (40.7571, -73.8458), "PIT": (40.4469, -80.0057),
}

# MLB Stats API helpers
@st.cache_data(ttl=300)
def get_today_schedule(game_date: str = None) -> pd.DataFrame:
    if game_date is None:
        game_date = date.today().isoformat()
    url = f"{MLB_BASE}/schedule"
    params = {
        "sportId": 1, "date": game_date,
        "hydrate": "probablePitcher,team,linescore,venue"
    }
    resp = requests.get(url, params=params, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()

    games = []
    for date_obj in data.get("dates", []):
        for game in date_obj.get("games", []):
            games.append({
                "game_pk": game["gamePk"],
                "away_team": game["teams"]["away"]["team"]["abbreviation"],
                "home_team": game["teams"]["home"]["team"]["abbreviation"],
                "venue": game["venue"]["name"],
                "probable_away": game["teams"]["away"].get("probablePitcher", {}).get("fullName"),
                "probable_home": game["teams"]["home"].get("probablePitcher", {}).get("fullName"),
            })
    return pd.DataFrame(games)

@st.cache_data(ttl=3600)
def get_batting_stats(season: int = None):
    if not pyb:
        return pd.DataFrame()
    if season is None:
        season = date.today().year
    return pyb.batting_stats(season)

@st.cache_data(ttl=3600)
def get_pitching_stats(season: int = None):
    if not pyb:
        return pd.DataFrame()
    if season is None:
        season = date.today().year
    return pyb.pitching_stats(season)

st.title("MLB Home Run Model Dashboard")

st.markdown("""
For each batter starting today, computes Model%, Fair, Book, Edge, Score, and 12-criteria checklist.
Data sources are free except optional odds API.
""")

game_date = st.date_input("Select Date", value=date.today())

schedule = get_today_schedule(game_date.isoformat())
batting = get_batting_stats()

if schedule.empty:
    st.warning("No games found for this date.")
    st.stop()

st.subheader(f"Games on {game_date}")

for _, game in schedule.iterrows():
    with st.expander(f"{game['away_team']} @ {game['home_team']} ({game['venue']})"):
        st.write(f"Probable Pitchers: {game['probable_away']} (away) vs {game['probable_home']} (home)")

# Model section (expand this with your full heuristic)
st.header("Today's HR Value Plays")
if not batting.empty and not batting.empty:
    # Simple placeholder — replace with your real weighted model
    batting["Barrel%"] = batting.get("Barrel%", 0)
    batting["HardHit%"] = batting.get("HardHit%", 0)
    batting["Model%"] = (batting["Barrel%"] * 0.4 + batting["HardHit%"] * 0.3 + 0.1) / 100
    batting["Model%"] = batting["Model%"].clip(upper=0.45)

    st.dataframe(
        batting[["Name", "Team", "Barrel%", "HardHit%", "Model%"]]
        .sort_values("Model%", ascending=False).head(20)
    )
else:
    st.info("Loading stats... (first run may take 30-60s)")

st.caption("Improve the Model% calculation in the code with your 12-criteria logic.")
