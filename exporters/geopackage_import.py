
from typing import Dict, Union
from geojson_pydantic import Feature, Point, Polygon, MultiPolygon as MultiPolygonPydantic
from mds import stop
from zones import edit_zone, get_zones
from zones import create_zone
from zones import zone
from zones.create_zone import check_if_user_has_access

from fastapi import UploadFile, HTTPException
from authorization import access_control
from db_helper import db_helper
from fudgeo.geopkg import FeatureClass, Field, GeoPackage, SpatialReferenceSystem
from fudgeo.geometry import MultiPolygon
from geojson_pydantic.types import Position2D
from shapely.geometry import shape

import uuid

from zones.stop import Stop
from zones.zone import Zone

def is_valid_uuid(uuid_string):
    try:
        # Attempt to create a UUID object from the string
        uuid_obj = uuid.UUID(uuid_string)
        # Check if the string representation matches exactly, to avoid partial matches
        return str(uuid_obj) == uuid_string.lower()
    except ValueError:
        # If ValueError is raised, it’s not a valid UUID
        print("INCORRECT")
        return False


def convert_capacity(record):
    if record[5]:
        return {
            "combined": record[5]
        }
    return {
        "bicycle": record[6] if record[6] else 0,
        "moped": record[7] if record[7] else 0,
        "cargo_bicycle": record[8] if record[8] else 0,
        "car": record[9] if record[9] else 0
    }

def convert_microhub_control_status(status: str) -> Dict[str, bool]:
    if status == "control_automatic":
        return {
            "control_automatic": True
        }
    if status == "is_returning":
        return {
            "is_renting": True,
            "is_installed": True,
            "is_returning": True,
            "control_automatic": False
        }

    return {
        "is_renting": False,
        "is_installed": True,
        "is_returning": False,
        "control_automatic": False
    }


def get_microhubs(gpkg: GeoPackage, municipality_code: str):
    fc = FeatureClass(geopackage=gpkg, name='microhubs')
    cursor = fc.select(fields=('_geography_id', 'name', 'internal_id', 'description', 'capacity_combined', 'capacity_bicycle',
                            'capacity_moped', 'capacity_cargo_bicycle', 'capacity_car',
                            'microhub_control_status', 'is_virtual'), include_geometry=True)
    features: list[tuple[MultiPolygon, str, str, str]] = cursor.fetchall()
    new_zones = []
    for feature in features:
        # We can improve this in the future for multipolygons.
        coords_list = [Position2D(float(coord[0]), float(coord[1])) for coord in feature[0].polygons[0].rings[0].coordinates]
        area = Polygon(type='Polygon', coordinates=[coords_list])
        area_feature = Feature[Union[Polygon, MultiPolygonPydantic], Dict](type='Feature', properties={}, geometry=area)

        shapely_polygon = shape(area.model_dump())
        
        centroid_coords = shapely_polygon.centroid
        centroid_point = Point(type='Point', coordinates=[centroid_coords.x, centroid_coords.y])

        # Create a FeatureModel with the centroid point as geometry
        centroid_feature = Feature[Point, Dict](geometry=centroid_point, properties={}, type='Feature')

        stop = Stop(
            location=centroid_feature,
            status=convert_microhub_control_status(feature[9]),
            capacity=convert_capacity(feature),
            is_virtual=feature[11]
        )
     

        new_zone = Zone(
            area=area_feature,
            name=feature[2],
            municipality=municipality_code,
            internal_id=feature[3],
            description=feature[4],
            geography_type="stop",
            stop=stop
        )

        if feature[1] and is_valid_uuid(feature[1]):
            new_zone.geography_id = uuid.UUID(feature[1])
        new_zones.append(new_zone)

    return new_zones

def get_no_parking(gpkg: GeoPackage, municipality_code: str):
    fc = FeatureClass(geopackage=gpkg, name='no_parking')
    cursor = fc.select(fields=('_geography_id', 'name', 'internal_id', 'description'), include_geometry=True)
    features: list[tuple[MultiPolygon, str, str, str]] = cursor.fetchall()
    new_zones = []
    for feature in features:
        # We can improve this in the future for multipolygons.
        coords_list = [Position2D(float(coord[0]), float(coord[1])) for coord in feature[0].polygons[0].rings[0].coordinates]
        area = Polygon(type='Polygon', coordinates=[coords_list])
        area_feature = Feature[Union[Polygon, MultiPolygonPydantic], Dict](type='Feature', properties={}, geometry=area)


        new_zone = Zone(
            area=area_feature,
            name=feature[2],
            municipality=municipality_code,
            internal_id=feature[3],
            description=feature[4],
            geography_type="no_parking"
        )

        if feature[1] and is_valid_uuid(feature[1]):
            new_zone.geography_id = uuid.UUID(feature[1])
        new_zones.append(new_zone)

    return new_zones

