"""
MLB Live Dashboard
-------------------
Watches live MLB games and alerts you when a team's batting order
changes mid-game. Uses MLB's free, official public Stats API —
no API key needed.

Run locally:
    streamlit run app.py
"""

import time
from datetime import date, datetime

import pandas as pd
import requests
import streamlit as st

BASE = "https://statsapi.mlb.com/api/v1"
BASE_V11 = "https://statsapi.mlb.com/api/v1.1"
HEADERS = {"User-Agent": "Mozilla/5.0 (dashboard script)"}

st.set_page_config(page_title="MLB Live Dashboard", layout="wide")


# ---------------------------------------------------------------------
# Data functions
# ---------------------------------------------------------------------
def get_schedule(game_date: str = None) -> dict:
    if game_date is None:
        game_date = date.today().isoformat()
    params = {"sportId": 1, "date": game_date, "hydrate": "linescore"}
    r = requests.get(f"{BASE}/schedule", params=params, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


def get_live_games(schedule_json: dict) -> list:
    live = []
    for date_block in schedule_json.get("dates", []):
        for game in date_block.get("games", []):
            if game.get("status", {}).get("abstractGameState") != "Live":
                continue
            teams = game.get("teams", {})
            live.append({
                "game_pk": game.get("gamePk"),
                "home_team": teams.get("home", {}).get("team", {}).get("name"),
                "away_team": teams.get("away", {}).get("team", {}).get("name"),
                "home_score": teams.get("home", {}).get("score"),
                "away_score": teams.get("away", {}).get("score"),
                "inning": game.get("linescore", {}).get("currentInning"),
                "inning_state": game.get("linescore", {}).get("inningState"),
            })
    return live


def get_live_feed(game_pk: int) -> dict:
    r = requests.get(f"{BASE_V11}/game/{game_pk}/feed/live", headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


def get_current_batting_order(live_feed_json: dict) -> dict:
    boxscore = live_feed_json.get("liveData", {}).get("boxscore", {})
    teams = boxscore.get("teams", {})
    result = {}
    for side in ("home", "away"):
        order = teams.get(side, {}).get("battingOrder", [])
        players = teams.get(side, {}).get("players", {})
        names = []
        for player_id in order:
            key = f"ID{player_id}"
            names.append(players.get(key, {}).get("person", {}).get("fullName", str(player_id)))
        result[side] = names
    return result


# ---------------------------------------------------------------------
# App state
# ---------------------------------------------------------------------
if "lineups" not in st.session_state:
    st.session_state.lineups = {}
if "alerts" not in st.session_state:
    st.session_state.alerts = []

st.title("⚾ MLB Live Dashboard")
st.caption("Live scores + batting order change alerts. Free MLB Stats API, no key needed.")

with st.sidebar:
    st.header("Settings")
    refresh_seconds = st.slider("Auto-refresh (seconds)", 15, 120, 30)
    auto_refresh = st.toggle("Auto-refresh", value=True)
    show_debug = st.checkbox("Show raw JSON (debug)", value=False)


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
try:
    schedule = get_schedule()
    live_games = get_live_games(schedule)
except Exception as e:
    st.error(f"Couldn't reach MLB Stats API: {e}")
    live_games = []

st.subheader("Live games")

if not live_games:
    st.info("No live MLB games right now. Check back during game hours.")
else:
    rows = [{
        "Game": f"{g['away_team']} @ {g['home_team']}",
        "Score": f"{g['away_score']} - {g['home_score']}",
        "Inning": f"{g['inning_state']} {g['inning']}",
    } for g in live_games]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.subheader("Lineup watch")
    for g in live_games:
        try:
            feed = get_live_feed(g["game_pk"])
            order = get_current_batting_order(feed)
        except Exception as e:
            if show_debug:
                st.warning(f"Feed error for {g['home_team']}: {e}")
            continue

        prev = st.session_state.lineups.get(g["game_pk"])
        if prev is not None and prev != order:
            st.session_state.alerts.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "game": f"{g['away_team']} @ {g['home_team']}",
                "change": "Batting order changed",
            })
        st.session_state.lineups[g["game_pk"]] = order

        with st.expander(f"{g['away_team']} @ {g['home_team']} — current lineups"):
            col1, col2 = st.columns(2)
            col1.write(f"**{g['away_team']}**")
            col1.write(order.get("away", []) or "Not posted yet")
            col2.write(f"**{g['home_team']}**")
            col2.write(order.get("home", []) or "Not posted yet")

    st.subheader("Alert log")
    if st.session_state.alerts:
        st.dataframe(
            pd.DataFrame(st.session_state.alerts).iloc[::-1],
            use_container_width=True, hide_index=True,
        )
    else:
        st.caption("No lineup changes detected yet this session.")

    if show_debug:
        st.subheader("Debug: raw schedule")
        st.json(schedule)

st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

if auto_refresh:
    time.sleep(refresh_seconds)
    st.rerun()
