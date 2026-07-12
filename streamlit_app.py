import streamlit as st
import pandas as pd

st.set_page_config(page_title="HR Prop Dashboard", layout="wide")
st.title("HR Prop Dashboard")

st.write("Upload a CSV with batter/game data to calculate fair odds, edge, and score.")

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

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

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    if "Model%" in df.columns and "Book Odds" in df.columns and "Checkmarks" in df.columns:
        df["Fair Odds"] = df["Model%"].apply(prob_to_american_odds)
        df["Edge"] = df.apply(lambda r: round(calc_edge(r["Model%"], r["Book Odds"]), 4), axis=1)
        df["Score"] = df.apply(lambda r: calc_score(r["Model%"], r["Edge"], r["Checkmarks"]), axis=1)

        st.subheader("Ranked Plays")
        st.dataframe(df.sort_values("Score", ascending=False), use_container_width=True)
    else:
        st.error("CSV must include columns: Model%, Book Odds, Checkmarks")
else:
    st.info("Upload a CSV to get started.")
