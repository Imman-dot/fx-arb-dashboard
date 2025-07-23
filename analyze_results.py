import pandas as pd

# 1) Load the CSV
df = pd.read_csv("optimization_results.csv")

# 2) Sort by total_pnl descending
top = df.sort_values("total_pnl", ascending=False).head(10)

# 3) Print to console
print("Top 10 parameter sets by Total PnL:\n", top.to_string(index=False))

