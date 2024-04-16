from db_helper import db_helper
from fastapi import HTTPException
import zones.zone as zone
import zones.stop as stop
from datetime import date
from service_areas.get_service_areas import query_service_area_geometries

from service_areas.service_area_delta import ServiceAreaDelta
from geojson_pydantic import FeatureCollection

def get_service_area_delta(
    service_area_version_id: int
) -> ServiceAreaDelta:
    with db_helper.get_resource() as (cur, conn):
        try:
            res = query_service_area_delta(cur, service_area_version_id)
            unchanged_geometries, added_geometries, removed_geometries = get_delta_geometries(cur, res["previous_geometries"], res["new_geometries"]) 
            return ServiceAreaDelta(
                    service_area_version_id=res["service_area_version_id"],
                    previous_service_area_version_id=res["previous_version_id"],
                    timestamp=res["timestamp"],
                    added_geometries=added_geometries,
                    removed_geometries=removed_geometries,
                    unchanched_geometries=unchanged_geometries
                )
        except HTTPException as e:
            conn.rollback()
            print(e)
            raise e
        except Exception as e:
            conn.rollback()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")

def get_delta_geometries(cur, previous_geometries_list, new_geometries_list):
    previous_geometries = set()
    if previous_geometries_list:
        previous_geometries  = set(previous_geometries_list)
    new_geometries = set(new_geometries_list)
    
    unchanged_geometries = previous_geometries.intersection(new_geometries)
    added_geometries = new_geometries.difference(previous_geometries)
    removed_geometries = previous_geometries.difference(new_geometries)

    unchanged_geometry_collection = get_delta_geometry_feature_collection(cur, unchanged_geometries)
    added_geometry_collection = get_delta_geometry_feature_collection(cur, added_geometries)
    removed_geometry_collection = get_delta_geometry_feature_collection(cur, removed_geometries)
    return unchanged_geometry_collection, added_geometry_collection, removed_geometry_collection

def get_delta_geometry_feature_collection(cur, geometry_hashes):
    if len(geometry_hashes) == 0:
        return None
    res = query_service_area_geometries(cur, list(geometry_hashes))
    return FeatureCollection.parse_obj(res["feature_collection"])

def query_service_area_delta(cur, service_area_version_id: int):
    stmt = """
    WITH change_record AS (
        SELECT service_area_version_id, municipality, operator, valid_from, 
        valid_until, service_area_geometries 
        FROM service_area 
        WHERE service_area_version_id = %s
        LIMIT 1
    ),
    previous_record AS (
            SELECT service_area.service_area_geometries, service_area.service_area_version_id
            FROM service_area, change_record
            WHERE service_area.municipality = change_record.municipality
            AND service_area.operator = change_record.operator
            AND service_area.valid_until <= change_record.valid_from
            ORDER BY service_area.valid_from DESC
            LIMIT 1
    )

    SELECT change_record.service_area_version_id, 
        change_record.service_area_geometries as new_geometries,
        change_record.valid_from as timestamp,
        (SELECT previous_record.service_area_geometries from previous_record) as previous_geometries,
        (SELECT previous_record.service_area_version_id from previous_record) as previous_version_id
    FROM change_record;
    """
    cur.execute(stmt, (service_area_version_id,))
    return cur.fetchone()