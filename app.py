import os
import requests
import random
import streamlit as st
import numpy as np
import pandas as pd
from dateutil import parser
from oandapyV20 import API
from oandapyV20.endpoints.pricing import PricingInfo
from cip import theoretical_forward, deviation_bps
from streamlit_autorefresh import st_autorefresh

# Auto-refresh every 5 seconds
st_autorefresh(interval=5_000, key="refresh")

# Page configuration
st.set_page_config(page_title="FX Arbitrage Dashboard", layout="wide")

# --- Credentials via Streamlit secrets & Endpoints ---
# Create a file at ~/.streamlit/secrets.toml (or ./fx_arbitrage/.streamlit/secrets.toml) with:
#
# [oanda]
# token      = "<YOUR_OANDA_TOKEN>"
# account_id = "<YOUR_OANDA_ACCOUNT_ID>"
#
# [slack]
# webhook = "<YOUR_SLACK_WEBHOOK_URL>"
#
# Streamlit will auto-load this file into st.secrets
OANDA_TOKEN      = st.secrets["oanda"]["token"]
OANDA_ACCOUNT_ID = st.secrets["oanda"]["account_id"]
SLACK_WEBHOOK    = st.secrets.get("slack", {}).get("webhook", "")
PRACTICE_SWAP_API = "https://api-fxpractice.oanda.com"

# Initialize OANDA client for spot data
client = API(access_token=OANDA_TOKEN, environment="practice")

# --- Sidebar controls ---
st.sidebar.header("Settings")
override_provider = st.sidebar.selectbox(
    "Forward-Rate Provider", ["Manual", "Swap-Points"]
)
manual_bps = st.sidebar.slider(
    "Manual forward offset (bps)", -10.0, 10.0, 0.0, step=0.1
)
threshold_bps = st.sidebar.number_input(
    "Deviation threshold (bps)", 0.5, 10.0, 1.0, step=0.5
)
stop_loss_bps = st.sidebar.number_input(
    "Stop-loss threshold (bps)", 0.0, 20.0, 2.0, step=0.5
)
spread_bps = st.sidebar.number_input(
    "Spread cost per trade (bps)", 0.0, 5.0, 0.1, step=0.1
)
tenor_days = st.sidebar.number_input(
    "Tenor days", 1, 90, 30
)
pairs = st.sidebar.multiselect(
    "Currency pairs", ["EUR_USD", "GBP_USD", "USD_JPY"], default=["EUR_USD", "GBP_USD", "USD_JPY"]
)

# Initialize histories
if 'history' not in st.session_state:
    st.session_state.history = {pair: [] for pair in pairs}
if 'fwd_history' not in st.session_state:
    st.session_state.fwd_history = {pair: [] for pair in pairs}

# --- Utility functions ---
def fetch_spot(pair):
    pricing = client.request(
        PricingInfo(accountID=OANDA_ACCOUNT_ID, params={"instruments": pair})
    )
    bid = float(pricing["prices"][0]["bids"][0]["price"])
    ask = float(pricing["prices"][0]["asks"][0]["price"])
    return (bid + ask) / 2


