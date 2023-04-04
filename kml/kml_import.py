from fastkml import kml, geometry as fgeo
from zones.zone import Zone, PolygonFeatureModel
import shapely.wkt
import shapely.wkb
import shapely.geometry
import shapely
from kml import db
from fastapi import HTTPException

def get_all_polygons(element):
    if not getattr(element, 'features', None):
        return []
    polygons = []
    # Get all polygons within document.
    for feature in element.features():
        if isinstance(feature, kml.Placemark) and isinstance(feature.geometry, fgeo.Polygon):
            polygons.append(feature)
        polygons.extend(get_all_polygons(feature))
    return polygons

def kml_import(kml_file, municipality_code):
    municipality_border = db.get_municipality_border(municipality_code)
    if not municipality_border:
        raise HTTPException(400, "municipality code is not known")
    municipality_area = shapely.wkb.loads(municipality_border)

    k = kml.KML()
    k.from_string(kml_file.decode("utf-8"))
   
    polygons = []
    for collection in k.features():
        polygons.extend(get_all_polygons(collection))
    zones = []
    for feature in polygons:
        geometry = shapely.wkt.loads(feature.geometry.wkt)
        geometry = shapely.force_2d(geometry)
        geojson_polygon = shapely.geometry.mapping(geometry)
        result = {
            "type": "Feature",
            "geometry": geojson_polygon,
            "properties": {}
        }
        zones.append({
            "is_within_borders_municipality": municipality_area.contains(geometry),
            "zone": Zone(
            area=result,
            name=feature.name,
            municipality=municipality_code,
            description=feature.name,
            geography_type="monitoring"
        )})
    return zones
   