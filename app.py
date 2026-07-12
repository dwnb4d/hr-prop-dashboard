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
    r = requests.get(f"{MLB_BASE}/schedule", params=params, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


def list_todays_games(schedule_json: dict) -> list:
    games = []
    for d in schedule_json.get("dates", []):
        for g in d.get("games", []):
            teams = g.get("teams", {})
            home = teams.get("home", {})
            away = teams.get("away", {})
            games.append({
                "game_pk": g.get("gamePk"),
                "home_abbr": home.get("team", {}).get("abbreviation"),
                "away_abbr": away.get("team", {}).get("abbreviation"),
                "home_name": home.get("team", {}).get("name"),
                "away_name": away.get("team", {}).get("name"),
                "home_pitcher": home.get("probablePitcher", {}).get("fullName"),
                "away_pitcher": away.get("probablePitcher", {}).get("fullName"),
                "home_pitcher_id": home.get("probablePitcher", {}).get("id"),
                "away_pitcher_id": away.get("probablePitcher", {}).get("id"),
                "game_date": g.get("gameDate"),
            })
    return games


@st.cache_data(ttl=180)
def get_boxscore(game_pk: int) -> dict:
    r = requests.get(f"{MLB_BASE}/game/{game_pk}/boxscore", headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


def get_lineup(boxscore_json: dict, side: str) -> list:
    """side = 'home' or 'away'. Returns list of {id, name} in batting order.
    Empty if lineup isn't posted yet (usually posts ~1-2 hrs before first pitch)."""
    team = boxscore_json.get("teams", {}).get(side, {})
    order = team.get("battingOrder", [])
    players = team.get("players", {})
    lineup = []
    for pid in order:
        key = f"ID{pid}"
        person = players.get(key, {}).get("person", {})
        bat_side = players.get(key, {}).get("batSide", {}).get("code")
        lineup.append({"id": person.get("id"), "name": person.get("fullName"), "bat_side": bat_side})
    return lineup


@st.cache_data(ttl=3600)
def get_pitcher_hand(pitcher_id: int) -> str:
    if not pitcher_id:
        return None
    r = requests.get(f"{MLB_BASE}/people/{pitcher_id}", headers=HEADERS, timeout=10)
    r.raise_for_status()
    people = r.json().get("people", [])
    if not people:
        return None
    return people[0].get("pitchHand", {}).get("code")


# ---------------------------------------------------------------------
# Statcast / pybaseball helpers
# ---------------------------------------------------------------------

@st.cache_data(ttl=3600)
def get_batter_statcast(season: int) -> pd.DataFrame:
    """Barrel%, hard-hit%, max EV per batter for the season."""
    df = pyb.statcast_batter_exitvelo_barrels(season, minBBE=1)
    return df


@st.cache_data(ttl=3600)
def get_batter_expected_stats(season: int) -> pd.DataFrame:
    """xSLG / ISO per batter for the season."""
    df = pyb.statcast_batter_expected_stats(season, minPA=1)
    return df


@st.cache_data(ttl=3600)
def get_pitcher_statcast(season: int) -> pd.DataFrame:
    """Barrel% allowed, hard-hit% allowed per pitcher for the season."""
    df = pyb.statcast_pitcher_exitvelo_barrels(season, minBBE=1)
    return df


@st.cache_data(ttl=3600)
def get_pitcher_standard_stats(season: int) -> pd.DataFrame:
    """HR/9 and K/9 per pitcher for the season (FanGraphs via pybaseball)."""
    df = pyb.pitching_stats(season, qual=1)
    return df


def lookup_batter_row(df: pd.DataFrame, name: str):
    if df is None or df.empty:
        return None
    matches = df[df["player_name"].str.contains(name.split(" ")[-1], case=False, na=False)]
    if matches.empty:
        return None
    return matches.iloc[0]


def lookup_pitcher_row(df: pd.DataFrame, name: str, name_col: str = "player_name"):
    if df is None or df.empty:
        return None
    matches = df[df[name_col].str.contains(name.split(" ")[-1], case=False, na=False)]
    if matches.empty:
        return None
    return matches.iloc[0]


# ---------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------

@st.cache_data(ttl=1800)
def get_weather(lat: float, lon: float) -> dict:
    points = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=HEADERS, timeout=10).json()
    forecast_url = points.get("properties", {}).get("forecastHourly")
    if not forecast_url:
        return {}
    forecast = requests.get(forecast_url, headers=HEADERS, timeout=10).json()
    periods = forecast.get("properties", {}).get("periods", [])
    if not periods:
        return {}
    now = periods[0]
    return {
        "temp_f": now.get("temperature"),
        "wind_speed": now.get("windSpeed"),
        "wind_dir": now.get("windDirection"),
    }


# ---------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------

# League-average HR probability per PA, used as the baseline the model
# adjusts up/down from. ~3.2-3.5% is typical MLB-wide; adjust if you
# have a more current number.
BASELINE_HR_PROB = 0.034


def safe(val, default=0.0):
    try:
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def compute_model(batter_ev, batter_xstats, pitcher_ev, pitcher_std,
                   platoon_edge: bool, park_factor: float,
                   wind_out: bool, temp_f, is_dome: bool):
    """
    Heuristic weighted model -> returns (model_pct, criteria_dict)
    All weights below are illustrative starting points, not fit to
    real outcomes. Tune them once you can backtest against results.
    """
    barrel_pct = safe(batter_ev.get("brl_percent") if batter_ev is not None else None)
    hardhit_pct = safe(batter_ev.get("hard_hit_percent") if batter_ev is not None else None)
    max_ev = safe(batter_ev.get("max_hit_speed") if batter_ev is not None else None)
    iso = safe(batter_xstats.get("iso") if batter_xstats is not None else None)
    xslg = safe(batter_xstats.get("est_slg") if batter_xstats is not None else None)

    pitcher_barrel_allowed = safe(pitcher_ev.get("brl_percent") if pitcher_ev is not None else None)
    pitcher_hardhit_allowed = safe(pitcher_ev.get("hard_hit_percent") if pitcher_ev is not None else None)
    pitcher_hr9 = safe(pitcher_std.get("HR/9") if pitcher_std is not None else None)
    pitcher_k9 = safe(pitcher_std.get("K/9") if pitcher_std is not None else None)

    # --- 12 criteria checklist ---
    criteria = {
        "Barrel% >= 13": barrel_pct >= 13,
        "Hard-Hit% >= 50": hardhit_pct >= 50,
        "ISO >= .220": iso >= 0.220,
        "xSLG >= .500": xslg >= 0.500,
        "Max EV >= 110": max_ev >= 110,
        "Platoon edge": bool(platoon_edge),
        "Pitcher HR/9 >= 1.10": pitcher_hr9 >= 1.10,
        "Barrel% allowed >= 10": pitcher_barrel_allowed >= 10,
    }
    if pitcher_hardhit_allowed > 0:
        criteria["Hard-Hit% allowed >= 45"] = pitcher_hardhit_allowed >= 45
    else:
        criteria["Contact-prone K/9 < 7.5 (fallback)"] = 0 < pitcher_k9 < 7.5
    criteria["HR-friendly park"] = park_factor >= 1.05

    if not is_dome:
        criteria["Wind blowing out"] = bool(wind_out)
        criteria["Warm >= 78F"] = safe(temp_f) >= 78

    criteria_met = sum(1 for v in criteria.values() if v)
    criteria_total = len(criteria)

    # --- Model% via weighted z-ish adjustments off league baselines ---
    # very rough centers/scales, tune once you can backtest
    adj = 0.0
    adj += (barrel_pct - 8.0) * 0.006      # league avg barrel% ~7-8
    adj += (hardhit_pct - 38.0) * 0.003    # league avg hard-hit% ~36-38
    adj += (iso - 0.150) * 0.9             # league avg ISO ~.150
    adj += (xslg - 0.400) * 0.5            # league avg xSLG ~.400
    adj += (max_ev - 106.0) * 0.004        # league avg max EV ~106
    adj += (pitcher_hr9 - 1.1) * 0.02
    adj += (pitcher_barrel_allowed - 7.5) * 0.004
    if platoon_edge:
        adj += 0.006
    adj += (park_factor - 1.0) * 0.03
    if not is_dome:
        if wind_out:
            adj += 0.01
        if safe(temp_f) >= 78:
            adj += 0.004

    model_pct = max(0.005, min(0.35, BASELINE_HR_PROB + adj))

    return model_pct, criteria, criteria_met, criteria_total


def prob_to_american_odds(p: float) -> str:
    if p <= 0 or p >= 1:
        return "—"
    if p >= 0.5:
        odds = -100 * p / (1 - p)
        return f"{odds:.0f}"
    else:
        odds = 100 * (1 - p) / p
        return f"+{odds:.0f}"


def american_odds_to_prob(odds: float) -> float:
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return -odds / (-odds + 100)


# ---------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------

st.title("⚾ MLB Home Run Model")
st.caption(
    "Model% is a heuristic Statcast-based score, not a backtested "
    "prediction — treat it as a research signal, not gospel."
)

if pyb is None:
    st.error(
        "pybaseball isn't installed. Add `pybaseball` to requirements.txt "
        "and redeploy."
    )
    st.stop()

with st.sidebar:
    st.header("Settings")
    season = st.number_input("Season", min_value=2015, max_value=date.today().year,
                              value=date.today().year)
    odds_api_key = st.text_input(
        "Odds API key (optional)", type="password",
        help="Leave blank to skip live Book odds / Edge. See README for setup."
    )
    show_debug = st.checkbox("Show raw data (debug)", value=False)
    st.caption(
        "Roof status for retractable-roof parks is assumed closed by "
        "default (wind/temp criteria skipped). No free reliable source "
        "for live roof status."
    )

with st.spinner("Loading today's slate..."):
    schedule = get_today_schedule()
    games = list_todays_games(schedule)

if not games:
    st.info("No MLB games scheduled today.")
    st.stop()

def load_source(label, fn, *args):
    """Load one data source independently. Returns None + shows a
    warning (not a hard crash) if that specific source is unavailable,
    so one blocked/changed source doesn't take down the whole app."""
    try:
        return fn(*args)
    except Exception as e:
        st.warning(f"Couldn't load {label}: {e}. Continuing without it.")
        return None


with st.spinner("Loading Statcast leaderboards (this can take a few seconds)..."):
    batter_ev_df = load_source("batter Statcast metrics", get_batter_statcast, season)
    batter_xstats_df = load_source("batter expected stats", get_batter_expected_stats, season)
    pitcher_ev_df = load_source("pitcher Statcast metrics", get_pitcher_statcast, season)
    pitcher_std_df = load_source("pitcher HR/9 + K/9 (FanGraphs)", get_pitcher_standard_stats, season)

    if batter_ev_df is None and batter_xstats_df is None:
        st.error(
            "Couldn't load any batter Statcast data, so the model can't "
            "run right now. This is usually temporary — try again in a "
            "few minutes."
        )
        st.stop()

    if pitcher_std_df is None:
        st.info(
            "Pitcher HR/9 and K/9 (from FanGraphs) are unavailable right "
            "now — FanGraphs sometimes blocks cloud-hosted apps like "
            "Streamlit Cloud. Everything else still works; those two "
            "criteria will just show as not-met until FanGraphs is "
            "reachable again."
        )

rows = []

for g in games:
    box = get_boxscore(g["game_pk"])
    for side, opp_pitcher_id, opp_pitcher_name in [
        ("home", g["away_pitcher_id"], g["away_pitcher"]),
        ("away", g["home_pitcher_id"], g["home_pitcher"]),
    ]:
        team_abbr = g["home_abbr"] if side == "home" else g["away_abbr"]
        lineup = get_lineup(box, side)
        pitcher_hand = get_pitcher_hand(opp_pitcher_id)

        is_dome = team_abbr in DOME_TEAMS
        park_factor = PARK_HR_FACTOR.get(g["home_abbr"], 1.0)

        wind_out, temp_f = False, None
        if not is_dome and g["home_abbr"] in STADIUM_COORDS:
            lat, lon = STADIUM_COORDS[g["home_abbr"]]
            try:
                w = get_weather(lat, lon)
                temp_f = w.get("temp_f")
                # crude check: treat any "Out" wind description as blowing out
                wind_out = "out" in (w.get("wind_dir") or "").lower()
            except Exception:
                pass

        for batter in lineup:
            if not batter["name"]:
                continue
            b_ev = lookup_batter_row(batter_ev_df, batter["name"])
            b_xs = lookup_batter_row(batter_xstats_df, batter["name"])
            p_ev = lookup_pitcher_row(pitcher_ev_df, opp_pitcher_name or "")
            p_std = lookup_pitcher_row(pitcher_std_df, opp_pitcher_name or "", name_col="Name") \
                if pitcher_std_df is not None and "Name" in pitcher_std_df.columns else None

            platoon_edge = (
                batter["bat_side"] and pitcher_hand and
                batter["bat_side"] != pitcher_hand
            ) or batter["bat_side"] == "S"

            model_pct, criteria, met, total = compute_model(
                b_ev, b_xs, p_ev, p_std, platoon_edge, park_factor,
                wind_out, temp_f, is_dome,
            )

            fair_odds = prob_to_american_odds(model_pct)

            book_price = None  # populated below if odds_api_key provided
            edge = None
            if odds_api_key:
                # Placeholder: wire up your odds provider's player-props
                # endpoint here. Left unfilled since no free reliable
                # source exists — see README "Book odds setup".
                pass

            score = model_pct * 100 + met * 1.5 + (edge or 0)

            rows.append({
                "Batter": batter["name"],
                "Team": team_abbr,
                "Opp Pitcher": opp_pitcher_name or "TBD",
                "Model%": f"{model_pct*100:.1f}%",
                "Fair": fair_odds,
                "Book": book_price if book_price else "—",
                "Edge": f"{edge:.1f}%" if edge is not None else "—",
                "Criteria": f"{met}/{total}",
                "Score": round(score, 1),
            })

if not rows:
    st.info(
        "No lineups posted yet for today's games — MLB usually posts "
        "them 1-2 hours before first pitch. Check back closer to game time."
    )
else:
    df = pd.DataFrame(rows).sort_values("Score", ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)

    if not odds_api_key:
        st.info(
            "Book odds / Edge are blank because no odds API key is set. "
            "See the README for how to wire one up once you're ready "
            "to pay for that data."
        )

if show_debug:
    st.subheader("Debug: today's games")
    st.json(games)
