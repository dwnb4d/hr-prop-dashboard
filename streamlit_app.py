import streamlit as st
import pandas as pd

st.set_page_config(page_title="HR Prop Dashboard", layout="wide")

st.title("HR Prop Dashboard")
st.write("Model probability, fair odds, book odds, edge, score, and criteria checks.")

data = [
    {
        "Player": "Example Batter",
        "Team": "SD",
        "Opponent": "LAD",
        "Hand": "R",
        "Pitcher Hand": "L",
        "Model%": 0.18,
        "Book Odds": +450,
        "Barrel%": 14,
        "Hard-Hit%": 52,
        "ISO": 0.238,
        "xSLG": 0.552,
        "Max EV": 113,
        "Pitcher HR/9": 1.22,
        "Pitcher Barrel% Allowed": 10.8,
        "Pitcher Hard-Hit% Allowed": 46.3,
        "Park HR Factor": 1.08,
        "Wind Out": True,
        "Temp": 81,
        "Dome": False,
    },
    {
        "Player": "Sample Slugger",
        "Team": "LAD",
        "Opponent": "SD",
        "Hand": "L",
        "Pitcher Hand": "R",
        "Model%": 0.24,
        "Book Odds": +320,
        "Barrel%": 16,
        "Hard-Hit%": 55,
        "ISO": 0.265,
        "xSLG": 0.590,
        "Max EV": 116,
        "Pitcher HR/9": 1.35,
        "Pitcher Barrel% Allowed": 11.4,
        "Pitcher Hard-Hit% Allowed": 48.2,
        "Park HR Factor": 1.11,
        "Wind Out": True,
        "Temp": 84,
        "Dome": False,
    },
]

df = pd.DataFrame(data)

def prob_to_american_odds(p):
    if p <= 0 or p >= 1:
        return None
    if p >= 0.5:
        return -round(100 * p / (1 - p))
    return round(100 * (1 - p) / p)

def american_to_prob(odds):
    if odds > 0:
        return 100 / (odds + 100)
    return -odds / (-odds + 100)

def calc_edge(model_prob, book_odds):
    return model_prob - american_to_prob(book_odds)

def calc_score(model_prob, edge, checkmarks):
    return round((50 * model_prob) + (300 * edge) + (2 * checkmarks), 2)

def criteria_row(r):
    c = {
        "Barrel% ≥ 13": r["Barrel%"] >= 13,
        "Hard-Hit% ≥ 50": r["Hard-Hit%"] >= 50,
        "ISO ≥ .220": r["ISO"] >= 0.220,
        "xSLG ≥ .500": r["xSLG"] >= 0.500,
        "Max EV ≥ 110": r["Max EV"] >= 110,
        "Platoon edge": (r["Hand"] == "L" and r["Pitcher Hand"] == "R") or (r["Hand"] == "R" and r["Pitcher Hand"] == "L"),
        "Pitcher HR/9 ≥ 1.10": r["Pitcher HR/9"] >= 1.10,
        "Barrel% allowed ≥ 10": r["Pitcher Barrel% Allowed"] >= 10,
        "Hard-Hit% allowed ≥ 45": r["Pitcher Hard-Hit% Allowed"] >= 45,
        "HR-friendly park": r["Park HR Factor"] >= 1.05,
        "Wind blowing out": True if r["Dome"] else r["Wind Out"],
        "Warm ≥ 78°F": True if r["Dome"] else r["Temp"] >= 78,
    }
    return c

criteria_data = df.apply(criteria_row, axis=1)
criteria_df = pd.DataFrame(criteria_data.tolist())

df["Checkmarks"] = criteria_df.sum(axis=1)
df["Fair Odds"] = df["Model%"].apply(prob_to_american_odds)
df["Edge"] = df.apply(lambda r: round(calc_edge(r["Model%"], r["Book Odds"]), 4), axis=1)
df["Score"] = df.apply(lambda r: calc_score(r["Model%"], r["Edge"], r["Checkmarks"]), axis=1)

st.sidebar.header("Filters")
min_edge = st.sidebar.slider("Minimum Edge", 0.0, 0.2, 0.0, 0.01)
min_score = st.sidebar.slider("Minimum Score", 0.0, 30.0, 0.0, 0.5)
team_filter = st.sidebar.multiselect("Team", sorted(df["Team"].unique()), default=sorted(df["Team"].unique()))

filtered = df[
    (df["Edge"] >= min_edge) &
    (df["Score"] >= min_score) &
    (df["Team"].isin(team_filter))
].copy()

st.subheader("Ranked Plays")
st.dataframe(
    filtered.sort_values("Score", ascending=False)[
        ["Player", "Team", "Opponent", "Model%", "Fair Odds", "Book Odds", "Edge", "Score", "Checkmarks"]
    ],
    use_container_width=True
)

st.subheader("Criteria Breakdown")
st.dataframe(criteria_df, use_container_width=True)
