#!/bin/bash -ex

#python scripts/overpass-osm.py
python scripts/gas-grass.py
python scripts/google-places.py
cd data/content-pack 
rm -f barbless-maps.zip
zip -r barbless-maps barbless-maps
cd -
rclone copy data/content-pack/barbless-maps.zip vue-barbless:vue-barbless/content-packs/
