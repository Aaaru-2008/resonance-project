"""
HeatScape backend -- Urban Heat Reduction Planner API.

Endpoints:
  GET  /health
  POST /analyze     -- upload raw CSV, get hotspots + cause breakdown + feature importance
  POST /recommend    -- upload hotspots CSV (or reuse /analyze output), get interventions + cost
  POST /pipeline      -- upload raw CSV -> run analyze + recommend in one call (what the frontend
                          will most likely hit for the live demo)

Run locally:
  pip install -r requirements.txt
  uvicorn app.main:app --reload
  -> docs at http://127.0.0.1:8000/docs
"""
import io
import math

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.analyze import detect_hotspots
from app.recommend import recommend_for_all

app = FastAPI(title="HeatScape API", version="1.0.0")

# Wide open for hackathon demo purposes -- tighten allow_origins before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _read_csv_upload(file: UploadFile) -> pd.DataFrame:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")
    raw = file.file.read()
    try:
        return pd.read_csv(io.BytesIO(raw))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {exc}")


def _clean_json(records: list[dict]) -> list[dict]:
    """Replace NaN/inf (which aren't valid JSON) with None so the response never breaks the frontend."""
    for row in records:
        for k, v in row.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                row[k] = None
    return records


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...), std_multiplier: float = Form(1.5)):
    """
    Expects a CSV with columns: ndvi, building_density, impervious_pct, lst_celsius
    (plus optionally cell_id / lat / lon which just pass through).
    """
    df = _read_csv_upload(file)
    try:
        hotspots, global_importance = detect_hotspots(df, std_multiplier=std_multiplier)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "hotspot_count": len(hotspots),
        "global_feature_importance": global_importance,
        "hotspots": _clean_json(hotspots.to_dict(orient="records")),
    }


@app.post("/recommend")
async def recommend(file: UploadFile = File(...), target_reduction: float = Form(2.0)):
    """
    Expects a CSV that already has hotspot cause-breakdown columns
    (low_vegetation, impervious_surface, building_density) -- i.e. the output of /analyze.
    """
    hotspots = _read_csv_upload(file)
    required = ["cause_low_vegetation", "cause_impervious_surface", "cause_building_density"]
    missing = [c for c in required if c not in hotspots.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing cause columns: {missing}. Run /analyze first.")

    result = recommend_for_all(hotspots, target_reduction=target_reduction)
    return {
        "target_reduction_c": target_reduction,
        "recommendations": _clean_json(result.to_dict(orient="records")),
    }


@app.post("/pipeline")
async def pipeline(
    file: UploadFile = File(...),
    std_multiplier: float = Form(1.5),
    target_reduction: float = Form(2.0),
):
    """
    One-shot endpoint: raw grid-cell CSV in -> hotspots + interventions + cost out.
    This is the one your frontend most likely wants for the live demo.
    """
    df = _read_csv_upload(file)
    try:
        hotspots, global_importance = detect_hotspots(df, std_multiplier=std_multiplier)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    result = recommend_for_all(hotspots, target_reduction=target_reduction)

    return {
        "hotspot_count": len(result),
        "global_feature_importance": global_importance,
        "target_reduction_c": target_reduction,
        "results": _clean_json(result.to_dict(orient="records")),
    }
