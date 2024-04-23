from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel

from authorization import access_control
from db_helper import db_helper
from zones.get_zones import get_zone_by_id
from zones.zone import check_if_user_has_access_to_zone_based_on_municipality


class ProposeRetirementRequest(BaseModel):
    geography_ids: list[UUID]
    undo: bool = False


def undo_propose_retirement(cur, geography_ids: list[UUID], user: access_control.User):
    for geography_id in geography_ids:
        zone = get_zone_by_id(cur, geography_id)

        check_if_user_has_access_to_zone_based_on_municipality(zone.municipality, user.acl)

        if zone.phase not in ["retirement_concept", "committed_retirement_concept"]:
            raise HTTPException(400, f"it's not possible to undo a propose retirement for zone, {geography_id} should be in retirement_concept or committed_retirement_concept")

        undo_propose_retirement_query(cur, zone.geography_id, user)


def undo_propose_retirement_query(cur, geography_id, user: access_control.User):
    stmt = """
        UPDATE geographies
        SET retire_date = null,
        published_retire_date = null,
        modified_at = NOW(),
        propose_retirement = false,
        last_modified_by = %s
        WHERE geography_id = %s
    """
    cur.execute(stmt, (user.email, geography_id))

def propose_retirement(cur, geography_ids: list[UUID], user: access_control.User):
    for geography_id in geography_ids:
        zone = get_zone_by_id(cur, geography_id)

        check_if_user_has_access_to_zone_based_on_municipality(zone.municipality, user.acl)

        if zone.phase not in ["published", "active"]:
            raise HTTPException(400, f"it's not possible to propose retirement for zone, {geography_id} should be in published or active phase.")

        propose_retirement_query(cur, zone.geography_id, user)

def propose_retirement_query(cur, geography_id, user: access_control.User):
    stmt = """
        UPDATE geographies
        SET retire_date = null,
        published_retire_date = null,
        modified_at = NOW(),
        propose_retirement = true,
        last_modified_by = %s
        WHERE geography_id = %s
    """
    cur.execute(stmt, (user.email, geography_id))

def propose_retirement_route(propose_retirement_request: ProposeRetirementRequest, current_user: access_control.User):
     with db_helper.get_resource() as (cur, conn):
        try:
            if not propose_retirement_request.undo:
                propose_retirement(cur, propose_retirement_request.geography_ids, current_user)
            else:
                undo_propose_retirement(cur, propose_retirement_request.geography_ids, current_user)
            conn.commit()
            return
        except HTTPException as e:
            conn.rollback()
            raise e
        except Exception as e:
            conn.rollback()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")
