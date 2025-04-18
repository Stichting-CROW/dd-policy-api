
from db_helper import db_helper
import json
from fastapi import HTTPException
from zones.zone import Zone, GeographyType
from modalities import Modality

def create_single_zone(cur, zone: Zone, user):
    check_if_user_has_access(zone.municipality, user.acl)
    zone.zone_id = create_classic_zone(cur, zone)
    zone.affected_modalities = derive_affected_modalities(zone)
    print(zone.affected_modalities)

    create_geography(cur, zone, user.email)
    create_stop(cur, zone)


    return zone

# Derive affected_modalities for backward compitable behaviour.
def derive_affected_modalities(zone: Zone):
    if zone.geography_type != GeographyType.stop:
        return zone.affected_modalities
    # if "combined" the default modes are affected
    print(zone.stop.capacity)
    if "combined" in zone.stop.capacity:
        return [Modality.bicycle, Modality.moped, Modality.cargo_bicycle]
    affected_modalities: list[Modality] = []
    if "moped" in zone.stop.capacity:
        affected_modalities.append(Modality.moped)
    if "bicycle" in zone.stop.capacity:
        affected_modalities.append(Modality.bicycle)
    if "cargo_bicycle" in zone.stop.capacity:
        affected_modalities.append(Modality.cargo_bicycle)
    if "car" in zone.stop.capacity:
        affected_modalities.append(Modality.car)
    return affected_modalities
    
def create_zones(zones, user):
    result = []
    errors = []
    with db_helper.get_resource() as (cur, conn):
        for zone in zones:
            try:
                result.append(create_single_zone(cur, zone, user))    
            except HTTPException as e:
                errors.append({
                    "geography_id": zone.geography_id,
                    "error": "geography_id_create_error",
                    "detail": str(e)
                })
            except Exception as e:
                print("It's going wrong here")
                conn.rollback()
                print(e)
                raise HTTPException(status_code=500, detail="DB problem, check server log for details.")
        try:
            conn.commit()
        except Exception as e:
            print(e)
            conn.rollback()
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")

    return result, errors

def create_zone(zone, user):
    with db_helper.get_resource() as (cur, conn):
        try:
            zone = create_single_zone(cur, zone, user)
            conn.commit()
            return zone
        except HTTPException as e:
            conn.rollback()
            raise e
        except Exception as e:
            conn.rollback()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")

def create_classic_zone(cur, data):
    if not check_if_zone_is_valid(cur, data.area.geometry.json(), data.municipality):
        raise HTTPException(status_code=403, detail="Zone not completely within borders municipality.")
    stmt = """
        INSERT INTO zones
        (area, name, municipality, zone_type)
        VALUES
        (ST_SetSRID(ST_MakeValid(ST_GeomFromGeoJSON(%s)), 4326), %s, %s, 'custom')
        RETURNING zone_id
    """
    cur.execute(stmt, (data.area.geometry.json(), data.name, data.municipality))
    return cur.fetchone()["zone_id"]

def create_geography(cur, data, email):
    stmt = """
        INSERT INTO geographies
        (geography_id, internal_id, zone_id, name, description, geography_type, effective_date, published_date, prev_geographies, created_at, modified_at, created_by, last_modified_by, affected_modalities)
        VALUES
        (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), %s, %s, %s)
        RETURNING created_at, modified_at
    """
    print(data)
    cur.execute(stmt, (str(data.geography_id), data.internal_id, data.zone_id, data.name, data.description, data.geography_type, 
        data.effective_date, data.published_date, data.prev_geographies, email, email, data.affected_modalities))
    res = cur.fetchone()
    data.created_at = res["created_at"]
    data.modified_at = res["modified_at"]
    data.last_modified_by = email
    data.created_by = email
    data.phase = "concept"

def create_stop(cur, data):
    if data.geography_type != "stop":
        return
    if data.stop is None:
        raise HTTPException(status_code=422, detail="Object that describes details of stop missing.")
    stop = data.stop
    stmt = """
        INSERT INTO stops
        (stop_id, name, location, status, capacity, geography_id, is_virtual)
        VALUES 
        (%s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), %s, %s, %s, %s)
    """
    cur.execute(stmt, (str(stop.stop_id), data.name, stop.location.geometry.json(), 
        json.dumps(stop.status), json.dumps(stop.capacity), str(data.geography_id), stop.is_virtual))

def check_if_zone_is_valid(cur, geometry, municipality):
    print(geometry)
    stmt = """  
    SELECT ST_WITHIN(
        ST_SetSRID(ST_MakeValid(ST_GeomFromGeoJSON(%s)), 4326), 
        -- Add some buffer to allow drawing a little bit out of the municipality border
        (SELECT st_buffer(area, 0.02) 
        FROM zones
        WHERE municipality = %s
        AND zone_type = 'municipality'
        limit 1) 
    ) as is_valid;
    """
    cur.execute(stmt, (geometry, municipality))
    result = cur.fetchone()
    print("succesvol")
    if result == None:
        return False
    return result["is_valid"]

def check_if_user_has_access(municipality, acl):
    if acl.is_admin:
        return True
    if not acl.is_allowed_to_edit:
        raise HTTPException(status_code=403, detail="User is not allowed to create or modify zones in this municipality, check ACL.")
    if municipality in acl.municipalities:
        return True
    raise HTTPException(status_code=403, detail="User is not allowed to create or modify zones in this municipality, check ACL.")
    
