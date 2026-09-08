"""Map each hotspot's dominant cause to an intervention with cost and impact estimates.

Refactored from hour1.py / recommend.py (identical scripts) into reusable functions.
Cost/reduction figures are indicative -- cite as such in the report/demo.
"""
import pandas as pd

INTERVENTIONS = {
    "low_vegetation": {
        "name": "Urban tree planting / green roofs",
        "cost_per_unit": 3500,        # INR per tree
        "unit": "trees",
        "temp_reduction_per_unit": 0.015,  # °C per tree, diminishing but additive
    },
    "impervious_surface": {
        "name": "Reflective / permeable pavement",
        "cost_per_unit": 1200,        # INR per m²
        "unit": "m²",
        "temp_reduction_per_unit": 0.008,
    },
    "building_density": {
        "name": "Cool/reflective roofing",
        "cost_per_unit": 900,         # INR per m²
        "unit": "m²",
        "temp_reduction_per_unit": 0.01,
    },
}


def recommend_for_hotspot(row, target_reduction: float = 2.0) -> dict:
    """Given a hotspot row with cause % columns, return the dominant intervention scaled to hit target_reduction."""
    causes = {k: row[f"cause_{k}"] for k in INTERVENTIONS}
    dominant = max(causes, key=causes.get)
    spec = INTERVENTIONS[dominant]
    units_needed = target_reduction / spec["temp_reduction_per_unit"]
    cost = units_needed * spec["cost_per_unit"]
    return {
        "dominant_cause": dominant.replace("_", " ").title(),
        "intervention": spec["name"],
        "units_needed": round(units_needed),
        "unit_type": spec["unit"],
        "estimated_cost_inr": round(cost),
        "estimated_temp_reduction_c": target_reduction,
    }


def recommend_for_all(hotspots: pd.DataFrame, target_reduction: float = 2.0) -> pd.DataFrame:
    if hotspots.empty:
        return hotspots
    recs = hotspots.apply(lambda row: recommend_for_hotspot(row, target_reduction), axis=1, result_type="expand")
    return pd.concat([hotspots, recs], axis=1)
