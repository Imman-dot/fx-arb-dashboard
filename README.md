# FX Arbitrage Dashboard

A Streamlit-based dashboard for monitoring covered interest parity (CIP) deviations and simulating P&L for FX arbitrage strategies in real time.

## 🚀 Features

- **Live Spot & Forward Rates**: Fetches spot prices from OANDA and simulates forward rates via manual offsets or demo swap-points.
- **Deviation Analysis**: Calculates deviation in basis points between observed and theoretical (CIP) forward rates.
- **Historical Charts**:  
  - Deviation history (last 50 refresh bars)  
  - Observed forward history (last 50 refresh bars)
- **Risk Metrics**:  
  - P&L distribution histograms for each tenor  
  - Equity curve showing cumulative P&L over the dashboard session
- **Summary Metrics**: Total PnL, Win Rate, Max Drawdown, and Current Deviation at a glance.
- **Alerts**: Sends Slack notifications on arbitrage signals exceeding configured thresholds.
- **Auto-Refresh**: Dashboard refreshes data every 5 seconds.

## 📁 Repo Structure

fx-arb-dashboard/
├── app.py                # Main Streamlit dashboard
├── cip.py                # CIP calculation helpers
├── optimize.py           # Parameter sweep backtest script
├── backtest.py           # Historical backtest using swap-points
├── requirements.txt      # Python dependencies
└── .streamlit/
└── config.toml       # Optional Streamlit config (no secrets)
