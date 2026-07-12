import streamlit as st
import pandas as pd

st.set_page_config(page_title="HR Prop Dashboard", layout="wide")
st.title("HR Prop Dashboard")
st.write("Upload a CSV to calculate fair odds, edge, and score.")

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

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    required_cols = ["Model%", "Book Odds", "Checkmarks"]
    missing = [c for c in required_cols if c not in df.columns]

    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
    else:
        df["Fair Odds"] = df["Model%"].apply(prob_to_american_odds)
        df["Edge"] = df.apply(lambda r: round(calc_edge(r["Model%"], r["Book Odds"]), 4), axis=1)
        df["Score"] = df.apply(lambda r: calc_score(r["Model%"], r["Edge"], r["Checkmarks"]), axis=1)

        st.subheader("Ranked Plays")
        st.dataframe(df.sort_values("Score", ascending=False), use_container_width=True)
else:
    st.info("Upload a CSV file to begin.")
