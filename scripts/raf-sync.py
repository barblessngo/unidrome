import requests
import json
import argparse
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import os
import ast
from content_pack import gdf_to_kmz_with_bundled_icons, series_to_html_table

def fetch_all_airports(base_url, headers):
    all_airports = []
    offset = 0
    limit = 50
    total = 1 # Initialize with a non-zero value to enter the loop

    while offset < total:
        response = requests.get(f"{base_url}&offset={offset}", headers=headers)
        if response.status_code == 200:
            data = response.json()
            total = data['metadata']['total']
            all_airports.extend(data['results'])
            offset += limit
        else:
            print(f"Failed to retrieve data: {response.status_code}")
            break

    return all_airports

def fetch_airport_overview(airport_id, headers):
    overview_url = f"https://api.guide.theraf.org/api/v1.0/airports/{airport_id}/overview"
    response = requests.get(overview_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to retrieve overview for airport {airport_id}: {response.status_code}")
        return {}

def fetch_airport_comments(airport_id, headers):
    comments_url = f"https://api.guide.theraf.org/api/v1.0/airports/{airport_id}/comments/directional-runways"
    response = requests.get(comments_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to retrieve comments for airport {airport_id}: {response.status_code}")
        return []

def fetch_airport_amenities(airport_id, headers):
    amenities_url = f"https://api.guide.theraf.org/api/v1.0/airports/{airport_id}/amenities"
    response = requests.get(amenities_url, headers=headers)
    if response.status_code == 200:
        return response.json().get('amenities', [])
    else:
        print(f"Failed to retrieve amenities for airport {airport_id}: {response.status_code}")
        return []

def fetch_airport_runways(airport_id, headers):
    runways_url = f"https://api.guide.theraf.org/api/v1.0/airports/{airport_id}/runways"
    response = requests.get(runways_url, headers=headers)
    if response.status_code == 200:
        return response.json().get('runways', [])
    else:
        print(f"Failed to retrieve runways for airport {airport_id}: {response.status_code}")
        return []

def fetch_airport_media(airport_id, headers):
    media_url = f"https://api.guide.theraf.org/api/v1.0/airports/{airport_id}/media/all?limit=20&offset=0&total=0"
    all_media = []
    offset = 0
    limit = 20
    total = 1  # Initialize with a non-zero value to enter the loop

    while offset < total:
        response = requests.get(f"{media_url}&offset={offset}", headers=headers)
        if response.status_code == 200:
            data = response.json()
            total = data['metadata']['total']
            all_media.extend(data['results'])
            offset += limit
        else:
            print(f"Failed to retrieve media for airport {airport_id}: {response.status_code}")
            break

    return all_media

def parse_coord(row):
    coord = row["coordinates"]
    lng = coord['lng']['decimal']
    lat  = coord['lat']['decimal']
    row["geometry"] = Point((lng,lat))
    row.drop("coordinates")
    return row

def parse_notes(row):
    d = row["notes"]
    row["note_alerts"] = "<br/>".join([str(n["text"]) for n in d["alert"] ])
    row["note_default"] = "<br/>".join([str(n["text"]) for n in d["default"] ])
    row.drop("notes")
    return row

def parse_name(row):
    row["name"] = row["title"]
    return row

def add_icon(row):
    row["icon_path"] = f"icons/raf-{row['visitType']}.png"
    return row

def add_description(row):
    columns = [
            "name", 
            "number", 
            "visitType",
            "elevation",
            "longestRunway",
            "lastSurveyedDate",
            "communicationFrequency",
            "timeZone",
            "note_alerts",
            "note_default"
    ]
    row["description"] = series_to_html_table(row, columns=columns )
    return row

def parse_df(df):
    df = df.apply(parse_coord, axis=1)
    df = df.apply(parse_notes, axis=1)
    df = df.apply(parse_name, axis=1)
    df = df.apply(add_icon, axis=1)
    df = df.apply(add_description, axis=1)
    gdf = gpd.GeoDataFrame(df, geometry=df["geometry"], crs='EPSG:4326')
    return gdf

def save_to_csv(data, filename):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download airport data with a bearer token, ie 'Bearer 1234...'.")
    parser.add_argument('--bearer_token', type=str, help="Bearer token for authentication", required=False)
    parser.add_argument('--file', type=str, help="pre-downloaded file with the data", required=False)
    args = parser.parse_args()

    headers = {
        'Authorization': f'{args.bearer_token}'
    }

    base_url = "https://api.guide.theraf.org/api/v1.0/airports?limit=50&total=0"
    airports_data = fetch_all_airports(base_url, headers)

    detailed_airports_data = []
    for airport in airports_data:
        airport_id = airport['id']
        overview_data = fetch_airport_overview(airport_id, headers)
        #comments_data = fetch_airport_comments(airport_id, headers)
        #amenities_data = fetch_airport_amenities(airport_id, headers)
        #runways_data = fetch_airport_runways(airport_id, headers)
        #media_data = fetch_airport_media(airport_id, headers)

        combined_data = {
            **airport,
            **overview_data,
        #    "comments": comments_data,
        #    "amenities": amenities_data,
        #    "runways": runways_data,
        #    "media": media_data
        }
        detailed_airports_data.append(combined_data)

    df = pd.DataFrame(detailed_airports_data)

    gdf = parse_df(df)
    gdf_to_kmz_with_bundled_icons(gdf, f"data/content-pack/barbless-maps/layers/RAF Airfield Guide.kmz")
    gdf.to_csv('data/us/raf/airfields.csv')
