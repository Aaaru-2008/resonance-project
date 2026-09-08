"""Detect urban heat hotspots and attribute causes using feature importance from a Random Forest.

Refactored from analyse.py: same logic, wrapped as reusable functions instead of a top-to-bottom script.
"""
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

FEATURES = ["ndvi", "building_density", "impervious_pct"]


def detect_hotspots(df: pd.DataFrame, std_multiplier: float = 1.5) -> tuple[pd.DataFrame, dict]:
    """
    Given a dataframe with columns FEATURES + 'lst_celsius' (and ideally 'cell_id'),
    returns (hotspots_df, global_feature_importance).
    """
    missing = [c for c in FEATURES + ["lst_celsius"] if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    X, y = df[FEATURES], df["lst_celsius"]
    model = RandomForestRegressor(n_estimators=200, random_state=42)
    model.fit(X, y)
    global_importance = dict(zip(FEATURES, model.feature_importances_.tolist()))

    threshold = df.lst_celsius.mean() + std_multiplier * df.lst_celsius.std()
    df = df.copy()
    df["is_hotspot"] = df.lst_celsius > threshold

    avg = df[FEATURES].mean()

    def cause_breakdown(row):
        # NOTE: keys are prefixed with "cause_" so they never collide with the raw
        # feature columns already on the dataframe (e.g. "building_density" the
        # feature vs. "building_density" the cause score) -- that collision caused
        # a silent duplicate-column bug in the original script.
        dev = {
            "cause_low_vegetation": max(0, avg.ndvi - row.ndvi) * global_importance["ndvi"],
            "cause_impervious_surface": max(0, row.impervious_pct - avg.impervious_pct) * global_importance["impervious_pct"],
            "cause_building_density": max(0, row.building_density - avg.building_density) * global_importance["building_density"],
        }
        total = sum(dev.values()) or 1
        return {k: round(v / total * 100, 1) for k, v in dev.items()}

    hotspots = df[df.is_hotspot].copy()
    if hotspots.empty:
        return hotspots, global_importance

    breakdowns = hotspots.apply(cause_breakdown, axis=1, result_type="expand")
    hotspots = pd.concat([hotspots, breakdowns], axis=1)
    hotspots = hotspots.sort_values("lst_celsius", ascending=False)

    return hotspots, global_importance
