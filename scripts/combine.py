from lon_lat_lookup_gen import lon_lat_lookup, get_all_gdfs
import geopandas as gpd
import pandas as pd
import h3pandas
from sklearn.cluster import DBSCAN
import numpy as np

gdfs = get_all_gdfs()
for file in gdfs:
    # filter out closed airports and heliports
    g = gdfs[file]
    airports = g[g['_is_airport'] == True]
    active = airports[airports['_is_active'] == True]
    gdfs[file] = active


prefixes = [ f"{k.replace('data/', '').replace('.csv', '').replace('/', '_').replace('.', '_')}_" for k in lon_lat_lookup ]
gdfs = [gdfs[file] for file in gdfs]
all_gdf_cnt = len(gdfs)
prefixed_gdfs = []
for gdf, prefix in zip(gdfs, prefixes):
    prefixed_gdf = gdf.rename(columns=lambda x: f"{prefix}{x}" if x != 'geometry' else x)
    prefixed_gdfs.append(prefixed_gdf)
gdfs = prefixed_gdfs

for gdf in gdfs:
    gdf.set_crs(epsg=4326, inplace=True)

for i, gdf in enumerate(gdfs):
    gdfs[i] = gdf.rename(columns={'geometry': f'geometry_temp_{i}'})

# Concatenate all GeoDataFrames
combined_gdf = pd.concat(gdfs, ignore_index=True)

# Combine the geometry columns into one efficiently
geometry_cols = [f'geometry_temp_{i}' for i in range(len(gdfs))]
combined_gdf['geometry'] = combined_gdf[geometry_cols[0]]
for col in geometry_cols[1:]:
    combined_gdf['geometry'] = combined_gdf['geometry'].combine_first(combined_gdf[col])

# Drop the temporary geometry columns
combined_gdf = combined_gdf.drop(columns=geometry_cols)

# Convert the combined DataFrame back to a GeoDataFrame
combined_gdf = gpd.GeoDataFrame(combined_gdf, geometry='geometry')
#combined_gdf = combined_gdf[combined_gdf['us_faa_nasr_APT_BASE_SITE_TYPE_CODE'] != 'H']
#combined_gdf = combined_gdf[combined_gdf['world_ourairports_airports_type'] != 'heliport']
#combined_gdf = combined_gdf[combined_gdf['world_ourairports_airports_type'] != 'closed']
#combined_gdf = combined_gdf[~combined_gdf['world_osm_daylight_aerodrome_name'].str.contains('heliport', case=False, na=False)]

#combined_gdf = combined_gdf.h3.geo_to_h3(3)
gdf = combined_gdf
coords = np.array(list(zip(gdf.geometry.x, gdf.geometry.y)))
    
# Perform DBSCAN clustering
db = DBSCAN(eps=.005, min_samples=2).fit(coords)
labels = db.labels_
gdf['cluster'] = db.labels_

# Number of clusters in labels, ignoring noise if present.
n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)
n_noise_ = list(labels).count(-1)

print("Estimated number of clusters: %d" % n_clusters_)
print("Estimated number of noise points: %d" % n_noise_)

# Aggregate based on cluster
singles = gdf[gdf["cluster"] == -1]
clusters = gdf[gdf["cluster"] != -1].dissolve(by='cluster')

# Convert singles to GeoDataFrame to concatenate
#singles = gpd.GeoDataFrame(singles, geometry='geometry')

# Concatenate clusters and singles
clusters = pd.concat([clusters, singles])

# Save the result to a new layer called "clusters"
clusters.to_file("package.gpkg", layer='clusters', driver="GPKG")

