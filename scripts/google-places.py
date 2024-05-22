import os
import pickle
import geopandas as gpd
import pandas as pd
import googlemaps
import hashlib
from lon_lat_lookup_gen import get_gdf
from content_pack import gdf_to_kmz_with_bundled_icons
import pprint
from shapely.geometry import Point

from dotenv import load_dotenv
load_dotenv()

gmaps = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))
types_map = {
    "lodging": "Lodging",
    "restaurant": "Restaurants",
}

# Function to convert geometry to latitude/longitude
def pt_to_ll(geometry):
    return geometry.y, geometry.x

# Function to create a unique filename based on parameters
def create_pickle_filename(lat, lon, radius, place_type):
    params_str = f"{lat}_{lon}_{radius}_{place_type}"
    return f"cache/places_nearby_{params_str}.pkl"

# Function to get nearby places and use pickle to save/load the response
def get_nearby(df, radius, place_type):
    lat, lon = pt_to_ll(df.geometry)
    pickle_file = create_pickle_filename(lat, lon, radius, place_type)

    if os.path.exists(pickle_file):
        with open(pickle_file, 'rb') as f:
            response = pickle.load(f)
    else:
        response = gmaps.places_nearby(location=(lat, lon), radius=radius, type=place_type)
        with open(pickle_file, 'wb') as f:
            pickle.dump(response, f)

    results = response['results']
    nearby_places = pd.DataFrame(results)



    # Add the original row information to each result
    return nearby_places

def clean_gdf(gdf):
    for col in gdf.columns:
        if gdf[col].apply(lambda x: isinstance(x, list)).any():
            gdf[col] = gdf[col].apply(lambda x: ', '.join(map(str, x)) if isinstance(x, list) else x)
    return gdf

def create_description(row):
    map_url = ""

    place_id = row.get('place_id', None)
    if not place_id:
        return None

    lng,lat = row.geometry.xy

    map_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
    map_url = f"https://www.google.com/maps/search/?api=1&query={lng},{lat}&query_place_id={place_id}"
    description = f'<h1><p><a href="{map_url}" target="_blank">View on Google Maps</a></p></h1>'
    row['description'] = description
    return row


faa = get_gdf('data/us/faa/nasr/APT_BASE.csv')
faa = faa[faa["STATE_CODE"].isin(["OR", "NV", "NM", "ID", "AZ", "CA", "UT", "WA", "TX", "CO", "WY", "MT"])]
airports = faa[faa["SITE_TYPE_CODE"] == "A"]
place_types = ["restaurant", "lodging"]
for place_type in place_types:
    results = airports.apply(get_nearby, axis=1, args=(2000, place_type))
    nearby_places = pd.concat(results.tolist(), ignore_index=True)
    nearby_places = nearby_places[nearby_places['geometry'].notnull()]
    geometry = [Point(xy['location']['lng'], xy['location']['lat']) for xy in nearby_places['geometry']]
    gdf = gpd.GeoDataFrame(nearby_places, geometry=geometry)
    gdf = gdf[gdf["business_status"] == "OPERATIONAL"]
    gdf = clean_gdf(gdf)
    gdf = gdf.apply(create_description, axis=1)

    icon_path = f"icons/{place_type}_11.png"
    gdf["icon_path"] = icon_path

    kmz_name = types_map[place_type]
    gdf_to_kmz_with_bundled_icons(gdf, f"data/content-pack/barbless-maps/layers/{kmz_name}.kmz")
    #gdf.to_file("nearby.gpkg", layer=place_type, driver="GPKG")
