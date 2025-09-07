# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from nifty_agent import NiftyInvestmentAgent

st.set_page_config(page_title="Nifty 50 Investment Agent", layout="wide")

st.title("Nifty 50 Investment Agent")
st.markdown("Automated investing in ICICINIFTY50 based on market conditions")

agent = NiftyInvestmentAgent()

# Sidebar for controls
st.sidebar.header("Controls")
if st.sidebar.button("Check Market Now"):
    with st.spinner("Checking market conditions..."):
        result = agent.daily_check()
        if result['action_taken']:
            st.sidebar.success("Investment executed!")
        else:
            st.sidebar.info("No action taken")

# Display current state
col1, col2 = st.columns(2)

with col1:
    st.subheader("Investment Status")
    if agent.state['last_investment_date']:
        st.metric("Last Investment", agent.state['last_investment_date'])
        st.metric("Days Since Last Investment", 
                 agent.state['trading_days_since_last_investment'])
    else:
        st.info("No investments recorded yet")

with col2:
    st.subheader("Current Triggers")
    market_data = agent.fetch_market_data()
    triggers = agent.check_triggers(market_data)
    
    if triggers:
        for trigger in triggers:
            st.warning(f"⚠️ {trigger['type']}: {trigger['message']}")
    else:
        st.success("No active triggers")

# Market data visualization
st.subheader("Market Data")
df = pd.DataFrame([market_data])
st.dataframe(df)

# Investment history
st.subheader("Investment History")
if agent.state['investment_history']:
    history_df = pd.DataFrame(agent.state['investment_history'])
    st.dataframe(history_df)
    
    # Visualize investment timing
    fig = px.scatter(history_df, x='date', y='trigger', color='trigger',
                    title="Investment History by Trigger Type")
    st.plotly_chart(fig)
else:
    st.info("No investment history available")

# Instructions
st.sidebar.header("About")
st.sidebar.info("""
This agent automatically invests in ICICINIFTY50 when:
1. Nifty 50 closes ≥2.5% below its 20-Day SMA
2. India VIX closes above 22
3. 20 trading days have passed since last investment

Checks occur daily at 3:00 PM IST.
""")