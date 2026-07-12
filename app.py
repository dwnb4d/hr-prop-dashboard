"""
MLB Home Run Model Dashboard
------------------------------
For each batter starting today, computes:
  Model%  - our modeled probability of hitting a HR today
  Fair    - American odds equivalent of Model% (no vig)
  Book    - best posted sportsbook price (REQUIRES an odds API key -
            see the "Book odds setup" section below. Shows "—" until
            you add one.)
  Edge    - Model% minus the market-implied probability from Book
  Score   - composite ranking combining Model%, Edge, and Statcast grade
  12-criteria checklist

Data sources (all free, no key needed for the model itself):
  - MLB Stats API (statsapi.mlb.com)      -> schedule, lineups, pitchers
  - pybaseball / Baseball Savant           -> Statcast batter & pitcher metrics
  - National Weather Service API           -> temp + wind for outdoor parks

IMPORTANT HONESTY NOTE:
This model is a hand-built heuristic (weighted combination of Statcast
z-scores), not a professionally trained/backtested model. Treat Model%
as a rough signal, not a guarantee. Also: Statcast scraping via
pybaseball can occasionally change column names upstream — use the
"Show raw data (debug)" toggle if a column looks empty, and check the
README for how to fix it.
"""

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

st.set_page_config(page_title="MLB HR Model", layout="wide")

MLB_BASE = "https://statsapi.mlb.com/api/v1"
HEADERS = {"User-Agent": "Mozilla/5.0 (dashboard script)"}

# ---------------------------------------------------------------------
# Reference data — approximate, double-check / update each season
# ---------------------------------------------------------------------

# Rough single-season HR park factors (1.00 = neutral). APPROXIMATE.
# Update these from Baseball Savant's park factor page each season.
PARK_HR_FACTOR = {
    "COL": 1.25, "CIN": 1.18, "NYY": 1.12, "BAL": 1.10, "PHI": 1.09,
    "TEX": 1.07, "BOS": 1.05, "CWS": 1.05, "MIL": 1.04, "HOU": 1.03,
    "TOR": 1.02, "MIN": 1.00, "ATL": 1.00, "WSH": 0.99, "CHC": 0.99,
    "LAA": 0.98, "STL": 0.97, "ARI": 0.96, "KC": 0.95, "CLE": 0.95,
    "TB": 0.94, "LAD": 0.94, "NYM": 0.92, "PIT": 0.92, "DET": 0.91,
    "SD": 0.88, "SF": 0.85, "SEA": 0.90, "MIA": 0.87, "OAK": 0.90,
}

# Stadiums with a roof — wind/temp criteria get skipped for these.
# Note: several of these are retractable and sometimes play outdoors;
# treated as closed/dome by default since roof status isn't reliably
# available for free. Adjust with the manual override in the sidebar
# if you know the roof is open for a specific game.
DOME_TEAMS = {"TB", "TOR", "ARI", "HOU", "MIL", "SEA", "MIA", "TEX"}

# Approximate stadium coordinates for weather lookups (outdoor parks only)
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

# ---------------------------------------------------------------------
# MLB Stats API helpers
# ---------------------------------------------------------------------

@st.cache_data(ttl=300)
def get_today_schedule(game_date: str = None) -> dict:
    if game_date is None:
        game_date = date.today().isoformat()
    params = {
        "sportId": 1, "date": game_date,
        "hydrate": "probablePitcher,team,linescore",
    }
