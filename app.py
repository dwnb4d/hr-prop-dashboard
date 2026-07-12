import streamlit as st
from datetime import date
import requests
import pandas as pd

try:
    import pybaseball as pyb
    pyb.cache.enable()
except ImportError:
    pyb = None

st.set_page_config(page_title="MLB HR Model", layout="wide")
st.title("MLB Home Run Model Dashboard")
st.write("Find good home run bets today - Like the example")

date_picked = st.date_input("Pick a day", value=date.today())

# Games
st.subheader("Today's Games")
# (keep your games code here - I omitted for brevity, add back if needed)

st.subheader("Top HR Value Plays")
if pyb:
    try:
        with st.spinner("Loading..."):
            batting = pyb.batting_stats_range(start_dt=(date.today() - pd.Timedelta(days=30)).isoformat())
            
            if not batting.empty:
                df = batting[['Name', 'Team', 'Barrel%', 'HardHit%', 'ISO', 'xSLG', 'maxEV']].copy()
                
                # Simple Model
                df['Model%'] = ((df['Barrel%'] * 0.4) + (df['HardHit%'] * 0.3) + (df['ISO'] * 50) ).clip(upper=0.45)
                df['Score'] = (df['Model%'] * 500).astype(int)
                
                # 12 Criteria (example)
                df['Barrel Check'] = df['Barrel%'] >= 13
                df['HardHit Check'] = df['HardHit%'] >= 50
                df['ISO Check'] = df['ISO'] >= 0.220
                
                sort_by = st.selectbox("Sort by", ["Score", "Model%", "Barrel%"])
                df = df.sort_values(sort_by, ascending=False)
                
                # Nice display
                st.dataframe(
                    df.head(30)[['Name', 'Team', 'Model%', 'Score', 'Barrel%', 'HardHit%', 'ISO', 'Barrel Check', 'HardHit Check', 'ISO Check']],
                    use_container_width=True
                )
    except Exception as e:
        st.error(str(e)[:150])
else:
    st.write("pybaseball not installed")

st.caption("We can make the checkmarks green and add Edge/Book next.")
