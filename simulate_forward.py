# simulate_forward.py

import random
from cip import theoretical_forward, deviation_bps

# === Simulation parameters ===
spot_mid      = 1.16987    # last known spot mid
r_domestic    = 0.025      # e.g. USD OIS annual rate
r_foreign     = 0.005      # e.g. EUR OIS annual rate
days          = 30         # tenor in days for 1M
threshold_bps = 2.0        # alert threshold in bps

# 1) Compute the “fair” 1M forward via CIP
theo_fwd = theoretical_forward(spot_mid, r_domestic, r_foreign, days)
print(f"Theoretical 1M forward: {theo_fwd:.6f}\n")

# 2) Run 10 simulated “observed” forwards with noise ±5 bps
for i in range(1, 11):
    noise_bps = random.uniform(-5, 5)
    obs_fwd   = theo_fwd * (1 + noise_bps / 10_000)
    dev       = deviation_bps(obs_fwd, theo_fwd)

    # 3) Determine if it breaches your threshold
    signal = ""
    if abs(dev) > threshold_bps:
        direction = "Sell forward / Buy spot" if dev > 0 else "Buy forward / Sell spot"
        signal = f" ⚠️ ARB SIGNAL: {dev:.2f} bps → {direction}"

    # 4) Print the result for this trial
    print(
        f"Sim #{i:2d}: noise={noise_bps:+.2f} bps → "
        f"observed={obs_fwd:.6f} → dev={dev:+.2f} bps{signal}"
    )
