def pnl_path(spot_series, obs_forward, notional=1_000_000):
    """
    Given a time series of spot prices (list of floats) and a 
    locked-in forward price (obs_forward), returns a list of 
    PnL values under a +1 lot trade.
    PnL_t = notional * (spot_t - obs_forward)
    """
    return [notional * (s - obs_forward) for s in spot_series]

import random
# e.g. 10 days of spot returns ±0.5%
base = 1.16987
path = []
for _ in range(10):
    shock = random.uniform(-0.005, 0.005)
    base = base * (1 + shock)
    path.append(round(base, 6))

from risk import pnl_path

# assume obs_forward from your engine, e.g. 1.17105
obs_forward = 1.17105  
pnls = pnl_path(path, obs_forward)
print("Day-by-day PnL:", pnls)

import numpy as np

# compute daily PnL changes
diffs = np.diff(pnls)
# find the 5th percentile loss
var95 = -np.percentile(diffs, 5)
print(f"1-day 95% VaR: ${var95:,.2f}")
