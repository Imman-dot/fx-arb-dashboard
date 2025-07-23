import os
import itertools
import pandas as pd
import matplotlib.pyplot as plt
import requests
from dateutil import parser
from oandapyV20 import API
from oandapyV20.endpoints.instruments import InstrumentsCandles
from cip import theoretical_forward, deviation_bps

# === Configuration ===
OANDA_TOKEN      = os.getenv("OANDA_TOKEN")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
BASE_URL_SWAP    = "https://api-fxpractice.oanda.com"  # practice swap endpoint

if not OANDA_TOKEN or not OANDA_ACCOUNT_ID:
    raise RuntimeError("Please set OANDA_TOKEN and OANDA_ACCOUNT_ID environment variables")

# Initialize OANDA API client for spot
api = API(access_token=OANDA_TOKEN, environment="practice")

# === Data fetching ===
def fetch_spot_history(pair: str, days: int = 365) -> pd.Series:
    req = InstrumentsCandles(
        instrument=pair,
        params={"granularity": "D", "count": days, "price": "M"}
    )
    data = api.request(req)["candles"]
    records = [(parser.isoparse(c["time"]).date(), (float(c["mid"]["o"]) + float(c["mid"]["c"]))/2)
               for c in data]
    return pd.Series({d: s for d, s in records}).sort_index()


def fetch_swap_history(pair: str, days: int = 365) -> pd.Series:
    url = f"{BASE_URL_SWAP}/v3/accounts/{OANDA_ACCOUNT_ID}/instruments/{pair}/swap_rates"
    headers = {"Authorization": f"Bearer {OANDA_TOKEN}"}
    params = {"count": days, "granularity": "D"}
    try:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json().get("swapRates", [])
        records = []
        for r in data:
            dt = parser.isoparse(r["time"]).date()
            lr = float(r.get("longRate", 0))
            sr = float(r.get("shortRate", 0))
            records.append((dt, lr - sr))
        return pd.Series({d: p for d, p in records}).sort_index()
    except Exception:
        # fallback zeros
        spot = fetch_spot_history(pair, days)
        return pd.Series(0.0, index=spot.index)

# === Backtest using real forward ===
def run_backtest(
    spot: pd.Series,
    swap_pts: pd.Series,
    threshold_bps: float,
    stop_loss_bps: float,
    spread_bps: float,
    tenor_days: int = 30,
    r_dom: float = 0.025,
    r_for: float = 0.005,
    notional: float = 1_000_000
) -> dict:
    df = pd.DataFrame({"spot": spot})
    df["swap_pts"] = swap_pts.reindex(df.index).fillna(method="ffill")
    df["theo_fwd"] = df["spot"].apply(lambda s: theoretical_forward(s, r_dom, r_for, tenor_days))
    df["obs_fwd"] = df["spot"] + df["swap_pts"] * tenor_days / 360
    df["dev_bps"] = (df["obs_fwd"] - df["theo_fwd"]) / df["theo_fwd"] * 10_000
    df["signal"] = 0
    df.loc[df["dev_bps"] >  threshold_bps, "signal"] = -1
    df.loc[df["dev_bps"] < -threshold_bps, "signal"] = +1
    cost = spread_bps / 10_000 * notional
    df["exit_spot"] = df["spot"].shift(-tenor_days)
    df["raw_pnl"] = df["signal"] * (df["exit_spot"] - df["obs_fwd"]) * notional
    df["pnl"] = df["raw_pnl"] - df["signal"].abs() * cost
    stop_amt = stop_loss_bps / 10_000 * notional
    df.loc[df["pnl"] < -stop_amt, "pnl"] = -stop_amt
    trades = df.dropna(subset=["pnl"])
    total_pnl  = trades["pnl"].sum()
    num_trades = (trades["signal"] != 0).sum()
    win_rate   = trades["pnl"].gt(0).mean() * 100 if num_trades else 0
    avg_pnl    = trades["pnl"].mean() if num_trades else 0
    equity     = trades["pnl"].cumsum()
    max_dd     = (equity.cummax() - equity).max() if not equity.empty else 0
    return {"total_pnl": total_pnl,
            "num_trades": num_trades,
            "win_rate": win_rate,
            "avg_pnl": avg_pnl,
            "max_drawdown": max_dd}

# === Optimization sweep ===
if __name__ == "__main__":
    pair = "EUR_USD"
    spot    = fetch_spot_history(pair, days=365)
    swap_pts= fetch_swap_history(pair, days=365)
    thresholds  = [0.5, 1.0, 2.0, 3.0]
    stop_losses = [2.0, 5.0, 10.0]
    spreads     = [0.1, 0.5, 1.0]
    tenor_days  = 30
    results = []
    for th, sl, sp in itertools.product(thresholds, stop_losses, spreads):
        m = run_backtest(spot, swap_pts, th, sl, sp, tenor_days)
        results.append({"threshold_bps": th,
                        "stop_loss_bps": sl,
                        "spread_bps": sp,
                        **m})
    df = pd.DataFrame(results)
    df.to_csv("optimization_results_real.csv", index=False)
    top = df.sort_values("total_pnl", ascending=False).head(10)
    print("Top 10 real-forward parameter sets:")
    print(top.to_string(index=False))

