```
python3 -v venv .venv
pip install -r requirements.txt

# hit scripts/*-latest.py files to update latest from that source
```

## Example find missing airports that are in ourairports.com but not OSM latest

```
# updates data/world/ourairports/airports.csv to latest
python scripts/ourairports-latest.py
# updates data/world/osm/overpass/aerodrome.csv to latest OSM
python scripts/overpass-latest.py
# runs the comparison and outputs to data/world/osm/overpass/missing_from_ourairports.csv 
python scripts/missing-from-ourairports.py

# how many are missing 
wc -l data/world/osm/overpass/missing_from_ourairports.csv 
    8765 data/world/osm/overpass/missing_from_ourairports.csv

```

