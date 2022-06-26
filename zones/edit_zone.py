from fastapi import HTTPException
from db_helper import db_helper
from mds import geography
from zones.create_zone import create_no_parking_policy, create_stop, check_if_zone_is_valid, create_classic_zone, create_geography
from zones.delete_zone import delete_no_parking, delete_stops, retire_geography, retire_policy
from zones.get_zones import get_zone_by_id
from zones.generate_policy import generate_policy
from uuid import uuid1
import json
import datetime

def edit_zone(new_zone, user):
    with db_helper.get_resource() as (cur, conn):
        try:
            old_zone = get_zone_by_id(cur, new_zone.geography_id)
            check_if_user_has_access(old_zone.municipality, new_zone.municipality, user.acl)
            print(old_zone)
            print(new_zone)
            if old_zone != new_zone:
                update_zone(cur, old_zone, new_zone)
            conn.commit()
            print("commited")
            return new_zone
        except HTTPException as e:
            conn.rollback()
            raise e
        except Exception as e:
            conn.rollback()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")


def update_zone(cur, old_zone, new_zone):
    print("Check stop should be updated:")
    print(stop_should_be_updated(old_zone, new_zone))
    if stop_should_be_updated(old_zone, new_zone):
        print("Update stop")
        new_zone.stop.stop_id = old_zone.stop.stop_id
        update_stop(cur, new_zone)
    if no_parking_should_be_updated(old_zone, new_zone):
        update_no_parking(cur, new_zone)
    if old_zone.geography_type != new_zone.geography_type:
        new_geography_type(cur, new_zone)
    if geography_should_be_updated(old_zone, new_zone):
        update_geography(cur, old_zone, new_zone)
    if old_zone.published and not new_zone.published and old_zone.geography_id == new_zone.geography_id:
        raise HTTPException(status_code=422, detail="You can't unpublish a geography.")
    if not old_zone.published and new_zone.published:
        publish_geography(cur, new_zone)
        

def new_geography_type(cur, new_zone):
    # Delete old no_parking and stops.
    delete_no_parking(cur, new_zone.geography_id)
    delete_stops(cur, new_zone.geography_id)
    # Creates no_parking_policy or stop when applicable.
    create_no_parking_policy(cur, new_zone)
    create_stop(cur, new_zone)

def geography_should_be_updated(old_zone, new_zone):
    return (
        old_zone.area != new_zone.area or
        old_zone.name != new_zone.name or
        old_zone.municipality != new_zone.municipality or
        old_zone.description != new_zone.description or
        old_zone.geography_type != new_zone.geography_type
    )

def stop_should_be_updated(old_zone, new_zone):
    print(old_zone.stop)
    print(new_zone.stop)
    print("checks")
    print(old_zone.stop != new_zone.stop)
    print(old_zone.stop == "stop")
    print(new_zone.stop == "stop")
    print(old_zone.name != new_zone.name)
    return (
        old_zone.geography_type == "stop" and
        new_zone.geography_type == "stop" and
        (old_zone.name != new_zone.name or
        old_zone.stop != new_zone.stop)
    )

def update_stop(cur, new_zone):
    stop = new_zone.stop
    stmt = """
        UPDATE stops
        SET name = %s,
        location = ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326),
        status = %s, 
        capacity = %s
        WHERE 
        stop_id = %s
    """
    cur.execute(stmt, (new_zone.name, stop.location.geometry.json(), 
        json.dumps(stop.status), json.dumps(stop.capacity), str(stop.stop_id)))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="No stop with this stop_id exists.")

def no_parking_should_be_updated(old_zone, new_zone):
    return (
        old_zone.geography_type == "no_parking" and
        new_zone.geography_type == "no_parking" and
        old_zone.no_parking != new_zone.no_parking
    )

def update_no_parking(cur, new_zone):
    no_parking = new_zone.no_parking
    stmt = """
        UPDATE no_parking_policy
        SET start_date = %s, 
        end_date = %s
        WHERE geography_id = %s
    """
    cur.execute(stmt, (no_parking.start_date, no_parking.end_date, str(new_zone.geography_id)))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="No no_parking policy with this geography_id exists.")
    retire_policy(cur, new_zone.geography_id)
    generate_policy(cur, new_zone)

def check_if_user_has_access(old_municipality, new_municipality, acl):
    if acl.is_admin:
        return True
    if old_municipality not in acl.municipalities:
        raise HTTPException(status_code=403, detail="User is not allowed to change municipality of this geography, check ACL.")
    if new_municipality not in acl.municipalities:
        raise HTTPException(status_code=403, detail="User is not allowed to edit zone in this municipality, check ACL.")
    return True

def update_geography(cur, old_zone, new_zone):
    print("Update geography")
    if old_zone.published:
        retire_and_create_geography(cur, new_zone, old_zone)
    else:
        update_existing_geography(cur, new_zone)

    
def retire_and_create_geography(cur, new_zone, old_zone):
    new_zone.geography_id = uuid1()
    new_zone.zone_id = create_classic_zone(cur, new_zone)
    create_geography(cur, new_zone)
    update_geography_id_stop(cur, old_zone.geography_id, new_zone.geography_id)
    update_geography_id_no_parking(cur, old_zone.geography_id, new_zone.geography_id)
    generate_policy(cur, new_zone)
    
    print("retire")
    print(str(old_zone.geography_id))
    retire_geography(cur, old_zone.geography_id)

def update_existing_geography(cur, new_zone):
    update_classic_zone(cur, new_zone)
    update_geography_record(cur, new_zone)

    
def update_classic_zone(cur, data):
    if not check_if_zone_is_valid(cur, data):
        raise HTTPException(status_code=403, detail="Zone not completely within borders municipality.")
    stmt = """
        UPDATE zones z
        SET area = ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326),
        name = %s, 
        municipality = %s
        FROM geographies g
        WHERE z.zone_id = g.zone_id
        AND g.geography_id = %s
    """
    cur.execute(stmt, (data.area.geometry.json(), data.name, data.municipality, str(data.geography_id)))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="No zone for this geography_id.")

def update_geography_record(cur, data):
    stmt = """
        UPDATE geographies
        SET name = %s,
        description = %s,
        geography_type = %s,
        effective_date = %s,
        published_date = %s,
        publish = %s
        WHERE geography_id = %s
    """
    cur.execute(stmt, (data.name, data.description, data.geography_type, 
        data.effective_date, data.published_date, data.published, str(data.geography_id)))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="No zone for this geography_id.")

def update_geography_id_stop(cur, old_geography_id, new_geography_id):
    stmt = """
        UPDATE stops
        SET geography_id = %s
        WHERE geography_id = %s
    """
    cur.execute(stmt, (str(new_geography_id), str(old_geography_id)))

def update_geography_id_no_parking(cur, old_geography_id, new_geography_id):
    stmt = """
        UPDATE no_parking_policy
        SET geography_id = %s
        WHERE geography_id = %s
    """
    cur.execute(stmt, (str(new_geography_id), str(old_geography_id)))
    retire_policy(cur, old_geography_id)
    

def publish_geography(cur, new_zone):
    new_zone.effective_date = datetime.datetime.now().astimezone()
    new_zone.published_date = datetime.datetime.now().astimezone()
    stmt = """
        UPDATE geographies
        SET effective_date = %s,
        published_date = %s,
        publish = %s
        WHERE geography_id = %s
    """
    cur.execute(stmt, (new_zone.effective_date, new_zone.published_date, True, str(new_zone.geography_id)))