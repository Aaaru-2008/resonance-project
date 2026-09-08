# HeatScape Backend

FastAPI backend wrapping the hotspot-detection and intervention-recommendation logic.

## Setup
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Interactive docs: http://127.0.0.1:8000/docs

## Endpoints

### GET /health
Simple liveness check.

### POST /analyze
Form-data: `file` (CSV with `ndvi`, `building_density`, `impervious_pct`, `lst_celsius`
columns — `cell_id` optional but recommended), `std_multiplier` (optional, default 1.5).
Returns hotspots + per-hotspot cause breakdown (`cause_low_vegetation`,
`cause_impervious_surface`, `cause_building_density`) + global feature importance.

### POST /recommend
Form-data: `file` (CSV that already has the `cause_*` columns — i.e. output of `/analyze`),
`target_reduction` (optional, default 2.0 °C).
Returns intervention + cost per hotspot.

### POST /pipeline  <- most likely what your frontend calls
Form-data: `file` (raw grid CSV, same as `/analyze`), `std_multiplier`, `target_reduction`.
Runs analyze + recommend in one call and returns the combined result.

## Sample request
```bash
curl -X POST http://127.0.0.1:8000/pipeline \
  -F "file=@sample_grid.csv" \
  -F "target_reduction=2.0"
```

## Bug fixed vs. the original scripts
The original `analyse.py` produced a cause-score column named `building_density`,
which collided with the raw feature column of the same name (duplicate column names
in the dataframe). This silently broke `recommend.py` downstream (`max()` on a
pandas Series instead of a scalar, causing a crash). Fixed here by prefixing
cause-score columns with `cause_` (`cause_low_vegetation`, `cause_impervious_surface`,
`cause_building_density`).

## Note
`hour1.py` and `recommend.py` (as uploaded) were byte-for-byte identical — both
folded into `app/recommend.py`.
