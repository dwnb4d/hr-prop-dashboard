# Power Stats section
st.subheader("Home Run Candidates")
if pyb:
    try:
        with st.spinner("Loading power stats..."):
            end = date.today()
            start = end - pd.Timedelta(days=30)
            df = pyb.statcast(start_dt=start.isoformat(), end_dt=end.isoformat())
            
            if not df.empty:
                # Use correct column names from Statcast
                player_stats = df.groupby('player_name').agg({
                    'barrel': 'mean',           # this is the rate
                    'launch_speed': 'max',      # Max EV
                    'events': 'count'
                }).reset_index()
                
                player_stats.rename(columns={
                    'player_name': 'Name',
                    'barrel': 'Barrel%',
                    'launch_speed': 'Max EV'
                }, inplace=True)
                
                player_stats['Model%'] = (player_stats['Barrel%'] * 2.5).clip(upper=0.45)
                player_stats = player_stats.sort_values('Model%', ascending=False).head(20)
                
                st.dataframe(player_stats[['Name', 'Barrel%', 'Max EV', 'Model%']])
            else:
                st.write("No recent Statcast data yet.")
    except Exception as e:
        st.error("Statcast issue")
        st.write(str(e)[:200])
else:
    st.write("pybaseball not installed")
