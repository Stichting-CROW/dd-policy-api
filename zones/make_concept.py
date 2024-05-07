from pydantic import BaseModel, Field
from typing import Dict, Union
from uuid import UUID, uuid1
from datetime import datetime, timezone
from pydantic import AwareDatetime
from fastapi import HTTPException
from zones.get_zones import query_zone_by_id
from authorization import access_control
from db_helper import db_helper
from zones.zone import check_if_user_has_access_to_zone_based_on_municipality, Zone
from zones.create_zone import create_single_zone
from zones.get_zones import get_zone_by_id


class MakeConceptRequest(BaseModel):
    geography_ids: list[UUID]

def move_published_zone_back_to_concept(cur, old_zone: Zone, user: access_control.User):

    new_zone = old_zone.model_copy(deep=True)
    new_zone.geography_id = uuid1()
    new_zone.prev_geographies = [old_zone.geography_id]
    new_zone.published_date = None
    new_zone.effective_date = None
    new_zone = create_single_zone(
        cur=cur,
        zone=new_zone,
        user=user
    )
    stmt = """
        UPDATE geographies
        SET propose_retirement = true,
        modified_at = NOW(),
        last_modified_by = %s
        WHERE geography_id = %s
    """
    cur.execute(stmt, (user.email, old_zone.geography_id))

def move_committed_concept_back_to_concept(cur, geography_id, user: access_control.User):
    stmt = """
        UPDATE geographies
        SET effective_date = null,
        published_date = null,
        modified_at = NOW(),
        last_modified_by = %s
        WHERE geography_id = %s
    """
    cur.execute(stmt, (user.email, geography_id))

def move_committed_concept_retirement_back_to_concept(cur, geography_id, user: access_control.User):
    stmt = """
        UPDATE geographies
        SET retire_date = null,
        published_retire_date = null,
        modified_at = NOW(),
        last_modified_by = %s
        WHERE geography_id = %s
    """
    cur.execute(stmt, (user.email, geography_id))

def make_concept(cur, geography_ids: list[UUID], user: access_control.User):
    for geography_id in geography_ids:
        zone = get_zone_by_id(cur, geography_id)

        check_if_user_has_access_to_zone_based_on_municipality(zone.municipality, user.acl)


        if zone.phase not in ["committed_concept", "published", "active", "committed_retirement_concept"]:
            raise HTTPException(400, f"it's not possible to make a concept of this zone {geography_id} is not in a committed_concept, published or active phase.")
        if zone.phase == "committed_concept":
            move_committed_concept_back_to_concept(cur, zone.geography_id, user)
        elif zone.phase == "committed_retirement_concept":
            move_committed_concept_retirement_back_to_concept(cur, zone.geography_id, user)
        elif zone.phase in ["published", "active"]:
            move_published_zone_back_to_concept(cur, zone, user)




def make_concept_route(make_concept_request: MakeConceptRequest, current_user: access_control.User):
     with db_helper.get_resource() as (cur, conn):
        try:
            make_concept(cur, make_concept_request.geography_ids, current_user)
            conn.commit()
            return
        except HTTPException as e:
            conn.rollback()
            raise e
        except Exception as e:
            conn.rollback()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")
