from click import pass_context
from db_helper import db_helper
import json
from fastapi import HTTPException
import zones.zone as zone
import zones.stop as stop
import zones.no_parking as no_parking
from geojson_pydantic import Feature, Polygon

def get_private_zones(municipality, geography_types):
    with db_helper.get_resource() as (cur, conn):
        try:
            zone_rows = query_zones(cur, municipality=municipality, geography_types=geography_types)
            zones = convert_zones(zone_rows)
            return zones
        except HTTPException as e:
            conn.rollback()
            raise e
        except Exception as e:
            conn.rollback()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")

def get_public_zones(municipality, geography_types):
    with db_helper.get_resource() as (cur, conn):
        try:
            zone_rows = query_zones(cur, municipality=municipality, geography_types=geography_types)
            zones = convert_zones(zone_rows)
            return zones
        except HTTPException as e:
            conn.rollback()
            raise e
        except Exception as e:
            conn.rollback()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")

def query_zones(cur, municipality, geography_types):
    stmt = """
        SELECT geographies.geography_id, geographies.name, description, geography_type, 
        effective_date, published_date, retire_date, prev_geographies, publish,
        zones.zone_id, zones.municipality, 
        json_build_object(
            'type',       'Feature',
            'geometry',   ST_AsGeoJSON(zones.area)::json,
            'properties',  json_build_object()
        ) as area,
        stops.stop_id, 
        json_build_object(
            'type',       'Feature',
            'geometry',   ST_AsGeoJSON( stops.location)::json,
            'properties',  json_build_object()
        ) as location,
        stops.status, stops.capacity,
        no_parking_policy.start_date, no_parking_policy.end_date
        FROM geographies
        JOIN zones
        USING (zone_id)
        LEFT JOIN stops
        USING (geography_id)
        LEFT JOIN no_parking_policy
        USING (geography_id)
        WHERE 
        ((true = %s) or (zones.municipality = %s))
        AND
        ((true = %s) or (geography_type IN %s)) 
    """
    print(municipality == None)
    print(geography_types == None)
    cur.execute(stmt, (municipality == None, municipality, len(geography_types) == 0, tuple(geography_types)))
    return cur.fetchall()

def convert_zones(zone_rows):
    results = []
    for zone_row in zone_rows: 
        result = zone.Zone(
            zone_id=zone_row["zone_id"],
            area=zone_row["area"],
            name=zone_row["name"],
            municipality=zone_row["municipality"],
            geography_id=zone_row["geography_id"],
            description=zone_row["description"],
            geography_type=zone_row["geography_type"],
            effective_date=str(zone_row["effective_date"]),
            published_date=str(zone_row["published_date"]),
            retire_data=zone_row["retire_date"],
            published=zone_row["publish"]
        )
        if result.geography_type == "stop":
            result.stop = convert_stop(stop_row=zone_row)
        elif result.geography_type == "no_parking":
            result.no_parking = convert_no_parking(no_parking_row=zone_row)
        results.append(result)
    return results

def convert_stop(stop_row):
    return stop.Stop(
        stop_id=stop_row["stop_id"],
        location=stop_row["location"],
        status=stop_row["status"],
        capacity=stop_row["capacity"]
    )

def convert_no_parking(no_parking_row):
    return no_parking.NoParking(
        start_date=no_parking_row["start_date"],
        end_date=no_parking_row["end_date"]
    )