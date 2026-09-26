#!/usr/bin/env python3
"""
One-off diagnostic (NOT part of the main pipeline): empirically tests whether Copernicus
GLO-30 DEM elevation differences across Bangkok canal-graph edges carry a usable
flow-direction signal, or are noise-dominated.

Result (this run, 2026-09-23): NEGATIVE. Median |elevation diff| across all 6,155 canal
edges is 0.77 m; even restricted to edges >= 200 m long, median is still only 0.88 m.
Copernicus GLO-30 is a DSM (includes building/canopy height, not bare-earth), with quoted
absolute vertical accuracy on the order of a few meters and materially worse local/relative
noise in dense urban terrain from radar speckle and structure clutter. A ~0.8 m median
signal sitting at or below that noise floor cannot be trusted to point "downhill" reliably
-- using it would silently convert noise into a fabricated direction claim. This is why
DEM-based direction is NOT wired into build_bangkok_canals.py's direction-inference step.

Data source: Copernicus DEM GLO-30, tile Copernicus_DSM_COG_10_N13_00_E100_00_DEM,
fetched anonymously (no API key/registration needed) from the public AWS Open Data
registry mirror (registry.opendata.aws/copernicus-dem/), not from ESA's own gated
Copernicus Data Space Ecosystem (which does require CCM-user registration). This AWS
mirror access path being open was itself a finding worth recording, even though the
elevation signal it delivers doesn't help here.

Usage:
    mkdir -p raw/bangkok/dem
    curl -o raw/bangkok/dem/Copernicus_DSM_N13_E100.tif \
      https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N13_00_E100_00_DEM/Copernicus_DSM_COG_10_N13_00_E100_00_DEM.tif
    python3 dem_signal_check.py
"""
from pathlib import Path

import numpy as np
import rasterio

import build_bangkok_canals as bc

HERE = Path(__file__).parent
DEM_TIF = HERE / "raw" / "bangkok" / "dem" / "Copernicus_DSM_N13_E100.tif"


def main():
    if not DEM_TIF.exists():
        raise SystemExit(f"Missing {DEM_TIF} -- see module docstring for the one-time download command.")

    gdf = bc.load_canal_lines()
    G = bc.build_undirected_canal_graph(gdf)
    print(f"Canal graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    with rasterio.open(DEM_TIF) as src:
        arr = src.read(1)

        def elev(lon, lat):
            row, col = src.index(lon, lat)
            r0, r1 = max(0, row - 1), min(arr.shape[0], row + 2)
            c0, c1 = max(0, col - 1), min(arr.shape[1], col + 2)
            patch = arr[r0:r1, c0:c1]
            patch = patch[~np.isnan(patch)]
            return float(np.median(patch)) if patch.size else np.nan

        lengths, diffs = [], []
        for a, b, d in G.edges(data=True):
            ea, eb = elev(*a), elev(*b)
            if np.isnan(ea) or np.isnan(eb):
                continue
            lengths.append(d["length_km"])
            diffs.append(abs(ea - eb))

    lengths, diffs = np.array(lengths), np.array(diffs)
    print(f"{len(diffs)}/{G.number_of_edges()} edges got a valid elevation-diff reading")
    print(f"median |dz| all edges:        {np.median(diffs):.2f} m")
    print(f"median |dz| edges >= 200 m:   {np.median(diffs[lengths >= 0.2]):.2f} m "
          f"(n={int((lengths >= 0.2).sum())})")
    for thresh in (0.5, 1, 2, 3):
        print(f"  frac edges with |dz| > {thresh} m: {(diffs > thresh).mean():.3f}")
    print("\nConclusion: signal (~0.8 m median) is at/below Copernicus GLO-30's own "
          "vertical-accuracy noise floor for this flat, urban, DSM-not-DTM terrain. "
          "NOT wired into direction inference -- see module docstring.")


if __name__ == "__main__":
    main()
