import pandas as pd
import overpy
import geopandas as gpd
from shapely.geometry import Point
import os
import pickle
import argparse

parser = argparse.ArgumentParser(description='Toggle cache usage')
parser.add_argument('--use-cache', action='store_true', help='Use cache if set')
args = parser.parse_args()
use_cache = args.use_cache


# Define the Overpass API
api = overpy.Overpass(url='https://overpass.kumi.systems/api/interpreter')

# Define the list of surfaces for Overpass query
osm_grass = ['unpaved', 'gravel', 'dirt', 'grass', 'compacted', 'sand', 'find_gravel', 'earth', 'dirt/sand']
surface_pattern = '|'.join(osm_grass)

# Check if pickle file exists
pickle_file = "api_response.pickle"
if use_cache and os.path.exists(pickle_file):
    # Unpickle the response
    with open(pickle_file, "rb") as f:
        result = pickle.load(f)
else:
    # Create an Overpass API object
    api = overpy.Overpass()

    # Define the Overpass query to get runways with specified surfaces within the United States
    query = """
    area["ISO3166-1"="US"]->.searchArea;
    way["aeroway"="runway"]["surface"~"unpaved|gravel|dirt|grass|compacted|sand|fine_gravel|earth|dirt/sand"](area.searchArea);
    out center;
    """

    # Execute the query
    result = api.query(query)

    # Pickle the response
    with open(pickle_file, "wb") as f:
        pickle.dump(result, f)

# Parse the response to extract relevant data
runways = []
for way in result.ways:
    # Get the coordinates of the center of the way
    center_lon = way.center_lon
    center_lat = way.center_lat
    # Create a Point geometry
    point = Point(center_lon, center_lat)
    # Add relevant data to the runways list
    runways.append({'geometry': point, 'surface': way.tags.get('surface', 'unknown')})

# Read data
faa_airports = pd.read_csv("data/us/faa/nasr/APT_BASE.csv", low_memory=False)
faa_airports = faa_airports[faa_airports["SITE_TYPE_CODE"] == "A"]
faa_runways = pd.read_csv("data/us/faa/nasr/APT_RWY.csv", low_memory=False)

# Filter runways with grass surfaces
grass = ['TURF', 'TURF-DIRT', 'TURF-GRVL', 'DIRT', 'GRVL-DIRT', 'GRAVEL', 'GRVL', 'DIRT-TRTD', 'TRTD-DIRT',
         'DIRT-TURF', 'SAND', 'DIRT-GRVL', 'GRVL-TURF', 'TURF-SAND', 'SOD', 'GRASS']
only_grass = faa_runways[faa_runways["SURFACE_TYPE_CODE"].isin(grass)]

# Filter airports with 100LL fuel type
only_gas = faa_airports[faa_airports["FUEL_TYPES"].str.contains("100LL", na=False)]

# Create a GeoDataFrame from the runways list
osm_only_grass_gfd = gpd.GeoDataFrame(runways, crs='EPSG:4326')

geometry = [Point(xy) for xy in zip(only_gas['LONG_DECIMAL'], only_gas['LAT_DECIMAL'])]
only_gas_gdf = gpd.GeoDataFrame(only_gas, geometry=geometry, crs='EPSG:4326')

# Create a buffer around the grass runways from OSM
buffer_distance = .02 
osm_only_grass_gfd_projected = osm_only_grass_gfd.to_crs('EPSG:4326')
osm_only_grass_gfd_buffer = osm_only_grass_gfd_projected.buffer(buffer_distance)
osm_only_grass_gfd_buffer = gpd.GeoDataFrame(osm_only_grass_gfd, geometry=osm_only_grass_gfd_buffer)
osm_only_grass_gfd_buffer.to_file('osm_only_grass_gfd_buffer.geojson', driver='GeoJSON')
only_gas_gdf.to_file('only_gas_gdf.geojson', driver='GeoJSON')

# Perform a spatial join between only_gas_gdf and the buffered grass runways from OSM
intersection = only_gas_gdf.sjoin(osm_only_grass_gfd_buffer, predicate="intersects")

# Merge filtered DataFrames
faa_gas_grass = pd.merge(only_grass, only_gas_gdf, on="SITE_NO")
faa_gas_grass_gdf = gpd.GeoDataFrame(faa_gas_grass, geometry=faa_gas_grass["geometry"], crs='EPSG:4326')

final_gdf = pd.concat([faa_gas_grass_gdf, intersection])
final_gdf = final_gdf[["ARPT_ID", "ARPT_NAME", "geometry"]]
# dedupes where the FAA and OSM say there is a grass runway
final_gdf = final_gdf.dissolve(by=["ARPT_ID", "ARPT_NAME"])
#final_gdf = final_gdf.reset_index()
#final_gdf["Name"] = final_gdf.apply(lambda row: f"{row['ARPT_NAME']} ({row['ARPT_ID']})", axis=1)
final_gdf.to_file('final_gdf.geojson', driver='GeoJSON')
