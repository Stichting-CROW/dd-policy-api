
from db_helper import db_helper
import json
from fastapi import HTTPException
import zones.generate_policy as generate_policy

def create_zone(zone, user):
    with db_helper.get_resource() as (cur, conn):
        try:
            check_if_user_has_access(zone, user.acl)
            zone.zone_id = create_classic_zone(cur, zone)
            create_geography(cur, zone)
            create_stop(cur, zone)
            create_no_parking_policy(cur, zone)
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
    if not check_if_zone_is_valid(cur, data):
        raise HTTPException(status_code=403, detail="Zone not completely within borders municipality.")
    stmt = """
        INSERT INTO zones
        (area, name, municipality, zone_type)
        VALUES
        (ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), %s, %s, 'custom')
        RETURNING zone_id
    """
    cur.execute(stmt, (data.area.geometry.json(), data.name, data.municipality))
    return cur.fetchone()["zone_id"]

def create_geography(cur, data):
    stmt = """
        INSERT INTO geographies
        (geography_id, zone_id, name, description, geography_type, effective_date, published_date, publish)
        VALUES
        (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    cur.execute(stmt, (str(data.geography_id), data.zone_id, data.name, data.description, data.geography_type, 
        data.effective_date, data.published_date, data.published))

def create_stop(cur, data):
    if data.geography_type != "stop":
        return
    if data.stop is None:
        raise HTTPException(status_code=422, detail="Object that describes details of stop missing.")
    stop = data.stop
    stmt = """
        INSERT INTO stops
        (stop_id, name, location, status, capacity, geography_id)
        VALUES 
        (%s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), %s, %s, %s)
    """
    print("execute.")
    cur.execute(stmt, (str(stop.stop_id), data.name, stop.location.geometry.json(), 
        json.dumps(stop.status), json.dumps(stop.capacity), str(data.geography_id)))

def create_no_parking_policy(cur, data):
    if data.geography_type != "no_parking":
        return
    if data.no_parking is None:
        raise HTTPException(status_code=422, detail="Object that describes details of no_parkin policy missing.")
    no_parking = data.no_parking
    stmt = """
        INSERT INTO no_parking_policy
        (geography_id, start_date, end_date)
        VALUES
        (%s, %s, %s)
    """
    cur.execute(stmt, (str(data.geography_id), no_parking.start_date, no_parking.end_date))
    generate_policy.generate_policy(cur, data)
    

def check_if_zone_is_valid(cur, data):
    stmt = """  
    SELECT ST_WITHIN(
        ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), 
        -- Add some buffer to allow drawing a little bit out of the municipality border
        (SELECT st_buffer(area, 0.02) 
        FROM zones
        WHERE municipality = %s
        AND zone_type = 'municipality'
        limit 1) 
    ) as is_valid;
    """
    cur.execute(stmt, (data.area.geometry.json(), data.municipality))
    result = cur.fetchone()
    if result == None:
        return False
    return result["is_valid"]

def check_if_user_has_access(zone, acl):
    if acl.is_admin:
        return True
    if zone.municipality in acl.municipalities:
        return True
    raise HTTPException(status_code=403, detail="User is not allowed to create zone in this municipality, check ACL.")
    
