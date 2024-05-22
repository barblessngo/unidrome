
import os
import simplekml
import zipfile

# local path of icons should be passed at gfd["icon_path"]
def gdf_to_kmz_with_bundled_icons(gdf, file_path):
    kml = simplekml.Kml()

    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom.geom_type == 'Point':
            point = kml.newpoint(name=row.get('name', ''), coords=[(geom.x, geom.y)])
            if "icon_path" in row:
                point.style.iconstyle.icon.href = os.path.basename(row["icon_path"])
                point.style.iconstyle.color = simplekml.Color.white
                point.style.labelstyle.scale = 0
            point.description = row.get("description", "")
        elif geom.geom_type == 'LineString':
            kml.newlinestring(name=row.get('name', 'No Name'), coords=list(geom.coords))
        elif geom.geom_type == 'Polygon':
            kml.newpolygon(name=row.get('name', 'No Name'), outerboundaryis=list(geom.exterior.coords))

    # Save KML to a temporary file
    kml_path = file_path.replace(".kmz", ".kml")
    kml.save(kml_path)

    # Create KMZ archive
    with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as kmz:
        kmz.write(kml_path, os.path.basename(kml_path))
        if "icon_path" in gdf:
            for icon_path in gdf["icon_path"].unique():
                kmz.write(icon_path, os.path.basename(icon_path))

    # Remove the temporary KML file
    os.remove(kml_path)

