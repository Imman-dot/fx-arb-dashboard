import warnings
from urllib3.exceptions import NotOpenSSLWarning

# Silence the LibreSSL/OpenSSL warning
warnings.filterwarnings("ignore", category=NotOpenSSLWarning)

import os
import json
import requests
from oandapyV20 import API
from oandapyV20.endpoints.pricing import PricingInfo
from cip import theoretical_forward, deviation_bps

# 1. Read credentials from environment variables
#    Ensure OANDA_TOKEN and OANDA_ACCOUNT_ID are exported in the same shell
token = os.getenv("OANDA_TOKEN")
account_id = os.getenv("OANDA_ACCOUNT_ID")

# Debug: verify credentials are loaded (remove after confirming)
print("DEBUG: token →", token)
print("DEBUG: account_id →", account_id)

# 2. Initialize OANDA client (practice environment)
client = API(access_token=token, environment="practice")

# 3. Fetch spot pricing for EUR/USD
pricing_req = PricingInfo(accountID=account_id, params={"instruments": "EUR_USD"})
pricing_resp = client.request(pricing_req)
print("\nSPOT PRICING:")
print(json.dumps(pricing_resp, indent=2))

# 4. Compute spot mid price
bid = float(pricing_resp["prices"][0]["bids"][0]["price"])
ask = float(pricing_resp["prices"][0]["asks"][0]["price"])
spot_mid = (bid + ask) / 2
print(f"Spot mid: {spot_mid:.6f}")

# 5. Fetch all swap rates for EUR/USD via correct endpoint
swap_url = "https://api-fxpractice.oanda.com/v3/instruments/EUR_USD/swap_rates"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
swap_resp = requests.get(swap_url, headers=headers)
swap_data = swap_resp.json()
print("\nSWAP RATES RESPONSE:")
print(json.dumps(swap_data, indent=2))

# 6. Extract 1M swap-rate if available
days = 30  # tenor in days for 1M
swap_rates = swap_data.get("swapRates", [])
if swap_rates:
    rate_1m = next((r for r in swap_rates if r.get("tenor") == "1M"), None)
    if rate_1m:
        print("\nObserved market 1M swap-rate object:")
        print(json.dumps(rate_1m, indent=2))
        # Compute observed forward outright: spot_mid + swap points
        fwd_pts = (rate_1m["longRate"] - rate_1m["shortRate"]) * days / 360
        obs_fwd = spot_mid + fwd_pts
        print(f"Observed 1M forward (spot + swap points): {obs_fwd:.6f}")
    else:
        print("\n⚠️ 1M tenor not found in swapRates; falling back to theoretical CIP")
        # placeholder interest rates
        r_domestic = 0.025  # e.g., USD OIS
        r_foreign = 0.005   # e.g., EUR OIS
        obs_fwd = theoretical_forward(spot_mid, r_domestic, r_foreign, days)
        print(f"Fallback observed forward: {obs_fwd:.6f}")
else:
    print("\n⚠️ No swapRates data; using theoretical CIP as observed forward")
    # placeholder interest rates
    r_domestic = 0.025
    r_foreign = 0.005
    obs_fwd = theoretical_forward(spot_mid, r_domestic, r_foreign, days)
    print(f"Fallback observed forward: {obs_fwd:.6f}")

# 7. Compute theoretical forward and deviation
# placeholder interest rates (update with live data when available)
r_domestic = 0.025
r_foreign = 0.005
theo_fwd = theoretical_forward(spot_mid, r_domestic, r_foreign, days)
dev_bps = deviation_bps(obs_fwd, theo_fwd)
print(f"\nTheoretical 1M Forward: {theo_fwd:.6f}")
print(f"Deviation         : {dev_bps:.2f} bps")

# 8. Flag arbitrage signal if deviation exceeds threshold
threshold = 2.0  # bps
if abs(dev_bps) > threshold:
    direction = "Sell forward / Buy spot" if dev_bps > 0 else "Buy forward / Sell spot"
    print(f"⚠️ Arbitrage signal: {dev_bps:.2f} bps → {direction}")
else:
    print("✅ No actionable arbitrage (deviation within threshold).")

