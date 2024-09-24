import overpy
import argparse
import pickle
import os
import csv

parser = argparse.ArgumentParser(description='Toggle cache usage')
parser.add_argument('--use-cache', action='store_true', help='Use cache if set')
args = parser.parse_args()
use_cache = args.use_cache

# Define the Overpass API
api = overpy.Overpass(url='https://overpass.private.coffee/api/interpreter')

for aeroway in ["runway", "aerodrome"]: 
    # Check if pickle file exists
    pickle_file = f"overpass-osm-{aeroway}.pickle"
    if use_cache and os.path.exists(pickle_file):
        # Unpickle the response
        with open(pickle_file, "rb") as f:
            result = pickle.load(f)
    else:
        # Create an Overpass API object
        api = overpy.Overpass()

        # Define the Overpass query to get runways with specified surfaces within the United States
        query = f"""
        (
          nw["aeroway"="{aeroway}"];
          nw["disused:aeroway"="{aeroway}"];
          nw["abandoned:aeroway"="{aeroway}"];
        );
        out center;
        """

        # Execute the query
        result = api.query(query)

        # Pickle the response
        with open(pickle_file, "wb") as f:
            pickle.dump(result, f)

    headers = ["id", "latitude", "longitude"]

    with open(f"data/world/osm/top-{aeroway}.txt", "r") as file:
        headers.extend([line.strip() for line in file.readlines()])

    # Create a CSV file with these headers
    with open(f"data/world/osm/overpass/{aeroway}.csv", "w", newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()

        for node in result.nodes:
            # Prepare the row data
            row_data = {
                'id': node.id,
                'latitude': float(node.lat),
                'longitude': float(node.lon)
            }
            update_tags = {}
            for tag in node.tags:
                if tag in headers and tag not in row_data:
                    update_tags[tag] = node.tags[tag]
            # Add tags data
            row_data.update(update_tags)
            # Write the row to CSV
            writer.writerow(row_data)

        for way in result.ways:
            # Prepare the row data
            row_data = {
                'id': way.id,
                'latitude': float(way.center_lat),
                'longitude': float(way.center_lon)
            }
            update_tags = {}
            for tag in way.tags:
                if tag in headers and tag not in row_data:
                    update_tags[tag] = way.tags[tag]
            # Add tags data
            row_data.update(update_tags)
            # Write the row to CSV
            writer.writerow(row_data)

