#!/usr/bin/env python3
"""
Updated Python Script to Find Airports from OurAirports Not in overpass Aerodrome or Runway Dataset
Excluding airports where type == 'closed' or type == 'heliport'
Optionally excluding airports that cannot be seen from imagery (controlled by a flag)
Added 'osm_editor_link' attribute for each missing airport

Usage:
    python find_missing_airports.py [--exclude-unable-to-see]
"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import argparse
import sys

def main(exclude_unable_to_see):
    # Step 1: Load and Filter the OurAirports Data
    # ---------------------------------------------
    # Load OurAirports data
    ourairports_df = pd.read_csv('data/world/ourairports/airports.csv')

    # Exclude airports where type == 'closed' or type == 'heliport'
    exclude_types = ['closed', 'heliport', 'seaplane_base']
    ourairports_df = ourairports_df[~ourairports_df['type'].isin(exclude_types)]

    # Drop rows with missing latitude or longitude
    ourairports_df = ourairports_df.dropna(subset=['latitude_deg', 'longitude_deg'])

    # Step 1.5: Optionally Exclude Airports Unable to Be Seen in Imagery
    # ------------------------------------------------------------------
    if exclude_unable_to_see:
        # Load the list of airports that cannot be seen from imagery
        unable_to_see_csv = 'data/world/ourairports/unable-to-be-seen-in-osm-imagery.csv'
        try:
            unable_to_see_df = pd.read_csv(unable_to_see_csv)
        except FileNotFoundError:
            print(f"Error: Unable to find '{unable_to_see_csv}' for exclusion.")
            sys.exit(1)

        # Ensure the 'id' column exists in both DataFrames
        if 'id' not in ourairports_df.columns or 'id' not in unable_to_see_df.columns:
            raise ValueError("Both OurAirports data and unable-to-be-seen CSV must contain an 'id' column.")

        # Exclude airports in unable_to_see_df from ourairports_df
        ourairports_df = ourairports_df[~ourairports_df['id'].isin(unable_to_see_df['id'])]

    # Step 2: Load the overpass Aerodrome Data
    # ----------------------------------------
    # Load overpass aerodrome data
    overpass_df = pd.read_csv('data/world/osm/overpass/aerodrome.csv', low_memory=False)

    # Drop rows with missing latitude or longitude
    overpass_df = overpass_df.dropna(subset=['latitude', 'longitude'])

    # Step 2.5: Load and Process the Runway Data
    # ------------------------------------------
    # Load runway data
    runway_df = pd.read_csv('data/world/osm/overpass/runway.csv', low_memory=False)

    # Drop rows with missing latitude or longitude
    runway_df = runway_df.dropna(subset=['latitude', 'longitude'])

    # Step 3: Convert DataFrames to GeoDataFrames
    # -------------------------------------------
    # Create geometries for OurAirports
    ourairports_geometry = [Point(xy) for xy in zip(ourairports_df['longitude_deg'], ourairports_df['latitude_deg'])]
    ourairports_gdf = gpd.GeoDataFrame(ourairports_df, geometry=ourairports_geometry, crs='EPSG:4326')

    # Create geometries for overpass aerodrome
    overpass_geometry = [Point(xy) for xy in zip(overpass_df['longitude'], overpass_df['latitude'])]
    overpass_gdf = gpd.GeoDataFrame(overpass_df, geometry=overpass_geometry, crs='EPSG:4326')

    # Create geometries for runway
    runway_geometry = [Point(xy) for xy in zip(runway_df['longitude'], runway_df['latitude'])]
    runway_gdf = gpd.GeoDataFrame(runway_df, geometry=runway_geometry, crs='EPSG:4326')

    # Step 4: Perform Spatial Join
    # ----------------------------
    # Project all GeoDataFrames to a metric CRS (EPSG:3857) for accurate distance measurements
    ourairports_gdf = ourairports_gdf.to_crs('EPSG:3857')
    overpass_gdf = overpass_gdf.to_crs('EPSG:3857')
    runway_gdf = runway_gdf.to_crs('EPSG:3857')

    # Combine overpass aerodrome and runway GeoDataFrames
    combined_gdf = pd.concat([overpass_gdf, runway_gdf], ignore_index=True)

    # Create a buffer around OurAirports points (e.g., 1000 meters)
    ourairports_gdf['geometry_buffer'] = ourairports_gdf.geometry.buffer(1000)  # Buffer of 1000 meters

    # Use the buffered geometry for spatial join
    ourairports_gdf_buffered = ourairports_gdf.set_geometry('geometry_buffer')

    # Prepare the combined GeoDataFrame for spatial join
    combined_gdf_sjoin = combined_gdf[['geometry']].copy()

    # Perform spatial join to find matching airports
    joined_gdf = gpd.sjoin(
        ourairports_gdf_buffered,
        combined_gdf_sjoin,
        how='left',
        predicate='intersects'
    )

    # Identify airports not in overpass or runway data (NaN in 'index_right' indicates no match)
    missing_airports_gdf = joined_gdf[joined_gdf['index_right'].isna()]

    # Step 5: Clean Up and Add OSM Editor Link
    # ----------------------------------------
    # Reset geometry to the original points (not the buffer)
    missing_airports_gdf = missing_airports_gdf.set_geometry('geometry')

    # Reproject back to EPSG:4326 (WGS84)
    missing_airports_gdf = missing_airports_gdf.to_crs('EPSG:4326')

    # Add 'osm_editor_link' attribute
    missing_airports_gdf['osm_editor_link'] = missing_airports_gdf.apply(
        lambda row: f"https://www.openstreetmap.org/edit?editor=id#map=18/{row.geometry.y:.6f}/{row.geometry.x:.6f}",
        axis=1
    )

    # Remove unnecessary columns (keep original columns, geometry, and 'osm_editor_link')
    columns_to_keep = ourairports_df.columns.tolist() + ['geometry', 'osm_editor_link']
    missing_airports_gdf = missing_airports_gdf[columns_to_keep]

    # Export to CSV
    missing_airports_gdf.to_csv('data/world/osm/overpass/missing_from_ourairports.csv', index=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Find missing airports from OurAirports data.')
    parser.add_argument('--exclude-unable-to-see', action='store_true',
                        help='Exclude airports listed in unable-to-be-seen-in-osm-imagery.csv')
    args = parser.parse_args()

    main(exclude_unable_to_see=args.exclude_unable_to_see)

