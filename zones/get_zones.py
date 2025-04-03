from click import pass_context
from db_helper import db_helper
import json
from fastapi import HTTPException
import zones.zone as zone_mod
import zones.stop as stop_mod
import zones.no_parking as no_parking
from geojson_pydantic import Feature, Polygon
from uuid import UUID


def get_private_zones(municipality, geography_types, phases: list[zone_mod.Phase], affected_modalities: list):
    with db_helper.get_resource() as (cur, conn):
        try:
            zone_rows = query_zones(cur, municipality=municipality, geography_types=geography_types, phases=phases, affected_modalities=affected_modalities)
            zones = zone_mod.convert_zones(zone_rows, include_private_data=True)
            zones_with_realtime_data = zone_mod.look_up_realtime_data(zones)
            return zones_with_realtime_data
        except HTTPException as e:
            conn.rollback()
            raise e
        except Exception as e:
            conn.rollback()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")

def get_public_zones(municipality, geography_types, phases: list[zone_mod.Phase], affected_modalities: list):
    with db_helper.get_resource() as (cur, conn):
        try:
            zone_rows = query_zones(cur, municipality=municipality, geography_types=geography_types, phases=phases, affected_modalities=affected_modalities)
            zones = zone_mod.convert_zones(zone_rows, include_private_data=False)
            zones_with_realtime_data = zone_mod.look_up_realtime_data(zones)
            return zones_with_realtime_data
        except HTTPException as e:
            conn.rollback()
            raise e
        except Exception as e:
            conn.rollback()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")

def query_zones(cur, municipality, geography_types, phases, affected_modalities: list):
    stmt = """
        SELECT *
        FROM (
            SELECT geographies.geography_id, internal_id, geographies.name, description, geography_type, 
            effective_date, published_date, propose_retirement, published_retire_date, retire_date, prev_geographies,
            zones.zone_id, zones.municipality, 
            json_build_object(
                'type',       'Feature',
                'geometry',   ST_AsGeoJSON(zones.area)::json,
                'properties',  json_build_object()
            ) as area,
            created_at, modified_at, created_by, last_modified_by,
            CASE 
                WHEN (published_date IS NULL) THEN 'concept'
                WHEN (propose_retirement = true AND published_retire_date IS NULL) THEN 'retirement_concept' 
                WHEN NOW() < published_date AND NOW() < effective_date THEN 'committed_concept'
                WHEN propose_retirement = true AND NOW() < published_retire_date AND NOW() < retire_date THEN 'committed_retirement_concept'
                WHEN NOW() > published_date AND NOW() < effective_date THEN 'published'
                WHEN propose_retirement = true AND NOW() > published_retire_date AND NOW() < retire_date THEN 'published_retirement'
                WHEN (NOW() > effective_date AND (NOW() < retire_date OR retire_date IS NULL)) THEN 'active'
                WHEN (NOW() > retire_date) THEN 'archived'
                ELSE 'error'
            END as phase,
            stops.stop_id, 
            json_build_object(
                'type',       'Feature',
                'geometry',   ST_AsGeoJSON( stops.location)::json,
                'properties',  json_build_object()
            ) as location,
            stops.status, stops.capacity, stops.is_virtual
            FROM geographies
            JOIN zones
            USING (zone_id)
            LEFT JOIN stops
            USING (geography_id)
            WHERE 
            ((true = %s) or (zones.municipality = %s))
            AND
            ((true = %s) or (geography_type = ANY(%s)))
            AND
            (geographies.affected_modalities && %s)
        ) as all_zones
        WHERE phase = ANY(%s);
    """
    print(phases)
    print(affected_modalities)
    cur.execute(stmt, (municipality == None, municipality, len(geography_types) == 0, geography_types, affected_modalities, phases))
    return cur.fetchall()

def get_zone_by_id(cur, geography_uuid: UUID) -> zone_mod.Zone:
    result = query_zone_by_id(cur, geography_uuid)
    if result == None:
        raise HTTPException(status_code=404, detail=f"Geography {geography_uuid} doesn't exist.")
    return zone_mod.convert_zone(result, include_private_data=True)

