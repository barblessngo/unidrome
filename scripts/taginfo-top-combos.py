import requests

tags = {
    'aerodrome': 'https://taginfo.openstreetmap.org/api/4/tag/combinations?key=aeroway&value=aerodrome&filter=all&sortname=to_count&sortorder=desc',
    'runway': 'https://taginfo.openstreetmap.org/api/4/tag/combinations?key=aeroway&value=runway&filter=all&sortname=to_count&sortorder=desc'
}


for tag in tags.keys():
    # Perform a GET request to fetch the data
    response = requests.get(tags[tag])
    data = response.json()

    # Extracting the 'other_key' from each item in the 'data' list
    other_keys = set([item["other_key"] for item in data["data"]])

    # Save the 'other_keys' to a text file, one per line
    with open(f"data/world/osm/top-{tag}.txt", "w") as file:
        for key in other_keys:
            file.write(key + "\n")