def get_monitoring(gpkg: GeoPackage, municipality_code: str):
    fc = FeatureClass(geopackage=gpkg, name='monitoring')
    cursor = fc.select(fields=('_geography_id', 'name', 'internal_id', 'description'), include_geometry=True)
    features: list[tuple[MultiPolygon, str, str, str]] = cursor.fetchall()
    new_zones = []
    for feature in features:
        # We can improve this in the future for multipolygons.
        coords_list = [Position2D(float(coord[0]), float(coord[1])) for coord in feature[0].polygons[0].rings[0].coordinates]
        area = Polygon(type='Polygon', coordinates=[coords_list])
        area_feature = Feature[Union[Polygon, MultiPolygonPydantic], Dict](type='Feature', properties={}, geometry=area)

        new_zone = Zone(
            area=area_feature,
            name=feature[2],
            municipality=municipality_code,
            internal_id=feature[3],
            description=feature[4],
            geography_type="no_parking"
        )

        if feature[1] and is_valid_uuid(feature[1]):
            new_zone.geography_id = uuid.UUID(feature[1])
        new_zones.append(new_zone)

    return new_zones

def gpkg_import(gpkg_file_name: str, municipality_code: str, current_user: access_control.User):
    check_if_user_has_access(municipality=municipality_code, acl=current_user.acl)
    gpkg = GeoPackage(gpkg_file_name)
    
    uploaded_zones = get_microhubs(gpkg, municipality_code)
    uploaded_zones.extend(get_no_parking(gpkg, municipality_code))
    uploaded_zones.extend(get_monitoring(gpkg, municipality_code))

    geography_ids = [data.geography_id for data in uploaded_zones]

    with db_helper.get_resource() as (cur, conn): 
        old_zones = get_zones.get_zones_by_ids(cur, geography_ids)
        zone_dict = {str(t.geography_id): t for t in old_zones}
    
        return process_uploaded_zones(uploaded_zones, zone_dict, current_user)


def edit_zones(to_edit_zones, zone_dict, user):
    result = []
    errors = []
    with db_helper.get_resource() as (cur, conn):
        for to_edit_zone in to_edit_zones:
            try:
                result.append(edit_zone.edit_old_zone(cur, zone_dict[str(to_edit_zone.geography_id)], to_edit_zone, user))    
            except HTTPException as e:
                errors.append({
                    "geography_id": to_edit_zone.geography_id,
                    "error": "geography_id_edit_error",
                    "detail": str(e)
                })
            except Exception as e:
                conn.rollback()
                print(e)
                raise HTTPException(status_code=500, detail="DB problem, check server log for details.")
        try:
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")
    return result, errors

def process_uploaded_zones(z: list[zone.Zone], zone_dict, current_user: access_control.User):
    res = {
        "created": [],
        "modified": [],
        "error": []
    }
    to_edit_zones = []
    to_create_zones = []
    for new_zone in z:
        if str(new_zone.geography_id) in zone_dict:
            # update
            edit_stop = None
            if new_zone.geography_type == "microhub":
                edit_stop = stop.EditStop(
                    location = new_zone.stop.location,
                    is_virtual = new_zone.stop.is_virtual,
                    status = new_zone.stop.status,
                    capacity = new_zone.stop.capacity,
                )

            to_edit_zones.append(edit_zone.EditZone(
                geography_id=new_zone.geography_id,
                area=new_zone.area,
                name=new_zone.name,
                internal_id=new_zone.internal_id,
                description=new_zone.description,
                geography_type=new_zone.geography_type,
                stop=edit_stop
            ))
            print(f"update {new_zone.geography_id}")
        else:
            to_create_zones.append(new_zone)

    res["created"], errors = create_zone.create_zones(to_create_zones, current_user)
    res["error"].extend(errors)
    
    res["modified"], errors = edit_zones(to_edit_zones, zone_dict, current_user)
    res["error"].extend(errors)
    return res