# FX Arbitrage Dashboard ⚖️

Real‑time FX CIP arbitrage signals with PnL simulation, equity curve, and Slack alerts.

## Key features

* **Live Data**: Fetches FX spot prices from OANDA practice API every 5 seconds
* **Forward Calculation**: Supports manual forward‑rate offsets or practice‑mode swap‑points
* **CIP Deviation**: Computes basis‑point deviation between observed and theoretical forward rates
* **Interactive Metrics**: On‑screen summary cards (Total PnL, Win Rate, Max Drawdown, Current Dev)
* **Visualizations**:

  * Deviation & Observed Forward history charts
  * PnL distribution histograms
  * Equity curve over the last 50 bars
* **Alerts**: Sends Slack notifications when deviation exceeds your threshold
* **Auto‑refresh**: Dashboard refreshes every 5 seconds for near‑live monitoring

## Overview

This Streamlit app provides a live dashboard for monitoring Covered Interest Parity (CIP) arbitrage opportunities in the FX market. It pulls spot prices from OANDA, applies either manual offsets or swap‑point data to generate observed forward rates, and calculates the deviation from the theoretical forward implied by interest‑rate differentials. Users can simulate PnL paths, view summary metrics, and receive Slack alerts when the deviation signal indicates a buy or sell opportunity.

## Why I Built This

I wanted to explore how CIP deviations can reveal risk‑free arbitrage opportunities between FX spot and forward markets. Building this dashboard helped me practice real‑time data integration, interactive UI development with Streamlit, and automated alerting—key skills for quantitative trading and fintech engineering.

## Problem Statement & Business Context

**Covered Interest Parity** states that the forward FX rate should offset interest‑rate differentials between two currencies. When markets deviate, banks and hedge funds can lock in arbitrage profits by simultaneously borrowing, converting, and hedging FX exposures. Detecting these fleeting mispricings in real time is valuable for high‑frequency traders, corporate treasuries, and quantitative researchers.

## Data & Tools Used

* **Data Sources**: OANDA practice API for spot rates; manual-bps slider or practice swap‑points for forwards
* **Languages & Frameworks**: Python, Streamlit
* **Libraries**:

  * `oandapyV20` for OANDA REST calls
  * `pandas`, `numpy` for data processing
  * `matplotlib` (via Streamlit) for charts
  * `streamlit_autorefresh` for auto‑reload
* **Alerting**: Slack webhook integration

## Methodology

1. **Spot & Forward Retrieval**:

   * **Manual offset**:
     `F_obs = F_theo * (1 + offset_bps/10000)`
   * **Swap-points fallback**:
     `F_obs = spot + swap_pts * tenor_days/360`
2. **Theoretical Forward** (Covered Interest Parity):
   `F_theo = spot * (1 + r_dom * T) / (1 + r_for * T)`
   *where* `T = tenor_days/360`
3. **Deviation** (in basis points):
   `dev_bps = (F_obs - F_theo)/F_theo * 10000`
4. **Signal Generation**:

   * If `dev_bps > threshold` → Sell forward
   * If `dev_bps < -threshold` → Buy forward
   * Otherwise → No arbitrage
5. **Risk Simulation**:

   * Simulate *N* spot paths with white-noise shocks
   * Compute PnL per path: `(S_T - F_obs) * notional - cost`, apply stop-loss cap
6. **Back-testing & Optimization**:

   * Parameter sweep on threshold, offset, spread, stop-loss
   * Evaluate Total PnL, Win Rate, Average PnL, Max Drawdown to pick optimal settings

## Results & Demo

* **Optimized back‑test** (30‑day tenor, 1 bp threshold, 2 bp stop‑loss, 0.1 bp spread):

  * Total PnL: **\$5,153,890**
  * Win Rate: **57.6 %**
  * Max Drawdown: **\$18,295**
* **Live dashboard**: see real‑time deviation, forward history, PnL distributions, equity curve, and Slack alerts.

## Key Challenges & Solutions

* **API Errors & Secret Management**: Learned to debug HTTP JSON errors and securely store credentials via Streamlit secrets or environment variables.
* **Streamlit State & Auto‑refresh**: Managing session state for time‑series history required careful use of `st.session_state` and `st_autorefresh`.
* **Debugging Complex Data Flows**: Overcame intermittent data errors by inserting smoke‑test banners and raw response dumps for rapid troubleshooting.

## Takeaways

* Sharpened Python debugging and attention to detail when integrating multiple APIs.
* Gained hands‑on experience with real‑time UI development using Streamlit.
* Developed a deep understanding of CIP arbitrage mechanics and PnL simulation.
* Improved best practices around secrets management and automated alerting workflows.

## Future Improvements

* **Reduce AI dependency**: rewrite key modules without AI assistance to strengthen core skills.
* **Real swap‑points**: upgrade to a funded OANDA account or integrate a paid forward‑rate API for genuine forward data.
* **Expand tenor & pairs**: support 7‑day, 90‑day forwards and additional FX crosses (AUD/USD, USD/CAD).
* **Cloud deployment**: containerize and host on Streamlit Cloud for 24/7 monitoring with built‑in uptime alerts.


