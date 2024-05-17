import pandas as pd
import geopandas as gpd
import os
from shapely.geometry import Point

def load_csv_as_gdf(filepath):
    df = pd.read_csv(filepath)
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat))
    gdf.set_crs("EPSG:4326", inplace=True)
    gdf = gdf.to_crs("EPSG:3857")
    return gdf

def rename_conflicting_columns(gdf):
    # Rename 'index_left' and 'index_right' if they exist in the dataframe
    if 'index_left' in gdf.columns:
        gdf.rename(columns={'index_left': 'index_left_old'}, inplace=True)
    if 'index_right' in gdf.columns:
        gdf.rename(columns={'index_right': 'index_right_old'}, inplace=True)
    for col in ['id_left', 'lon_left', 'buffered_geometry_left', 'lat_left']:
        if col in gdf.columns:
            gdf.drop(columns=[col], inplace=True)

    return gdf

root_directory = 'data/world'
geo_dataframes = []

for dirpath, dirnames, filenames in os.walk(root_directory):
    for filename in filenames:
        if filename.endswith('.csv'):
            file_path = os.path.join(dirpath, filename)
            gdf = load_csv_as_gdf(file_path)
            gdf = rename_conflicting_columns(gdf)
            geo_dataframes.append(gdf)

# Assuming all GeoDataFrames are now in all_gdfs list
# Define a buffer distance for proximity-based merging (e.g., 500 meters)
buffer_distance = 500  # distance in meters

final_merged_gdf = None

for i, gdf in enumerate(geo_dataframes):
    gdf['buffered_geometry'] = gdf.geometry.buffer(buffer_distance)
    if final_merged_gdf is None:
        final_merged_gdf = gdf
    else:
        # Perform spatial join with unique suffixes
        final_merged_gdf = gpd.sjoin(final_merged_gdf, gdf, how='inner', predicate='intersects')
        breakpoint()
        final_merged_gdf = rename_conflicting_columns(final_merged_gdf)
        # Clean up columns by dropping or renaming

aggregated_data = final_merged_gdf.groupby('geometry').agg(lambda x: x.iloc[0]).reset_index()

# Convert back to a non-geo DataFrame if only tabular data is needed
final_merged_df = pd.DataFrame(aggregated_data.drop(columns='geometry'))

# Save the merged and aggregated DataFrame to a new CSV file
final_merged_df.to_csv('data/merged.csv', index=False)

print("Merged and aggregated CSV saved successfully in 'data/merged.csv'.")
