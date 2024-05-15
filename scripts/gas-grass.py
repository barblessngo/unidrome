import pandas as pd
import overpass
import geopandas as gpd
from shapely.geometry import Point

faa_airports = pd.read_csv("data/us/faa/nasr/APT_BASE.csv", low_memory=False)
faa_runways = pd.read_csv("data/us/faa/nasr/APT_RWY.csv", low_memory=False)

grass = ['TURF', 'TURF-DIRT','TURF-GRVL','DIRT','GRVL-DIRT', 'GRAVEL','GRVL', 'DIRT-TRTD', 'TRTD-DIRT', 'DIRT-TURF', 'SAND', 'DIRT-GRVL','GRVL-TURF','TURF-SAND', 'SOD','GRASS']
only_grass = faa_runways[faa_runways["SURFACE_TYPE_CODE"].isin(grass)]
only_gas = faa_airports[faa_airports["FUEL_TYPES"].str.contains("100LL", na=False)]
                       #, "SITE_NO", "SITE_TYPE_CODE"]]
merged = pd.merge(only_grass, only_gas, on="SITE_NO")
geometry = [Point(xy) for xy in zip(merged['LONG_DECIMAL'], merged['LAT_DECIMAL'])]

osm_grass = ['unpaved', 'gravel', 'dirt', 'grass', 'compacted', 'sand', 'find_gravel', 'earth', 'dirt/sand']
surface_pattern = '|'.join(osm_grass)

api = overpass.API()

# Define the Overpass query to get centroids of runways with specified surfaces within the United States
query = f"""
[out:json];
area["ISO3166-1"="US"]->.searchArea;
way["aeroway"="runway"]["surface"~"{surface_pattern}"](area.searchArea);
out center;
"""

response = api.get(query)
# Parse the response to extract relevant data
runways = []
for element in response['elements']:
    if element['type'] == 'way' and 'center' in element:
        runway_id = element['id']
        surface = element['tags'].get('surface', 'unknown')
        center = element['center']
        latitude = center['lat']
        longitude = center['lon']
        runways.append({'id': runway_id, 'surface': surface, 'latitude': latitude, 'longitude': longitude})

df_runways = pd.DataFrame(runways)
print(df_runways)


#gdf = gpd.GeoDataFrame(merged, geometry=geometry)
#print(gdf)
#gdf.to_file('output.geojson', driver='GeoJSON')
