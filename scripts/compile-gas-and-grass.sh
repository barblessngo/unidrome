#!/bin/bash -ex

python scripts/gas-grass.py
mv final_gdf.geojson data/content-pack/barbless-maps/layers/Gas\ and\ Grass.geojson
cd data/content-pack 
rm -f barbless-maps.zip
zip -r barbless-maps barbless-maps
cd -
rclone copy data/content-pack/barbless-maps.zip vue-barbless:vue-barbless/content-packs/
