from fastapi import HTTPException
from db_helper import db_helper
import traceback
import zones.get_zones as get_zones
from uuid import UUID

from pydantic import BaseModel

class DeleteZonesRequest(BaseModel):
    geography_ids: list[UUID]

def delete_zones(request: DeleteZonesRequest, user):
    with db_helper.get_resource() as (cur, conn):
        try:
            for geography_id in request.geography_ids:
                delete_single_zone(cur, geography_id, user)
            conn.commit()
            return
        except HTTPException as e:
            conn.rollback()
            raise e
        except Exception as e:
            conn.rollback()
            print(traceback.format_exc())
            print(e)
            raise e

def delete_zone(geography_uuid, user):
    with db_helper.get_resource() as (cur, conn):
        try:
            delete_single_zone(cur, geography_uuid, user)
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

def delete_single_zone(cur, geography_uuid: UUID, user):
    zone = get_zones.get_zone_by_id(cur, geography_uuid=geography_uuid)
    check_if_user_has_access(municipality=zone.municipality, acl=user.acl)
    # If a geography is published it can only be retired and not deleted.
    if zone.phase == "concept":
        delete_stops(cur, geography_uuid=geography_uuid)
        delete_geography(cur, geography_uuid=geography_uuid)
    else:
        raise HTTPException(status_code=400, detail=f"It's not possible to delete a zone that is in another phase then concept, geography_id: {geography_uuid}")

def delete_stops(cur, geography_uuid):
    stmt = """
        DELETE
        FROM stops
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

def check_if_user_has_access(municipality, acl):
    if acl.is_admin:
        return True
    if municipality in acl.municipalities and acl.is_allowed_to_edit:
        return True
    raise HTTPException(status_code=403, detail="User is not allowed to delete geography in this municipality, check ACL.")