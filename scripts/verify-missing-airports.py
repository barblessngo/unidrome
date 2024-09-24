#!/usr/bin/env python3
"""
Interactive script to verify missing airports within a bounding region.

Usage:
    python verify_missing_airports.py <bounding_geojson_path>

The script will:
- Load missing airports from 'data/world/osm/overpass/missing_from_ourairports.csv'.
- Filter them by the provided bounding region.
- Exclude airports already listed in 'data/world/ourairports/unable-to-be-seen-in-osm-imagery.csv'.
- Iterate through each airport, opening its OSM editor link in a browser.
- Prompt the user to confirm if there is a missing airport (default 'n').
- Record any airports unable to be seen in imagery to 'unable-to-be-seen-in-osm-imagery.csv'.
"""

import sys
import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import webbrowser

def main(bounding_geojson_path):
    # Paths to data files
    missing_airports_csv = 'data/world/osm/overpass/missing_from_ourairports.csv'
    unable_to_see_csv = 'data/world/ourairports/unable-to-be-seen-in-osm-imagery.csv'

    # Step 1: Load the Missing Airports Data
    # ---------------------------------------
    try:
        missing_airports_df = pd.read_csv(missing_airports_csv)
    except FileNotFoundError:
        print(f"Error: Missing airports CSV file '{missing_airports_csv}' not found.")
        sys.exit(1)

    if missing_airports_df.empty:
        print("Error: Missing airports CSV file is empty.")
        sys.exit(1)

    if 'longitude_deg' not in missing_airports_df.columns or 'latitude_deg' not in missing_airports_df.columns:
        print("Error: CSV file does not contain 'longitude_deg' and 'latitude_deg' columns.")
        sys.exit(1)

    # Create geometries for missing airports
    missing_airports_geometry = [
        Point(xy) for xy in zip(missing_airports_df['longitude_deg'], missing_airports_df['latitude_deg'])
    ]
    missing_airports_gdf = gpd.GeoDataFrame(
        missing_airports_df, geometry=missing_airports_geometry, crs='EPSG:4326'
    )

    # Step 2: Load the Bounding Region GeoJSON
    # ----------------------------------------
    try:
        bounding_region_gdf = gpd.read_file(bounding_geojson_path)
    except FileNotFoundError:
        print(f"Error: Bounding region GeoJSON file '{bounding_geojson_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading GeoJSON file: {e}")
        sys.exit(1)

    if bounding_region_gdf.empty:
        print("Error: Bounding region GeoJSON file is empty.")
        sys.exit(1)

    # Ensure both GeoDataFrames are in the same CRS
    if bounding_region_gdf.crs != missing_airports_gdf.crs:
        print("CRS mismatch. Reprojecting bounding region to match missing airports CRS.")
        bounding_region_gdf = bounding_region_gdf.to_crs(missing_airports_gdf.crs)

    # Step 3: Filter Missing Airports by Bounding Region
    # --------------------------------------------------
    # Combine all geometries in bounding_region_gdf into a single geometry
    bounding_union = bounding_region_gdf.unary_union

    # Filter missing airports to those within the bounding region
    missing_airports_in_region_gdf = missing_airports_gdf[
        missing_airports_gdf.geometry.within(bounding_union)
    ].reset_index(drop=True)

    if missing_airports_in_region_gdf.empty:
        print("No missing airports found within the specified bounding region.")
        sys.exit(0)
    else:
        print(f"Found {len(missing_airports_in_region_gdf)} missing airports within the region.")

    # Step 4: Load Existing Unable-to-See Airports (if any)
    # -----------------------------------------------------
    if os.path.exists(unable_to_see_csv):
        unable_to_see_df = pd.read_csv(unable_to_see_csv)
        # Ensure that 'id' column exists for merging
        if 'id' not in unable_to_see_df.columns:
            print(f"Error: '{unable_to_see_csv}' does not contain 'id' column.")
            sys.exit(1)
    else:
        unable_to_see_df = pd.DataFrame(columns=missing_airports_df.columns)

    # Step 5: Exclude Already Reviewed Airports
    # -----------------------------------------
    # Exclude airports that are already in unable_to_see_df
    if not unable_to_see_df.empty:
        missing_airports_in_region_gdf = missing_airports_in_region_gdf[
            ~missing_airports_in_region_gdf['id'].isin(unable_to_see_df['id'])
        ].reset_index(drop=True)

        print(f"After excluding already reviewed airports, {len(missing_airports_in_region_gdf)} remain to be reviewed.")

    if missing_airports_in_region_gdf.empty:
        print("No new airports to review in the specified bounding region.")
        sys.exit(0)

    # Step 6: Iterate Through Missing Airports
    # ----------------------------------------
    for index, row in missing_airports_in_region_gdf.iterrows():
        print(f"\nProcessing airport {index + 1} of {len(missing_airports_in_region_gdf)}")
        print(f"Name: {row.get('name', 'Unknown')}")
        print(f"IATA Code: {row.get('iata_code', 'N/A')}")
        print(f"ICAO Code: {row.get('ident', 'N/A')}")
        print(f"Location: ({row['latitude_deg']}, {row['longitude_deg']})")
        print(f"OSM Editor Link: {row['osm_editor_link']}")

        # Open the OSM editor link in a web browser
        webbrowser.open(row['osm_editor_link'], new=2)  # new=2 opens in a new tab, if possible

        # Prompt the user for input
        user_input = input("Is there a missing airport here? [y/N]: ").strip().lower()
        if user_input == 'y':
            print("Marked as missing airport.")
            # Do nothing, as it's already considered missing
        else:
            print("Marked as unable to be seen in imagery.")
            # Add to unable_to_see_df using pd.concat
            unable_to_see_df = pd.concat([unable_to_see_df, pd.DataFrame([row])], ignore_index=True)

            # Save the unable_to_see_df after each entry
            unable_to_see_df.to_csv(unable_to_see_csv, index=False)

    print("\nVerification complete.")
    print(f"Unable to see airports saved to '{unable_to_see_csv}'.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python verify_missing_airports.py <bounding_geojson_path>")
        sys.exit(1)

    bounding_geojson_path = sys.argv[1]

    main(bounding_geojson_path)

