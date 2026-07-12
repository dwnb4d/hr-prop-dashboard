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

# Stadiums with a roof — wind/temp criteria get skipped for
