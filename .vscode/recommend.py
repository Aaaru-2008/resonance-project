"""Map each hotspot's dominant cause to an intervention with cost and impact estimates."""

# (cost per unit in INR, °C reduction per unit, unit description) — indicative figures, cite as such in report
INTERVENTIONS = {
    "low_vegetation": {
        "name": "Urban tree planting / green roofs",
        "cost_per_unit": 3500,       # INR per tree
        "unit": "trees",
        "temp_reduction_per_unit": 0.015,  # °C per tree, diminishing but additive
    },
    "impervious_surface": {
        "name": "Reflective / permeable pavement",
        "cost_per_unit": 1200,       # INR per m²
        "unit": "m²",
        "temp_reduction_per_unit": 0.008,
    },
    "building_density": {
        "name": "Cool/reflective roofing",
        "cost_per_unit": 900,        # INR per m²
        "unit": "m²",
        "temp_reduction_per_unit": 0.01,
    },
}

def recommend_for_hotspot(row, target_reduction=2.0):
    """Given a hotspot row with cause % columns, return the dominant intervention scaled to hit target_reduction."""
    causes = {k: row[k] for k in INTERVENTIONS}
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

if __name__ == "__main__":
    import pandas as pd
    hotspots = pd.read_csv("hotspots_analysis.csv")
    recs = hotspots.apply(recommend_for_hotspot, axis=1, result_type="expand")
    result = pd.concat([hotspots, recs], axis=1)
    result.to_csv("final_recommendations.csv", index=False)
    print(result[["cell_id", "lst_celsius", "dominant_cause", "intervention", "estimated_cost_inr"]].head(10))