def fetch_swap_point(pair):
    """Fetch the daily swap-point for the given tenor."""
    url = f"{PRACTICE_SWAP_API}/v3/accounts/{OANDA_ACCOUNT_ID}/instruments/{pair}/swap_rates"
    headers = {"Authorization": f"Bearer {OANDA_TOKEN}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return 0.0
    for r in resp.json().get("swapRates", []):
        if r.get('tenor').endswith('D') and int(r.get('tenor')[:-1]) == tenor_days:
            lr = float(r.get("longRate", 0))
            sr = float(r.get("shortRate", 0))
            return lr - sr
    return 0.0


def simulate_pnl(spot0, obs_fwd, days, sims=500):
    pnls = []
    for _ in range(sims):
        path = spot0
        daily = []
        for _ in range(days):
            shock = random.uniform(-0.005, 0.005)
            path *= (1 + shock)
            daily.append(1e6 * (path - obs_fwd))
        pnls.append(daily)
    return np.array(pnls)

# --- Data collection & metrics ---
data_rows = []
for pair in pairs:
    spot_mid = fetch_spot(pair)

    # Determine observed forward
    if override_provider == "Manual":
        theo_fwd = theoretical_forward(spot_mid, 0.025, 0.005, tenor_days)
        obs_fwd = theo_fwd * (1 + manual_bps / 10_000)
    else:
        swap_pts = fetch_swap_point(pair)
        obs_fwd = spot_mid + swap_pts * tenor_days / 360
        theo_fwd = theoretical_forward(spot_mid, 0.025, 0.005, tenor_days)

    dev_bps = deviation_bps(obs_fwd, theo_fwd)

    # update histories
    hist = st.session_state.history[pair]
    hist.append(dev_bps)
    if len(hist) > 50:
        hist.pop(0)
    st.session_state.history[pair] = hist

    fh = st.session_state.fwd_history[pair]
    fh.append(obs_fwd)
    if len(fh) > 50:
        fh.pop(0)
    st.session_state.fwd_history[pair] = fh

    # signal
    if dev_bps > threshold_bps:
        sig = "Rich → Sell forward"
    elif dev_bps < -threshold_bps:
        sig = "Cheap → Buy forward"
    else:
        sig = "No arbitrage"

    # PnL calculation
    cost = spread_bps / 10_000 * 1_000_000
    raw_pnl = (obs_fwd - theo_fwd) * 1_000_000
    pnl = raw_pnl - cost
    stop_amt = stop_loss_bps / 10_000 * 1_000_000
    if pnl < -stop_amt:
        pnl = -stop_amt

    data_rows.append({
        "Pair":             pair,
        "Spot Mid":         f"{spot_mid:.6f}",
        "Observed Forward": f"{obs_fwd:.6f}",
        "Theoretical Fwd":  f"{theo_fwd:.6f}",
        "Deviation (bps)":  f"{dev_bps:+.2f}",
        "Signal":           sig,
        "PnL ($)":          f"{pnl:,.0f}"
    })

    if SLACK_WEBHOOK and sig != "No arbitrage":
        requests.post(SLACK_WEBHOOK, json={"text": f"Arb alert: {pair} {dev_bps:+.2f}bps → {sig}"})

# --- Summary Metrics ---
col1, col2, col3, col4 = st.columns(4)
# parse PnL values from data_rows
pnls = [float(r["PnL ($)"].replace("$","").replace(",","") ) for r in data_rows]
total_pnl = sum(pnls)
win_rate  = np.mean([1 if v>0 else 0 for v in pnls]) * 100
max_dd     = min(pnls)
current_dev= data_rows[0]["Deviation (bps)"]
col1.metric("Total PnL", f"${total_pnl:,.0f}")
col2.metric("Win Rate", f"{win_rate:.1f}%")
col3.metric("Max Drawdown", f"${max_dd:,.0f}")
col4.metric("Current Dev", f"{current_dev} bps")

# --- Display dashboard ---
st.title("FX Arbitrage Dashboard — Live")
st.dataframe(pd.DataFrame(data_rows), use_container_width=True)
st.markdown("**Auto-refreshes every 5s**")

# Deviation & Forward History
st.subheader("Deviation History (bps)")
for pair in pairs:
    st.line_chart(pd.DataFrame({pair: st.session_state.history[pair]}))

st.subheader("Observed Forward History")
for pair in pairs:
    st.line_chart(pd.DataFrame({pair: st.session_state.fwd_history[pair]}))

# PnL Distribution
st.subheader(f"PnL Distribution at Day {tenor_days}")
for pair in pairs:
    spot_mid = fetch_spot(pair)
    if override_provider == "Manual":
        theo_fwd = theoretical_forward(spot_mid, 0.025, 0.005, tenor_days)
        obs_fwd = theo_fwd * (1 + manual_bps / 10_000)
    else:
        swap_pts = fetch_swap_point(pair)
        obs_fwd = spot_mid + swap_pts * tenor_days / 360
    sims = simulate_pnl(spot_mid, obs_fwd, tenor_days, sims=1000)
    st.write(f"{pair} PnL Histogram")
    st.bar_chart(pd.Series(sims[:, -1], name=pair))

# --- Equity Curve ---
st.subheader("Equity Curve (last 50 bars)")
for pair in pairs:
    # compute per-bar PnL from history and forward history
    pnl_series = []
    for obs, dev in zip(st.session_state.fwd_history[pair], st.session_state.history[pair]):
        spot_val = fetch_spot(pair)
        theo_val = theoretical_forward(spot_val, 0.025, 0.005, tenor_days)
        raw = (obs - theo_val) * 1_000_000
        cost = spread_bps/10_000 * 1_000_000
        pnl_val = raw - cost
        stop_amt = stop_loss_bps/10_000 * 1_000_000
        pnl_series.append(max(pnl_val, -stop_amt))
    equity = np.cumsum(pnl_series)
    st.line_chart(pd.DataFrame({pair: equity}))


