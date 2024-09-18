# Updated Python Script to Find Airports from OurAirports Not in Daylight Aerodrome Dataset
# Excluding airports where type == 'closed' or type == 'heliport'
# Added 'osm_editor_link' attribute for each missing airport

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# Step 1: Load and Filter the OurAirports Data
# ---------------------------------------------
# Load OurAirports data
ourairports_df = pd.read_csv('data/world/ourairports/airports.csv')

# Exclude airports where type == 'closed' or type == 'heliport'
exclude_types = ['closed', 'heliport']
ourairports_df = ourairports_df[~ourairports_df['type'].isin(exclude_types)]

# Drop rows with missing latitude or longitude
ourairports_df = ourairports_df.dropna(subset=['latitude_deg', 'longitude_deg'])

# Step 2: Load the Daylight Aerodrome Data
# ----------------------------------------
# Load Daylight aerodrome data
daylight_df = pd.read_csv('data/world/osm/daylight/aerodrome.csv')

# Drop rows with missing latitude or longitude
daylight_df = daylight_df.dropna(subset=['latitude', 'longitude'])

# Step 3: Convert DataFrames to GeoDataFrames
# -------------------------------------------
# Create geometries for OurAirports
ourairports_geometry = [Point(xy) for xy in zip(ourairports_df['longitude_deg'], ourairports_df['latitude_deg'])]
ourairports_gdf = gpd.GeoDataFrame(ourairports_df, geometry=ourairports_geometry, crs='EPSG:4326')

# Create geometries for Daylight
daylight_geometry = [Point(xy) for xy in zip(daylight_df['longitude'], daylight_df['latitude'])]
daylight_gdf = gpd.GeoDataFrame(daylight_df, geometry=daylight_geometry, crs='EPSG:4326')

# Step 4: Perform Spatial Join
# ----------------------------
# Project to a metric CRS (EPSG:3857) for accurate distance measurements
ourairports_gdf = ourairports_gdf.to_crs('EPSG:3857')
daylight_gdf = daylight_gdf.to_crs('EPSG:3857')

# Create a buffer around OurAirports points (e.g., 1000 meters)
ourairports_gdf['geometry_buffer'] = ourairports_gdf.geometry.buffer(1000)  # Buffer of 1000 meters

# Use the buffered geometry for spatial join
ourairports_gdf_buffered = ourairports_gdf.set_geometry('geometry_buffer')

# Prepare the Daylight GeoDataFrame for spatial join
daylight_gdf_sjoin = daylight_gdf[['geometry']].copy()

# Perform spatial join to find matching airports
joined_gdf = gpd.sjoin(
    ourairports_gdf_buffered,
    daylight_gdf_sjoin,
    how='left',
    predicate='intersects'  # Updated parameter name
)

# Identify airports not in Daylight (NaN in 'index_right' indicates no match)
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

# Export to GeoPackage
missing_airports_gdf.to_file('missing_airports.gpkg', layer='missing_airports', driver='GPKG')

print("Exported missing airports to 'missing_airports.gpkg' with 'osm_editor_link' attribute.")

