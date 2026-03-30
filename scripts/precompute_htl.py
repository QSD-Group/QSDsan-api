#!/usr/bin/env python3
"""
One-time script to pre-compute HTL results for all NJ counties.

Reads county sludge totals from app/data/htl/htl_data.csv, runs htl_calc()
for each county, and writes MDSP ($/gal) and GWP (lb CO2/gal) result columns
back to the same CSV.

Usage:
    uv run python scripts/precompute_htl.py

This is slow (~minutes) due to exposan simulation per county. Run once,
commit the enriched CSV, and the htl_county() service function will use
the pre-computed columns for instant lookups.
"""
import os
import sys

# Make sure app/ is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from app.services.htl_service import htl_calc

CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "app", "data", "htl", "htl_data.csv",
)

def main():
    df = pd.read_csv(CSV_PATH)

    mdsps = []
    gwps  = []

    for _, row in df.iterrows():
        county = row["County"]
        dmt    = float(row["County Total (Dry Metric Tonnes/Year)"])
        mass_kg_hr = dmt * 1000 / 24  # dry metric tonnes/yr → kg/hr

        print(f"Computing {county} (DMT={dmt:.1f}) ...", end=" ", flush=True)
        try:
            mdsp, gwp = htl_calc(mass_kg_hr)
            print(f"MDSP={mdsp:.4f} $/gal, GWP={gwp:.4f} lb CO2/gal")
        except Exception as exc:
            print(f"ERROR: {exc}")
            mdsp, gwp = float("nan"), float("nan")

        mdsps.append(mdsp)
        gwps.append(gwp)

    df["MDSP ($/gal)"]      = mdsps
    df["GWP (lb CO2/gal)"]  = gwps
    df.to_csv(CSV_PATH, index=False)
    print(f"\nWrote enriched CSV to {CSV_PATH}")


if __name__ == "__main__":
    main()
