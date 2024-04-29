from pydantic import BaseModel, Field
from typing import Dict, Union
from uuid import UUID, uuid1
from datetime import datetime, timezone
from pydantic import AwareDatetime
from fastapi import HTTPException
from zones.get_zones import get_zone_by_id
from authorization import access_control
from db_helper import db_helper
from zones.zone import check_if_user_has_access_to_zone_based_on_municipality

class PublishZoneRequest(BaseModel):
    geography_ids: list[UUID]
    publish_on: AwareDatetime
    effective_on: AwareDatetime


def publish_zones_query(cur, publish_zones_request: PublishZoneRequest, geography_ids):
    if len(geography_ids) == 0:
        return
    stmt = """
        UPDATE geographies
        SET effective_date = %s,
        published_date = %s,
        modified_at = NOW()
        WHERE geography_id = ANY(%s)
    """

    cur.execute(stmt, (publish_zones_request.effective_on, publish_zones_request.publish_on, geography_ids))

def publish_retire_zones_query(cur, publish_zones_request: PublishZoneRequest, geography_ids):
    if len(geography_ids) == 0:
        return
    stmt = """
        UPDATE geographies
        SET retire_date = %s,
        published_retire_date = %s,
        modified_at = NOW()
        WHERE geography_id = ANY(%s)
    """
    cur.execute(stmt, (publish_zones_request.effective_on, publish_zones_request.publish_on, geography_ids))


def publish_zones_route(publish_zone_request: PublishZoneRequest, current_user: access_control.User):
     with db_helper.get_resource() as (cur, conn):
        try:
            publish_zones(cur, publish_zone_request, current_user)
            conn.commit()
            return
        except HTTPException as e:
            conn.rollback()
            raise e
        except Exception as e:
            conn.rollback()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")

def publish_zones(cur, publish_zones_request: PublishZoneRequest, user):
    if publish_zones_request.publish_on < datetime.now(timezone.utc):
        raise HTTPException(400, "publish_on should be in the future")
    if publish_zones_request.effective_on < datetime.now(timezone.utc):
        raise HTTPException(400, "effective_on should be in the future")
    if publish_zones_request.effective_on < publish_zones_request.publish_on:
        raise HTTPException(400, "effective_on should be >= publish_on")

    to_publish = []
    to_retire = []
    # This code could be optimized
    for geography_id in publish_zones_request.geography_ids:
        zone = get_zone_by_id(cur, geography_id)
        if zone.geography_type == "monitoring":
            raise HTTPException(400, detail=f"It's not possible to publish a monitoring zone: {geography_id}")
        check_if_user_has_access_to_zone_based_on_municipality(zone.municipality, user.acl)
        if zone == None:
            raise HTTPException(404, f"zone {geography_id} doesn't exists, try again.")
        if zone.phase not in ["concept", "committed_concept", "retirement_concept", "committed_retirement_concept"]:
            raise HTTPException(400, f"it's not possible to publish (or update the publication date of this zone) because {geography_id} is not a concept or committed_concept")
        if zone.phase in ["retirement_concept", "committed_retirement_concept"]:
            to_retire.append(geography_id)
        else:
            to_publish.append(geography_id)
    
    publish_zones_query(cur, publish_zones_request, to_publish)
    publish_retire_zones_query(cur, publish_zones_request, to_retire)
