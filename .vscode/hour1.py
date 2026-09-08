

import argparse
import os
from datetime import datetime

import ee
import pandas as pd

# ──────────────────── CONFIGURATION ────────────────────
PROJECT_ID = "graceful-disk-507908-m5"       # ← your GCP project
BBOX       = [80.15, 12.90, 80.30, 13.10]   # ← [lon_min, lat_min, lon_max, lat_max]
GRID_SIZE  = 20                              # 20×20 grid cells
OUTPUT_DIR = "data_runs"                     # each run's CSV lives here
LATEST_CSV = "hotspot_data.csv"              # always mirrors the most recent run


# ──────────────────── HELPERS ────────────────────
def parse_date(s):
    """Validate a YYYY-MM-DD string."""
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date '{s}'. Use YYYY-MM-DD.")


def prompt_dates():
    """Ask the user for start and end dates interactively."""
    print("\n── Enter date range for satellite data ──\n")
    while True:
        s = input("Start date (YYYY-MM-DD): ").strip()
        try:
            start = datetime.strptime(s, "%Y-%m-%d")
            break
        except ValueError:
            print("  Invalid format. Use YYYY-MM-DD.")

    while True:
        e = input("End date   (YYYY-MM-DD): ").strip()
        try:
            end = datetime.strptime(e, "%Y-%m-%d")
            if end <= start:
                print("  End date must be after start date.")
                continue
            break
        except ValueError:
            print("  Invalid format. Use YYYY-MM-DD.")

    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def init_ee():
    """Authenticate only when needed, then initialise."""
    try:
        ee.Initialize(project=PROJECT_ID)
    except Exception:
        print("⏳ Not authenticated — opening browser …")
        ee.Authenticate()
        ee.Initialize(project=PROJECT_ID)
    print(f"✓ Connected to Earth Engine  (project: {PROJECT_ID})")


def build_grid(aoi):
    """Create a GRID_SIZE × GRID_SIZE FeatureCollection over the AOI."""
    coords = aoi.bounds().coordinates().get(0).getInfo()
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    lon_min, lon_max = min(lons), max(lons)
    lat_min, lat_max = min(lats), max(lats)
    lon_step = (lon_max - lon_min) / GRID_SIZE
    lat_step = (lat_max - lat_min) / GRID_SIZE

    cells = []
    for i in range(GRID_SIZE):
        for j in range(GRID_SIZE):
            cell = ee.Geometry.Rectangle([
                lon_min + j * lon_step, lat_min + i * lat_step,
                lon_min + (j + 1) * lon_step, lat_min + (i + 1) * lat_step,
            ])
            cells.append(ee.Feature(cell, {
                "row": i, "col": j, "cell_id": f"{i}_{j}",
            }))
    return ee.FeatureCollection(cells)


# ──────────────────── MAIN PIPELINE ────────────────────
def fetch_and_save(start_date, end_date):
    """Fetch all layers for the given date range, merge, save to a fresh timestamped CSV."""
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n{'═' * 55}")
    print(f"  Date range: {start_date} → {end_date}")
    print(f"  AOI (bbox): {BBOX}")
    print(f"  Run ID    : {run_timestamp}")
    print(f"{'═' * 55}")

    aoi  = ee.Geometry.Rectangle(BBOX)
    grid = build_grid(aoi)
    print(f"✓ Grid: {GRID_SIZE}×{GRID_SIZE} = {GRID_SIZE**2} cells\n")

    # ── MODIS LST (8-day composite, 1 km) ──
    # LST_Day_1km: scale factor 0.02, Kelvin → °C
    print("  Fetching MODIS LST …")
    lst_img = (
        ee.ImageCollection("MODIS/061/MOD11A2")
        .filterDate(start_date, end_date)
        .filterBounds(aoi)
        .select("LST_Day_1km")
        .mean()
        .multiply(0.02)
        .subtract(273.15)
        .rename("lst_celsius")
    )

    # ── MODIS NDVI (16-day composite, 1 km) ──
    # NDVI: scale factor 0.0001
    print("  Fetching MODIS NDVI …")
    ndvi_img = (
        ee.ImageCollection("MODIS/061/MOD13A2")
        .filterDate(start_date, end_date)
        .filterBounds(aoi)
        .select("NDVI")
        .mean()
        .multiply(0.0001)
        .rename("ndvi")
    )

    # ── GHSL Built-up density (static, 0-1 fraction) ──
    print("  Fetching GHSL built-up surface …")
    built_img = (
        ee.Image("JRC/GHSL/P2023A/GHS_BUILT_S/2020")
        .select(0)
        .divide(10000)
        .clamp(0, 1)
        .rename("building_density")
    )

    # ── WorldPop Population (static) ──
    print("  Fetching WorldPop population …")
    pop_img = (
        ee.ImageCollection("WorldPop/GP/100m/pop")
        .filterDate("2020-01-01", "2021-01-01")
        .filterBounds(aoi)
        .mosaic()
        .rename("population")
    )

    # ── Combine & reduce per cell ──
    combined = lst_img.addBands([ndvi_img, built_img, pop_img])

    print("  Reducing regions (this may take a minute) …")
    reduced = combined.reduceRegions(
        collection=grid,
        reducer=ee.Reducer.mean(),
        scale=1000,
    )
    result = reduced.getInfo()

    # ── Build DataFrame ──
    rows = []
    for f in result["features"]:
        p  = f["properties"]
        bd = p.get("building_density") or 0
        rows.append({
            "cell_id":          p["cell_id"],
            "row":              p["row"],
            "col":              p["col"],
            "lst_celsius":      p.get("lst_celsius"),
            "ndvi":             p.get("ndvi"),
            "building_density": bd,
            "impervious_pct":   min(1.0, bd * 1.1),
            "population":       p.get("population") or 0,
        })

    df = pd.DataFrame(rows)

    n_missing = df["lst_celsius"].isna().sum()
    if n_missing:
        print(f"  ⚠ {n_missing}/{len(df)} cells have no LST data (dropped)")

    df = df.dropna(subset=["lst_celsius"])

    # ── Save: a fresh, uniquely-named file per run, plus a "latest" pointer ──
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    run_csv = os.path.join(OUTPUT_DIR, f"hotspot_data_{run_timestamp}.csv")
    df.to_csv(run_csv, index=False)
    df.to_csv(LATEST_CSV, index=False)  # analyze.py/recommend.py/app.py read this fixed name

    print(f"\n✓ Saved {len(df)} cells → {run_csv}")
    print(f"✓ Also updated       → {LATEST_CSV}  (used by the rest of the pipeline)")
    if not df.empty:
        print(f"  LST  : {df.lst_celsius.min():.1f} – {df.lst_celsius.max():.1f} °C")
        print(f"  NDVI : {df.ndvi.min():.3f} – {df.ndvi.max():.3f}")
        print(f"  Pop  : {df.population.min():.0f} – {df.population.max():.0f}")


# ──────────────────── ENTRY POINT ────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch satellite data for a date range",
    )
    parser.add_argument("--start", type=parse_date, default=None,
                        help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=parse_date, default=None,
                        help="End date (YYYY-MM-DD)")
    args = parser.parse_args()

    if args.start and args.end:
        if args.end <= args.start:
            parser.error("--end must be after --start")
        start_date = args.start.strftime("%Y-%m-%d")
        end_date   = args.end.strftime("%Y-%m-%d")
    elif args.start or args.end:
        parser.error("Both --start and --end are required")
    else:
        start_date, end_date = prompt_dates()

    init_ee()
    fetch_and_save(start_date, end_date)