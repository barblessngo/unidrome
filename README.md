```
python3 -v venv .venv
pip install -r requirements.txt

# hit scripts/*-latest.py files to update latest from that source
```

## Example find missing airports that are in ourairports.com but not daylight latest

```
# updates data/world/ourairports/airports.csv to latest
python3 scripts/ourairports-latest.py
# updates data/world/osm/daylight/aerodrome.csv to latest daylight
python3 scripts/daylight-latest.py
# runs the comparison and outputs to data/world/osm/daylight/missing_from_ourairports.csv 
python3 scripts/missing-from-ourairports.py

# 14k airports in ourairports that are not in daylight
$ wc -l data/world/osm/daylight/missing_from_ourairports.csv 
   14132 data/world/osm/daylight/missing_from_ourairports.csv

```

