import math
import os
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# CORRECTED IMPORTS FOR YOUR FOLDER STRUCTURE
from app.analyze import detect_hotspots
from app.recommend import recommend_for_all
import hour1

app = FastAPI(title="HeatScape API - Earth Engine Edition", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "hotspot_data.csv"

def _clean_json(records: list[dict]) -> list[dict]:
    for row in records:
        for k, v in row.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                row[k] = None
    return records

@app.on_event("startup")
def startup_event():
    try:
        hour1.init_ee()
    except Exception as e:
        print("Earth Engine init skipped. Authenticate via terminal first.")

@app.get("/health")
def health():
    return {"status": "ok", "earth_engine": "ready"}

@app.post("/fetch-satellite")
def fetch_satellite(start_date: str = Query("2023-01-01"), end_date: str = Query("2023-12-31")):
    try:
        hour1.fetch_and_save(start_date, end_date)
        return {"message": f"Successfully fetched EE data", "file": DATA_FILE}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/analyze")
def analyze(std_multiplier: float = Query(1.5)):
    if not os.path.exists(DATA_FILE):
        raise HTTPException(status_code=404, detail="No data found. Call /fetch-satellite first.")
        
    df = pd.read_csv(DATA_FILE)
    try:
        hotspots, global_importance = detect_hotspots(df, std_multiplier=std_multiplier)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "hotspot_count": len(hotspots),
        "global_feature_importance": global_importance,
        "hotspots": _clean_json(hotspots.to_dict(orient="records")),
    }

@app.get("/recommend")
def recommend(target_reduction: float = Query(2.0)):
    if not os.path.exists(DATA_FILE):
        raise HTTPException(status_code=404, detail="No data found. Call /fetch-satellite first.")
        
    df = pd.read_csv(DATA_FILE)
    hotspots, _ = detect_hotspots(df)
    result = recommend_for_all(hotspots, target_reduction=target_reduction)
    
    return {
        "target_reduction_c": target_reduction,
        "recommendations": _clean_json(result.to_dict(orient="records")),
    }

@app.get("/pipeline")
def pipeline(std_multiplier: float = Query(1.5), target_reduction: float = Query(2.0)):
    if not os.path.exists(DATA_FILE):
        raise HTTPException(status_code=404, detail="No data found. Call /fetch-satellite first.")
        
    df = pd.read_csv(DATA_FILE)
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