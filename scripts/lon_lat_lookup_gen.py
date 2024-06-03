from shapely.geometry import Point
import pandas as pd
import geopandas as gpd

class AerodromeParser():

    def parse_geom(row):
        return None

    def is_airport(row):
        return False

    def is_heliport(row):
        return False

    def is_active(row):
        return True

class MxParser(AerodromeParser):
    def parse_geom(row):
        try:
            if pd.isna(row.iloc[11]):
                return None
            latitude_deg = float(row.iloc[11])
            latitude_min = float(row.iloc[12])
            latitude_sec = float(row.iloc[13])

            longitude_deg = float(row.iloc[14])
            longitude_min = float(row.iloc[15])
            longitude_sec = float(row.iloc[16])
            latitude = latitude_deg + latitude_min/60 + latitude_sec/3600
            longitude = -1 * (longitude_deg + longitude_min/60 + longitude_sec/3600)
            return Point(longitude, latitude)
        # if it cannot parse a float, return none
        except ValueError:
            return None

    def is_airport(row):
        return row['TIPO AERÓDROMO'] == 'AERÓDROMO'

    def is_heliport(row):
        return row['NO. DE EXPEDIENTE'][:2] == 'HP' or row['TIPO AERÓDROMO'] == 'HELIPUERTO'

class FAAParser(AerodromeParser):
    def parse_geom(row):
        return Point(float(row.iloc[24]), float(row.iloc[19])) if row.iloc[19] and row.iloc[24] else None

    def is_airport(row):
        return row['SITE_TYPE_CODE'] != 'H'

    def is_heliport(row):
        return row['SITE_TYPE_CODE'] == 'H'

    def is_active(row):
        return True

class OurAirportsParser(AerodromeParser):
    def parse_geom(row):
        return Point(float(row.iloc[5]), float(row.iloc[4]))

    def is_airport(row):
        return row['type'].find('airport') != -1

    def is_heliport(row):
        return row['type'] == 'heliport'

    def is_active(row):
        return row['type'] != 'closed'

class OSMDaylightParser(AerodromeParser):
    def parse_geom(row):
        return Point(float(row.iloc[2]), float(row.iloc[1]))

    def is_airport(row):
        if pd.isna(row['name']):
            return True
        return row['name'].find('heliport') == -1

    def is_heliport(row):
        if pd.isna(row['name']):
            return True
        return row['name'].find('heliport') != -1


lon_lat_lookup = {
    'data/mx/afac/aerodromos.csv': MxParser,
    'data/us/faa/nasr/APT_BASE.csv': FAAParser,
    ##'data/world/ourairports/runways.csv': lambda row: Point(float(row.iloc[10]), float(row.iloc[9])) if row.iloc[9] and row.iloc[10] else None,
    'data/world/ourairports/airports.csv': OurAirportsParser,
    ##'data/world/osm/daylight/runway.csv': lambda row: Point(float(row.iloc[2]), float(row.iloc[1])),
    'data/world/osm/daylight/aerodrome.csv': OSMDaylightParser,
    #'data/world/wikidata/airports.csv': lambda row: Point(float(row.iloc[8]), float(row.iloc[9])),
}


def get_gdf(file_path):
    # Read the CSV file into a DataFrame
    df = pd.read_csv(file_path, low_memory=False)
    
    parser = lon_lat_lookup[file_path]
    # Apply the lambda function to each row
    df['geometry'] = df.apply(parser.parse_geom, axis=1)
    df = df.dropna(subset=['geometry'])
    df['_is_airport'] = df.apply(parser.is_airport, axis=1)
    df['_is_heliport'] = df.apply(parser.is_heliport, axis=1)
    df['_is_active'] = df.apply(parser.is_active, axis=1)
    gdf = gpd.GeoDataFrame(df)
    
    return gdf

def get_all_gdfs():
    gdfs = {}
    for file in lon_lat_lookup:
        func = lon_lat_lookup.get(file)
        if func:
            gdfs[file] = get_gdf(file)
    return gdfs