def query_zone_by_id(cur, geography_uuid: UUID):
    stmt = """
        SELECT geographies.geography_id, internal_id, geographies.name, description, geography_type, 
        effective_date, published_date, propose_retirement, published_retire_date, retire_date, prev_geographies,
        zones.zone_id, zones.municipality, 
        json_build_object(
            'type',       'Feature',
            'geometry',   ST_AsGeoJSON(zones.area)::json,
            'properties',  json_build_object()
        ) as area,
        created_at, modified_at, created_by, last_modified_by,
        CASE 
            WHEN (published_date IS NULL) THEN 'concept'
            WHEN (propose_retirement = true AND published_retire_date IS NULL) THEN 'retirement_concept' 
            WHEN NOW() < published_date AND NOW() < effective_date THEN 'committed_concept'
            WHEN propose_retirement = true AND NOW() < published_retire_date AND NOW() < retire_date THEN 'committed_retirement_concept'
            WHEN NOW() > published_date AND NOW() < effective_date THEN 'published'
            WHEN propose_retirement = true AND NOW() > published_retire_date AND NOW() < retire_date THEN 'published_retirement'
            WHEN (NOW() > effective_date AND (NOW() < retire_date OR retire_date IS NULL)) THEN 'active'
            WHEN (NOW() > retire_date) THEN 'archived'
            ELSE 'error'
        END as phase,
        stops.stop_id, 
        json_build_object(
            'type',       'Feature',
            'geometry',   ST_AsGeoJSON( stops.location)::json,
            'properties',  json_build_object()
        ) as location,
        stops.status, stops.capacity, stops.is_virtual
        FROM geographies
        JOIN zones
        USING (zone_id)
        LEFT JOIN stops
        USING (geography_id)
        WHERE 
        geographies.geography_id = %s
    """
    cur.execute(stmt, (str(geography_uuid),))
    return cur.fetchone()


def get_zones_by_ids(cur, geography_uuids: list[UUID]):
    result = query_zones_by_ids(cur, geography_uuids)
    zones = []
    for row in result:
        zones.append(zone_mod.convert_zone(row, include_private_data=True))
    return zones

def query_zones_by_ids(cur, geography_uuids: list[UUID]):
    stmt = """
        SELECT geographies.geography_id, internal_id, geographies.name, description, geography_type, 
        effective_date, published_date, propose_retirement, published_retire_date, retire_date, prev_geographies,
        zones.zone_id, zones.municipality, 
        json_build_object(
            'type',       'Feature',
            'geometry',   ST_AsGeoJSON(zones.area)::json,
            'properties',  json_build_object()
        ) as area,
        created_at, modified_at, created_by, last_modified_by,
        CASE 
            WHEN (published_date IS NULL) THEN 'concept'
            WHEN (propose_retirement = true AND published_retire_date IS NULL) THEN 'retirement_concept' 
            WHEN NOW() < published_date AND NOW() < effective_date THEN 'committed_concept'
            WHEN propose_retirement = true AND NOW() < published_retire_date AND NOW() < retire_date THEN 'committed_retirement_concept'
            WHEN NOW() > published_date AND NOW() < effective_date THEN 'published'
            WHEN propose_retirement = true AND NOW() > published_retire_date AND NOW() < retire_date THEN 'published_retirement'
            WHEN (NOW() > effective_date AND (NOW() < retire_date OR retire_date IS NULL)) THEN 'active'
            WHEN (NOW() > retire_date) THEN 'archived'
            ELSE 'error'
        END as phase,
        stops.stop_id, 
        json_build_object(
            'type',       'Feature',
            'geometry',   ST_AsGeoJSON( stops.location)::json,
            'properties',  json_build_object()
        ) as location,
        stops.status, stops.capacity, stops.is_virtual
        FROM geographies
        JOIN zones
        USING (zone_id)
        LEFT JOIN stops
        USING (geography_id)
        WHERE 
        geographies.geography_id = ANY(%s)
    """
    cur.execute(stmt, (geography_uuids,))
    return cur.fetchall()
