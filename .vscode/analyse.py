"""Detect hotspots and attribute causes using feature importance from a Random Forest."""
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

df = pd.read_csv("hotspot_data.csv")

FEATURES = ["ndvi", "building_density", "impervious_pct"]
X, y = df[FEATURES], df["lst_celsius"]

model = RandomForestRegressor(n_estimators=200, random_state=42)
model.fit(X, y)
global_importance = dict(zip(FEATURES, model.feature_importances_))

# Flag hotspots: LST above mean + 1 std
threshold = df.lst_celsius.mean() + 1.5 * df.lst_celsius.std()
df["is_hotspot"] = df.lst_celsius > threshold

# Per-hotspot cause attribution: how far each feature deviates from the grid average,
# weighted by that feature's global importance -> a per-cell "contribution" score.
avg = df[FEATURES].mean()
def cause_breakdown(row):
    dev = {
        "low_vegetation": max(0, avg.ndvi - row.ndvi) * global_importance["ndvi"],
        "impervious_surface": max(0, row.impervious_pct - avg.impervious_pct) * global_importance["impervious_pct"],
        "building_density": max(0, row.building_density - avg.building_density) * global_importance["building_density"],
    }
    total = sum(dev.values()) or 1
    return {k: round(v / total * 100, 1) for k, v in dev.items()}

hotspots = df[df.is_hotspot].copy()
breakdowns = hotspots.apply(cause_breakdown, axis=1, result_type="expand")
hotspots = pd.concat([hotspots, breakdowns], axis=1)
hotspots = hotspots.sort_values("lst_celsius", ascending=False)

hotspots.to_csv("hotspots_analysis.csv", index=False)
print(f"Threshold: {threshold:.1f}°C | Hotspots found: {len(hotspots)}")
print(f"Global feature importance: {global_importance}")