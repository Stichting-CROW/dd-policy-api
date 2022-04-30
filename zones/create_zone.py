
from db_helper import db_helper
import json
from fastapi import HTTPException

def create_zone(zone):
    with db_helper.get_resource() as (cur, conn):
        try:
            zone.zone_id = create_classic_zone(cur, zone)
            create_geography(cur, zone)
            create_stop(cur, zone)
            create_no_parking_policy(cur, zone)
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")

def create_classic_zone(cur, data):
    if not check_if_zone_is_valid(data):
        raise HTTPException(status_code=404, detail="Zone not completely within borders municipality.")
    print(data.area.geometry.json())
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
        (%s, %s, %s, %s, %s, NOW(), NOW(), %s)
    """
    cur.execute(stmt, (str(data.geography_id), data.zone_id, data.name, data.description, data.geography_type, data.publish))

def create_stop(cur, data):
    if data.stop is None or data.geography_type != "stop":
        print("no_stop")
        return
    stop = data.stop
    stmt = """
        INSERT INTO stops
        (stop_id, name, location, status, capacity, geography_id)
        VALUES 
        (%s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), %s, %s, %s)
    """
    cur.execute(stmt, (str(stop.stop_id), data.name, stop.location.geometry.json(), 
        json.dumps(stop.status), json.dumps(stop.capacity), str(data.geography_id)))

def create_no_parking_policy(cur, data):
    if data.no_parking is None or data.geography_type != "no_parking":
        print("no no_parking")
        return
    no_parking = data.no_parking
    stmt = """
        INSERT INTO no_parking_policy
        (geography_id, start_date, end_date)
        VALUES
        (%s, %s, %s)
    """
    cur.execute(stmt, (str(data.geography_id), no_parking.start_date, no_parking.end_date))

def check_if_zone_is_valid(zone_data):
    return True
    # cur = self.conn.cursor()
    # stmt = """  
    # SELECT ST_WITHIN(
    #     ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), 
    #     -- Add some buffer to allow drawing a little bit out of the municipality border
    #     (SELECT st_buffer(area, 0.02) 
    #     FROM zones
    #     WHERE municipality = %s
    #     AND zone_type = 'municipality'
    #     limit 1)
    # );
    # """
    # cur.execute(stmt, (json.dumps(zone_data.get("geojson")), zone_data.get("municipality")))
    # return cur.fetchone()[0]