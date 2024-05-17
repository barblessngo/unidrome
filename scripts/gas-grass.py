import pandas as pd
import overpy
import geopandas as gpd
from shapely.geometry import Point
import os


# Define the list of surfaces for Overpass query
osm_grass = ['unpaved', 'gravel', 'dirt', 'grass', 'compacted', 'sand', 'find_gravel', 'earth', 'dirt/sand']
osm_runways = pd.read_csv("data/world/osm/overpass/runway.csv", low_memory=False)
osm_runways = osm_runways[osm_runways["surface"].isin(osm_grass)]

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
geometry = [Point(xy) for xy in zip(osm_runways['longitude'], osm_runways['latitude'])]
osm_only_grass_gfd = gpd.GeoDataFrame(osm_runways, geometry=geometry, crs='EPSG:4326')

geometry = [Point(xy) for xy in zip(only_gas['LONG_DECIMAL'], only_gas['LAT_DECIMAL'])]
only_gas_gdf = gpd.GeoDataFrame(only_gas, geometry=geometry, crs='EPSG:4326')

# Create a buffer around the grass runways from OSM
buffer_distance = .02 
osm_only_grass_gfd_projected = osm_only_grass_gfd.to_crs('EPSG:4326')
osm_only_grass_gfd_buffer = osm_only_grass_gfd_projected.buffer(buffer_distance)
osm_only_grass_gfd_buffer = gpd.GeoDataFrame(osm_only_grass_gfd, geometry=osm_only_grass_gfd_buffer)
#osm_only_grass_gfd_buffer.to_file('osm_only_grass_gfd_buffer.geojson', driver='GeoJSON')
#only_gas_gdf.to_file('only_gas_gdf.geojson', driver='GeoJSON')

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
