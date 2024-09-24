#!/usr/bin/env python3
"""
Script to filter missing airports by a bounding region and output to a GeoJSON file.

Usage:
    python filter_missing_airports.py <bounding_geojson_path> <output_geojson_path>
"""

import sys
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

def main(bounding_geojson_path, output_geojson_path):
    # Step 1: Load the Missing Airports Data
    # ---------------------------------------
    # Load the missing airports CSV into a GeoDataFrame
    missing_airports_df = pd.read_csv('data/world/osm/overpass/missing_from_ourairports.csv')

    # Create geometries for missing airports
    missing_airports_geometry = [
        Point(xy) for xy in zip(missing_airports_df['longitude_deg'], missing_airports_df['latitude_deg'])
    ]
    missing_airports_gdf = gpd.GeoDataFrame(
        missing_airports_df, geometry=missing_airports_geometry, crs='EPSG:4326'
    )

    # Step 2: Load the Bounding Region GeoJSON
    # ----------------------------------------
    # Load the bounding region GeoJSON file
    bounding_region_gdf = gpd.read_file(bounding_geojson_path)

    # Ensure both GeoDataFrames are in the same CRS
    if bounding_region_gdf.crs != missing_airports_gdf.crs:
        bounding_region_gdf = bounding_region_gdf.to_crs(missing_airports_gdf.crs)

    # Step 3: Filter Missing Airports by Bounding Region
    # --------------------------------------------------
    # Combine all geometries in bounding_region_gdf into a single geometry
    bounding_union = bounding_region_gdf.unary_union

    # Filter missing airports to those within the bounding region
    missing_airports_in_region_gdf = missing_airports_gdf[
        missing_airports_gdf.geometry.within(bounding_union)
    ]

    # Step 4: Output the Filtered Airports to a GeoJSON File
    # ------------------------------------------------------
    # Output the filtered GeoDataFrame to a GeoJSON file
    missing_airports_in_region_gdf.to_file(output_geojson_path, driver='GeoJSON')

    print(f"Filtered airports saved to {output_geojson_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python filter_missing_airports.py <bounding_geojson_path> <output_geojson_path>")
        sys.exit(1)

    bounding_geojson_path = sys.argv[1]
    output_geojson_path = sys.argv[2]

    main(bounding_geojson_path, output_geojson_path)

