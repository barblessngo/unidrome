from shapely.geometry import Point
import pandas as pd
import geopandas as gpd

lon_lat_lookup = {
    'data/us/faa/nasr/APT_BASE.csv': lambda row: Point(float(row.iloc[24]), float(row.iloc[19])) if row.iloc[19] and row.iloc[24] else None,
    #'data/world/ourairports/runways.csv': lambda row: Point(float(row.iloc[10]), float(row.iloc[9])) if row.iloc[9] and row.iloc[10] else None,
    'data/world/ourairports/airports.csv': lambda row: Point(float(row.iloc[5]), float(row.iloc[4])),
    #'data/world/osm/daylight/runway.csv': lambda row: Point(float(row.iloc[2]), float(row.iloc[1])),
    'data/world/osm/daylight/aerodrome.csv': lambda row: Point(float(row.iloc[2]), float(row.iloc[1])),
    'data/world/wikidata/airports.csv': lambda row: Point(float(row.iloc[8]), float(row.iloc[9])),
}

def get_gdf(file_path):
    # Read the CSV file into a DataFrame
    df = pd.read_csv(file_path, low_memory=False)
    
    # Apply the lambda function to each row
    df['geometry'] = df.apply(lon_lat_lookup[file_path], axis=1)
    df = df.dropna(subset=['geometry'])
    gfd = gpd.GeoDataFrame(df)
    
    return gfd

def get_all_gdfs():
    gdfs = {}
    for file in lon_lat_lookup:
        func = lon_lat_lookup.get(file)
        if func:
            gdfs[file] = get_gdf(file)
    return gdfs
