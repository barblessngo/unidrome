OUT=/tmp/out
PMTILES=${OUT}.pmtiles
GEOJSONL=${OUT}.geojsonl

ogr2ogr -f GeoJSONSeq ${OUT}.geojsonl PG:"dbname=unidrome" clustered_osm &&
tippecanoe \
	--quiet \
	--read-parallel \
	-zg \
	-o ${PMTILES} \
	--coalesce-densest-as-needed \
	--extend-zooms-if-still-dropping \
	-l aerodrome \
	--force \
	${GEOJSONL}

rm ${OUT}.geojsonl
echo ${OUT}.pmtiles

