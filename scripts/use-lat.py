from lon_lat_lookup_gen import lon_lat_lookup, get_all_gdfs
import geopandas as gpd
import pandas as pd
import h3pandas

gdfs = get_all_gdfs()
prefixes = [ f"{k.replace('/', '_').replace('.', '_')}_" for k in lon_lat_lookup ]
gdfs = [gdfs[file] for file in gdfs]
prefixed_gdfs = []
for gdf, prefix in zip(gdfs, prefixes):
    prefixed_gdf = gdf.rename(columns=lambda x: f"{prefix}{x}" if x != 'geometry' else x)
    prefixed_gdfs.append(prefixed_gdf)
gdfs = prefixed_gdfs
print(gdfs)

for gdf in gdfs:
    gdf.set_crs(epsg=4326, inplace=True)

for i, gdf in enumerate(gdfs):
    gdfs[i] = gdf.rename(columns={'geometry': f'geometry_temp_{i}'})

# Rename the geometry column in each GeoDataFrame to avoid conflicts
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

df = combined_gdf.h3.geo_to_h3_aggregate(7)
h3_combined = gpd.GeoDataFrame(df, geometry='geometry')

print(h3_combined)
# Save the combined GeoDataFrame to a file
h3_combined.to_file("package.gpkg", layer='unidrome', driver="GPKG")
