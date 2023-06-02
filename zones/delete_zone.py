from fastapi import HTTPException
from db_helper import db_helper
import traceback

def delete_zone(geography_uuid, user):
    with db_helper.get_resource() as (cur, conn):
        try:
            is_published, geography_in_municipality = check_if_geometry_is_published(cur, geography_uuid)
            check_if_user_has_access(municipality=geography_in_municipality, acl=user.acl)
            delete_stops(cur, geography_uuid=geography_uuid)
            delete_no_parking(cur, geography_uuid=geography_uuid)
            # If a geography is published it can only be retired and not deleted.
            if not is_published:
                delete_geography(cur, geography_uuid=geography_uuid)
            else:
                retire_geography(cur, geography_uuid=geography_uuid)
                retire_policy(cur, geography_uuid=geography_uuid)
            conn.commit()
            return
        except HTTPException as e:
            conn.rollback()
            raise e
        except Exception as e:
            conn.rollback()
            print(traceback.format_exc())
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.\n\n" + str(e))

def check_if_geometry_is_published(cur, geography_uuid):
    stmt = """
        SELECT geography_id, publish, retire_date, municipality
        FROM geographies
        JOIN zones
        USING(zone_id)
        WHERE geography_id = %s
    """
    cur.execute(stmt, (str(geography_uuid),))
    result = cur.fetchone()
    if result == None:
        raise HTTPException(status_code=404, detail="Geography with this geography_uuid doesn't exist.")
    if result["retire_date"] != None:
        raise HTTPException(status_code=422, detail="Geography with this geography_uuid is already retired.")
    return (result["publish"], result["municipality"])


def delete_stops(cur, geography_uuid):
    stmt = """
        DELETE
        FROM stops
        WHERE geography_id = %s
    """
    cur.execute(stmt, (str(geography_uuid),))
    return

def delete_no_parking(cur, geography_uuid):
    stmt = """
        DELETE 
        FROM no_parking_policy
        WHERE geography_id = %s
    """
    cur.execute(stmt, (str(geography_uuid),))
    return

def delete_geography(cur, geography_uuid):
    stmt = """
        DELETE 
        FROM geographies
        WHERE geography_id = %s
        RETURNING zone_id
    """
    cur.execute(stmt, (str(geography_uuid),))
    zone_id = cur.fetchone()["zone_id"]
    stmt2 = """
        DELETE 
        FROM zones
        WHERE zone_id = %s
    """
    cur.execute(stmt2, (zone_id,))
    return

def retire_geography(cur, geography_uuid):
    stmt = """
        UPDATE geographies
        SET retire_date = NOW()
        WHERE geography_id = %s
    """
    cur.execute(stmt, (str(geography_uuid),))
    return

def retire_policy(cur, geography_uuid):
    print("HIER")
    stmt = """
        UPDATE policies
        SET end_date = NOW()
        WHERE geography_ref = %s
    """
    cur.execute(stmt, (str(geography_uuid),))
    return

def check_if_user_has_access(municipality, acl):
    if acl.is_admin:
        return True
    if municipality in acl.municipalities and acl.is_allowed_to_edit:
        return True
    raise HTTPException(status_code=403, detail="User is not allowed to delete geography in this municipality, check ACL.")