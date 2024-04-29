from fastkml import kml, geometry as fgeo
from zones.zone import Zone, PolygonFeatureModel, EditZone, GeographyType
from zones.create_zone import check_if_user_has_access
from zones.stop import Stop
import zones.create_zone as create_zone_mod
from zones.get_zones import get_zone_by_id
import zones.edit_zone as edit_zone
import shapely.wkt
import shapely.wkb
import shapely.geometry
import shapely
from fastapi import HTTPException
from authorization import access_control
from uuid import UUID
from db_helper import db_helper

def convert_to_shapely_geometry(feature):
    geometry = shapely.wkt.loads(feature.geometry.wkt)
    return shapely.force_2d(geometry)

def create_zone(cur, feature: kml.Placemark, default_municipality_code: str, current_user: access_control.User):
    new_zone, err = parse_data_for_create(feature, default_municipality_code)
    if err:
        return None, err
    try:
        return create_zone_mod.create_zone(new_zone, current_user), None
    except Exception as e:
        return None, {
            "name": new_zone.name,
            "error": "geography_id_create_error",
            "detail": str(e)
        }

def generate_default_stop(point):
    location = {
        "type": "Feature",
        "geometry": shapely.geometry.mapping(point),
        "properties": {}
    }
    return Stop(
        location=location,
        status={"control_automatic": True},
        capacity={"combined": 10},
        is_virtual=False
    )

def parse_data_for_create(kml_feature, municipality_code):
    internal_id = next((data_element.value for data_element in kml_feature.extended_data.elements if hasattr(data_element, "name") and data_element.name == "internal_id"), None)
    geography_type = next((data_element.value for data_element in kml_feature.extended_data.elements if hasattr(data_element, "name") and data_element.name == "geography_type"), "stop")
    
    try:
        geography_type = GeographyType(geography_type)
    except:
        return None, {
            "name": kml_feature.name,
            "error": "invalid_geography_type"
        }
    
    geometry = convert_to_shapely_geometry(feature=kml_feature)
    geojson_polygon = shapely.geometry.mapping(geometry)
    stop = None
    if geography_type == "stop":
        stop = generate_default_stop(shapely.centroid(geometry))

   
    area = {
        "type": "Feature",
        "geometry": geojson_polygon,
        "properties": {}
    }
    return Zone(
            area=area,
            internal_id=internal_id,
            name=kml_feature.name,
            municipality=municipality_code,
            description=kml_feature.description or kml_feature.name,
            geography_type=geography_type,
            stop=stop
    ), None

def parse_data_for_update(geography_id: UUID, kml_feature: kml.Placemark):
    internal_id = next((data_element.value for data_element in kml_feature.extended_data.elements if data_element.name == "internal_id"), None)
    geography_type = next((data_element.value for data_element in kml_feature.extended_data.elements if data_element.name == "geography_type"), None)
    if geography_type:
        try:
            geography_type = GeographyType(geography_type)
        except:
            return None, {
                "geography_id": geography_id,
                "error": "invalid_geography_type"
            }
        
    geometry = convert_to_shapely_geometry(feature=kml_feature)
    geojson_polygon = shapely.geometry.mapping(geometry)
    area = {
        "type": "Feature",
        "geometry": geojson_polygon,
        "properties": {}
    }
    
    return EditZone(
        geography_id=geography_id,
        area=area,
        name=kml_feature.name,
        internal_id=internal_id,
        description=kml_feature.description,
        geography_type=geography_type
    ), None


def update_zone(cur, geography_id: UUID, kml_feature: kml.Placemark, email: str):
    zone: Zone = None
    try:
        zone = get_zone_by_id(cur, geography_uuid=UUID(geography_id))
    except:
        print("geography_id doesnt_exists")

    if not zone:
        return None, {
            "geography_id": geography_id,
            "error": "geography_id_doesnt_exists"
        }
    elif zone.phase != "concept":
        return None, {
            "geography_id": geography_id,
            "error": "geography_id_cant_be_edited_zone_not_in_concept_phase"
        }
    new_zone, err = parse_data_for_update(geography_id=geography_id, kml_feature=kml_feature)
    if err:
        return None, err
    try:
        res = edit_zone.update_zone(cur, old_zone=zone, new_zone=new_zone, email=email)
        return res, None
    except Exception as e:
        return None, {
            "geography_id": geography_id,
            "error": "geography_id_update_error",
            "detail": str(e)
        }

    

def get_all_polygons(element) -> list[kml.Placemark]:
    if not getattr(element, 'features', None):
        return []
    polygons = []
    # Get all polygons within document.
    for feature in element.features():
        if isinstance(feature, kml.Placemark) and isinstance(feature.geometry, fgeo.Polygon):
            polygons.append(feature)
        polygons.extend(get_all_polygons(feature))
    return polygons



def kml_import(kml_file, municipality_code: str, current_user: access_control.User):
    check_if_user_has_access(municipality=municipality_code, acl=current_user.acl)

    municipality_border = db.get_municipality_border(municipality_code)
    if not municipality_border:
        raise HTTPException(400, "municipality code is not known")
    municipality_area = shapely.wkb.loads(municipality_border)

    k = kml.KML()
    k.from_string(kml_file.decode("utf-8"))
   
    polygons: list[kml.Placemark] = []
    for collection in k.features():
        polygons.extend(get_all_polygons(collection))

    res = {
        "created": [],
        "modified": [],
        "error": []
    }
    with db_helper.get_resource() as (cur, conn):  
        for feature in polygons:
            geography_id = next((data_element.value for data_element in feature.extended_data.elements if hasattr(data_element, "name") and data_element.name == "_geography_id"), None)
            if geography_id:
                updated_zone, err = update_zone(cur, geography_id, feature, current_user.email)
                if updated_zone:
                    res["modified"].append(updated_zone)
                if err:
                    res["error"].append(err)
            else:
                created_zone, err = create_zone(cur, feature=feature, default_municipality_code=municipality_code, current_user=current_user)
                if created_zone:
                    res["created"].append(created_zone)
                if err:
                    res["error"].append(err) 
        conn.commit()
    return res

# 1 check if geography_id is filled
# if yes, get geography and check phase
    # if phase is != concept error and skip
    # else update existing geography or create new geography
# else 
# import new geography and generate new geography_id as concept

# inserted
# updated
# error