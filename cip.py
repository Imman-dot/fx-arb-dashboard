def theoretical_forward(spot: float, r_dom: float, r_for: float, tenor_days: int) -> float:
    """
    Calculate the theoretical forward rate:
      F = S * (1 + r_dom * (tenor_days/360)) / (1 + r_for * (tenor_days/360))
    """
    return spot * (1 + r_dom * tenor_days / 360) / (1 + r_for * tenor_days / 360)

def deviation_bps(obs_fwd: float, theo_fwd: float) -> float:
    """
    Compute the deviation between observed and theoretical forward,
    expressed in basis points.
    """
    return (obs_fwd - theo_fwd) / theo_fwd * 10_000

if __name__ == "__main__":
    # Example inputs (replace these with your real data)
    spot_rate      = 1.16910            # from PricingInfo closeout or mid
    observed_fwd   = 1.16930            # placeholder forward outright
    r_domestic     = 0.025              # e.g., 2.5% annual domestic interest
    r_foreign      = 0.005              # e.g., 0.5% annual foreign interest
    tenor_in_days  = 30                 # for 1M tenor, approx 30 days

    theo = theoretical_forward(spot_rate, r_domestic, r_foreign, tenor_in_days)
    dev  = deviation_bps(observed_fwd, theo)

    print(f"Theoretical 1M Forward: {theo:.6f}")
    print(f"Deviation: {dev:.2f} bps")
