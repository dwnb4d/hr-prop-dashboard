import streamlit as st
import pandas as pd
import random
from datetime import date, datetime

st.set_page_config(page_title="MLB HR Dashboard", layout="wide")
st.title("⚾ MLB HR Dashboard")
st.caption("Prototype — full model inputs can be wired in later. All values are mock/demo when real data unavailable.")

# Helper functions
def safe_numeric(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def format_american_odds(odds):
    o = safe_numeric(odds)
    return f"+{int(o)}" if o > 0 else str(int(o))

def implied_prob(odds):
    o = safe_numeric(odds)
    return abs(o) / (abs(o) + 100) if o != 0 else 0.5

def fair_odds(prob):
    p = max(min(safe_numeric(prob, 0.5), 0.99), 0.01)
    return int(round((1 - p) / p * 100)) if p < 0.5 else -int(round(p / (1 - p) * 100))

def assign_tier(score):
    s = safe_numeric(score)
    if s >= 85: return "Elite"
    if s >= 70: return "Strong"
    if s >= 55: return "Value"
    return "Speculative"

def build_hr_summary(player, edge, criteria_met):
    reasons = []
    if edge > 8: reasons.append("high edge vs book")
    if criteria_met > 7: reasons.append(f"meets {criteria_met}/12 thresholds")
    if "Elite" in assign_tier(edge * 0.8 + criteria_met * 2):
        reasons.append("elite profile")
    return "; ".join(reasons) or "solid matchup profile"

THRESHOLDS = ["ISO>0.22", "HR/FB>18%", "HardHit%>48%", "Barrel%>10%", "PullAir%>28%",
              "vsRHP HR rate", "Park factor>1.05", "Recent form", "Opp pitcher HR/9>1.3",
              "Temp>75F", "Wind>10mph out", "Rest advantage"]

def evaluate_criteria(row):
    met = random.randint(5, 11)  # demo
    return met, [t for t in THRESHOLDS[:met]]

# Sidebar controls
selected_date = st.sidebar.date_input("Slate Date", value=date.today())
st.sidebar.write(f"Slate driven by: {selected_date}")

# Games section (robust)
st.header("Today's Games")
try:
    games = pd.DataFrame({
        "Matchup": ["NYY @ BOS", "LAD @ SF", "CHC @ STL"],
        "Time": ["7:10 PM", "9:45 PM", "8:15 PM"],
        "Weather": ["72F, calm", "68F, 12mph out", "78F, indoors"]
    })
    st.dataframe(games, use_container_width=True)
except Exception as e:
    st.error(f"Games load error: {e}")

# Player data (mock with fallbacks)
st.header("Featured Top Plays")
random.seed(int(selected_date.strftime("%Y%m%d")))
players = [
    {"name": "Aaron Judge", "score": 91, "model_prob": 0.31, "book_odds": 185, "criteria_met": 9},
    {"name": "Shohei Ohtani", "score": 84, "model_prob": 0.27, "book_odds": 210, "criteria_met": 8},
    {"name": "Matt Olson", "score": 78, "model_prob": 0.24, "book_odds": 245, "criteria_met": 7},
    {"name": "Pete Alonso", "score": 73, "model_prob": 0.22, "book_odds": 265, "criteria_met": 6},
]

cols = st.columns(4)
for i, p in enumerate(players[:4]):
    tier = assign_tier(p["score"])
    edge = round((p["model_prob"] - implied_prob(p["book_odds"])) * 100, 1)
    fair = fair_odds(p["model_prob"])
    summary = build_hr_summary(p["name"], edge, p["criteria_met"])
    with cols[i]:
        st.markdown(f"### {p['name']}")
        st.markdown(f"**Tier:** {tier}  |  **Score:** {p['score']}")
        st.write(f"Model Prob: {p['model_prob']*100:.0f}% | Book: {format_american_odds(p['book_odds'])}")
        st.write(f"Fair Odds: {format_american_odds(fair)} | Edge: {edge}%")
        st.caption(summary)
        with st.expander("Criteria"):
            met, checklist = evaluate_criteria(p)
            st.write(f"{met}/12 thresholds met")
            st.write(", ".join(checklist))

# Full sortable table
st.subheader("Full Player Table")
df = pd.DataFrame(players)
df["tier"] = df["score"].apply(assign_tier)
df["edge"] = df.apply(lambda r: round((r.model_prob - implied_prob(r.book_odds)) * 100, 1), axis=1)
st.dataframe(df.sort_values("score", ascending=False), use_container_width=True)

st.write("Data simulated for demo purposes. Connect real pybaseball / odds feeds for production.")
