import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
from dateutil import parser
from oandapyV20 import API
from oandapyV20.endpoints.instruments import InstrumentsCandles
from cip import theoretical_forward, deviation_bps

# === Configuration ===
OANDA_TOKEN      = os.getenv("OANDA_TOKEN")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
BASE_URL         = "https://api-fxtrade.oanda.com"  # production for swap rates

if not OANDA_TOKEN or not OANDA_ACCOUNT_ID:
    raise RuntimeError("Please set OANDA_TOKEN and OANDA_ACCOUNT_ID environment variables")

# Initialize OANDA API client (practice for spot data)
api = API(access_token=OANDA_TOKEN, environment="practice")

# === Data Fetching ===

def fetch_spot_history(pair: str, days: int = 365) -> pd.Series:
    """
    Fetch daily historical spot mid-prices for the FX pair.
    Returns a pandas Series indexed by date.
    """
    req = InstrumentsCandles(
        instrument=pair,
        params={"granularity": "D", "count": days, "price": "M"}
    )
    data = api.request(req)["candles"]
    records = []
    for c in data:
        dt = parser.isoparse(c["time"])  # full timestamp
        o = float(c["mid"]["o"])
        c_ = float(c["mid"]["c"])
        records.append((dt.date(), (o + c_) / 2))
    series = pd.Series({d: s for d, s in records}).sort_index()
    return series


def fetch_swap_history(pair: str, days: int = 365) -> pd.Series:
    """
    Fetch daily historical swap-rates (forward-points) for the FX pair.
    Returns a pandas Series of daily forward-points (decimal) indexed by date.
    Falls back to zeros if endpoint unavailable (e.g., practice account).
    """
    url = f"{BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/instruments/{pair}/swap_rates"
    headers = {"Authorization": f"Bearer {OANDA_TOKEN}"}
    params = {"count": days, "granularity": "D"}
    try:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json().get("swapRates", [])
        records = []
        for r in data:
            dt = parser.isoparse(r["time"]).date()
            long_rate = float(r.get("longRate", 0))
            short_rate = float(r.get("shortRate", 0))
            records.append((dt, long_rate - short_rate))
        series = pd.Series({d: p for d, p in records}).sort_index()
    except Exception:
        # Practice environment may not support swap_rates; fallback to zeros
        print("Warning: swap_rates endpoint unavailable, falling back to zeros.")
        # Build zero series over requested date range
        df_spot = fetch_spot_history(pair, days=days)
        series = pd.Series(0.0, index=df_spot.index)
    return series

# === Backtest ===

def backtest(
    pair: str,
    tenor_days: int = 30,
    r_dom: float = 0.025,
    r_for: float = 0.005,
    notional: float = 1_000_000,
    spread_bps: float = 0.5,
    stop_loss_bps: float = 5.0,
    history_days: int = 365
) -> None:
    """
    Back-test FX CIP arbitrage using real swap-points.
    """
    # Fetch data
    spot = fetch_spot_history(pair, days=history_days)
    swap_pts = fetch_swap_history(pair, days=history_days)

    # Build DataFrame
    df = pd.DataFrame({"spot": spot})
    # theoretical forward
    df["theo_fwd"] = df["spot"].apply(lambda s: theoretical_forward(s, r_dom, r_for, tenor_days))
    # observed forward = spot + tenor * swap_pts/360
    df["swap_pts"] = swap_pts.reindex(df.index).fillna(method="ffill")
    df["obs_fwd"] = df["spot"] + df["swap_pts"] * tenor_days / 360

    # deviation and signal
    df["dev_bps"] = (df["obs_fwd"] - df["theo_fwd"]) / df["theo_fwd"] * 10_000
    df["signal"] = 0
    df.loc[df["dev_bps"] > 0, "signal"] = -1  # sell forward if rich
    df.loc[df["dev_bps"] < 0, "signal"] = +1  # buy forward if cheap

    # PnL with spread cost & stop-loss
    cost = spread_bps / 10_000 * notional
    df["exit_spot"] = df["spot"].shift(-tenor_days)
    df["raw_pnl"] = df["signal"] * (df["exit_spot"] - df["obs_fwd"]) * notional
    df["pnl"] = df["raw_pnl"] - df["signal"].abs() * cost
    stop_amt = stop_loss_bps / 10_000 * notional
    df.loc[df["pnl"] < -stop_amt, "pnl"] = -stop_amt

    # drop incomplete
    trades = df.dropna(subset=["pnl"])

    # metrics
    total_pnl    = trades["pnl"].sum()
    num_trades   = (trades["signal"] != 0).sum()
    win_rate     = trades["pnl"].gt(0).mean() * 100 if num_trades else 0
    avg_pnl      = trades["pnl"].mean() if num_trades else 0
    equity = trades["pnl"].cumsum()
    max_dd = (equity.cummax() - equity).max() if not equity.empty else 0

    # output
    print(f"=== Backtest Results for {pair} ({tenor_days}d tenor) ===")
    print(f"Total PnL            : ${total_pnl:,.0f}")
    print(f"Number of trades     : {num_trades}")
    print(f"Win rate             : {win_rate:.1f}%")
    print(f"Average PnL/trade    : ${avg_pnl:,.0f}")
    print(f"Max Drawdown         : ${max_dd:,.0f}")

    # plot equity
    plt.figure(figsize=(10, 4))
    plt.plot(equity.index, equity.values)
    plt.title(f"Equity Curve ({pair}, {tenor_days}d)")
    plt.xlabel("Date")
    plt.ylabel("Cumulative PnL ($)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# === Main ===
if __name__ == "__main__":
    backtest("EUR_USD")

