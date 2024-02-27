from db_helper import db_helper
from fastapi import HTTPException
import zones.zone as zone
import zones.stop as stop
import zones.no_parking as no_parking

from service_areas.service_area import ServiceArea
from geojson_pydantic import FeatureCollection

def get_service_areas(municipalities, operators):
    with db_helper.get_resource() as (cur, conn):
        try:
            res = query_service_areas(cur, municipalities=municipalities, operators=operators)
            response = []
            for service_area in res:
                geometries = query_service_area_geometries(cur, service_area["service_area_geometries"])
                geometries_feature_collection = FeatureCollection.parse_obj(geometries["feature_collection"])
                response.append(ServiceArea(
                    service_area_version_id=service_area["service_area_version_id"],
                    municipality=service_area["municipality"],
                    operator=service_area["operator"],
                    valid_from=service_area["valid_from"],
                    geometries=geometries_feature_collection
                ))
            return response
        except HTTPException as e:
            conn.rollback()
            raise e
        except Exception as e:
            conn.rollback()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")


def query_service_areas(cur, municipalities: list[str], operators: list[str]):

    stmt = """
        SELECT service_area_version_id, municipality, operator, valid_from, service_area_geometries  
        FROM service_area 
        WHERE municipality = ANY(%s) AND operator = ANY(%s)
        AND valid_until IS NULL;
    """
    cur.execute(stmt, (municipalities, operators))
    return cur.fetchall()

def query_service_area_geometries(cur, geom_hashes: list[str]):
    stmt = """
        SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', json_agg(ST_AsGeoJSON(q1.*)::json)
            ) as feature_collection
        FROM 
        (
            SELECT geom, geom_hash 
            FROM service_area_geometry
            WHERE geom_hash = ANY(%s)
        ) as q1;
    """
    cur.execute(stmt, (geom_hashes,))
    return cur.fetchone()


