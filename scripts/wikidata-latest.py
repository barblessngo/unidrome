import requests
import os
import csv

class Wikidata:
    QUERY_ENDPOINT = "https://query.wikidata.org/sparql"
    QUERY = """
    SELECT ?airport (MIN(?name) as ?minName) (MIN(?ele) AS ?minEle) (MIN(?runway) AS ?minRunway) (MIN(?icao) AS ?minICAO) (MIN(?iata) AS ?minIATA) (MIN(?website) AS ?minWebsite) (MIN(?coord) AS ?minCoord) (MIN(?osm) AS ?minOSM)
    WHERE {
      ?airport wdt:P31 wd:Q1248784;  # Instances of airports
               rdfs:label ?name.      # Airport name

      OPTIONAL { ?airport wdt:P2044 ?ele. }             # Elevation
      OPTIONAL { ?airport wdt:P529 ?runway. }           # Runway
      OPTIONAL { ?airport wdt:P239 ?icao. }             # ICAO code
      OPTIONAL { ?airport wdt:P238 ?iata. }             # IATA code
      OPTIONAL { ?airport wdt:P856 ?website. }          # Official website
      ?airport wdt:P625 ?coord.                         # Coordinates
      OPTIONAL { ?airport wdt:P11693 ?osm. }            # OSM link
      FILTER (LANG(?name) = "en")                       # Filter for English labels
      BIND(STR(?coord) AS ?wkt_string)
      FILTER(STRSTARTS(?wkt_string, "Point("))          # Check if ?coord starts with "Point("
    }
    GROUP BY ?airport
    """

    @staticmethod
    def fetch_data():
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/sparql-results+json"
        }
        params = {
            "query": Wikidata.QUERY,
            "format": "json"
        }
        try:
            response = requests.get(Wikidata.QUERY_ENDPOINT, headers=headers, params=params)
            response.raise_for_status()  # Raises an HTTPError for bad responses
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching data: {e}")
            return None

    @staticmethod
    def save_csv(data, filename):
        if data:
            fields = data['head']['vars']
            fields.extend(['LAT', 'LON'])  # Add latitude and longitude fields
            fields.remove('minCoord')  # Remove the original coordinate field

            rows = []
            for result in data['results']['bindings']:
                row = [result.get(field, {}).get('value', '') for field in fields if field not in ['LAT', 'LON']]
                coord = result.get('minCoord', {}).get('value', 'Point(0 0)')
                lon, lat = Wikidata.parse_point(coord)
                row.append(lat)
                row.append(lon)
                rows.append(row)

            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(fields)  # headers
                csvwriter.writerows(rows)
            print(f"Data successfully saved to {filename}")
        else:
            print("No data to save.")

    @staticmethod
    def parse_point(point_str):
        # Example: 'Point(-0.123 51.456)' -> ['51.456', '-0.123']
        point_clean = point_str.strip('Point()')
        lon, lat = point_clean.split()
        return lat, lon

if __name__ == "__main__":
    data = Wikidata.fetch_data()
    if data:
        Wikidata.save_csv(data, os.path.join('data', 'world', 'wikidata', 'airports.csv'))
    else:
        print("Failed to fetch or save data.")

