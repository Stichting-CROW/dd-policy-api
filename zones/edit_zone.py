from fastapi import HTTPException
from db_helper import db_helper
from mds import geography
from zones.create_zone import check_if_zone_is_valid, create_stop
from zones.delete_zone import delete_stops
from zones.get_zones import get_zone_by_id
from mds.generate_policy import generate_policy
from zones.zone import Zone, EditZone, BulkEditZone, convert_to_edit_zone, GeographyType
from zones.stop import Stop, PointFeatureModel
from authorization import access_control
from uuid import uuid1
import json
import traceback
from pydantic import BaseModel, Field
from fastapi import HTTPException
from uuid import UUID
import shapely
from modalities import Modality

class BulkEditZonesRequest(BaseModel):
    geography_ids: list[UUID]
    bulk_edit: BulkEditZone


def edit_zones(edit_zone_request: BulkEditZonesRequest,  user: access_control.User):
    with db_helper.get_resource() as (cur, conn):
        try:
            merged_zones = []
            for geography_id in edit_zone_request.geography_ids:
                new_zone = convert_to_edit_zone(edit_zone_request.bulk_edit, geography_id=geography_id)
                merged_zone = edit_single_zone(cur, new_zone=new_zone, user=user)
                merged_zones.append(merged_zone)
            conn.commit()
            return merged_zones
        except HTTPException as e:
            conn.rollback()
            raise e
        except Exception as e:
            conn.rollback()
            print(traceback.format_exc())
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details. \n\n" + str(e))

def edit_zone(new_zone: EditZone, user: access_control.User):
    with db_helper.get_resource() as (cur, conn):
        try:
            merged_zone = edit_single_zone(cur, new_zone=new_zone, user=user)
            conn.commit()
            return merged_zone
        except HTTPException as e:
            conn.rollback()
            raise e
        except Exception as e:
            conn.rollback()
            print(traceback.format_exc())
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details. \n\n" + str(e))

def edit_single_zone(cur, new_zone: EditZone, user: access_control.User):
    old_zone = get_zone_by_id(cur, new_zone.geography_id)
    return edit_old_zone(cur, old_zone, new_zone, user)

def edit_old_zone(cur, old_zone, new_zone: EditZone, user: access_control.User):
    check_if_edit_is_allowed(old_zone=old_zone, new_zone=new_zone)
    check_if_user_has_access(old_zone.municipality, user.acl)
    
    merged_zone = update_zone(cur, old_zone, new_zone, user.email)
    return merged_zone

def check_if_edit_is_allowed(old_zone: Zone, new_zone: EditZone):
    if old_zone.phase == "concept":
        return
    if new_zone.area:
        raise HTTPException(status_code=400, detail=f"It's not possible to edit area when zone is in {old_zone.phase}")
    if new_zone.name:
        raise HTTPException(status_code=400, detail=f"It's not possible to edit name when zone is in {old_zone.phase}")
    if new_zone.description:
        raise HTTPException(status_code=400, detail=f"It's not possible to edit description when zone is in {old_zone.phase}")
    if new_zone.geography_type:
        raise HTTPException(status_code=400, detail=f"It's not possible to edit geography_type when zone is in {old_zone.phase}")
    
    if new_zone.stop and new_zone.stop.location:
        raise HTTPException(status_code=400, detail=f"It's not possible to edit stop.location when zone is in {old_zone.phase}")
    return

def derive_affected_modalities_edit(old_zone: Zone, new_zone: EditZone):
    if not new_zone.affected_modalities and new_zone.geography_type != GeographyType.stop:
        return old_zone.affected_modalities

    if new_zone.geography_type != GeographyType.stop:
        return new_zone.affected_modalities
    

    if "combined" in new_zone.stop.capacity:
        return [Modality.bicycle, Modality.moped, Modality.cargo_bicycle]
    affected_modalities: list[Modality] = []
    if "moped" in new_zone.stop.capacity:
        affected_modalities.append(Modality.moped)
    if "bicycle" in new_zone.stop.capacity:
        affected_modalities.append(Modality.bicycle)
    if "cargo_bicycle" in new_zone.stop.capacity:
        affected_modalities.append(Modality.cargo_bicycle)
    if "car" in new_zone.stop.capacity:
        affected_modalities.append(Modality.car)
    return affected_modalities

def update_zone(cur, old_zone: Zone, new_zone: EditZone, email: str):
    is_new_geography_type = new_zone.geography_type and new_zone.geography_type == "stop" and old_zone.geography_type != "stop"
    if (is_new_geography_type and (new_zone.stop == None or new_zone.stop.is_virtual == None or
          new_zone.stop.status == None or new_zone.stop.capacity == None)):
        raise HTTPException(status_code=400, detail="stop object with is_virtual, status and capacity should be provided")
    
    
    if new_zone.area:
        old_zone.area = new_zone.area
    if new_zone.name:
        old_zone.name = new_zone.name
    if new_zone.description:
        old_zone.description = new_zone.description
    if new_zone.internal_id:
        old_zone.internal_id = new_zone.internal_id
    if new_zone.geography_type:
        old_zone.geography_type = new_zone.geography_type
    
    old_zone.affected_modalities = derive_affected_modalities_edit(old_zone=old_zone, new_zone=new_zone)

    # check stop fields.
    if new_zone.stop and not old_zone.stop:
        location = new_zone.stop.location
        if not location:
            point = shapely.centroid(
                    shapely.from_geojson(
                        old_zone.area.geometry.model_dump_json()
                        )
                    )
            location = {
                "type": "Feature",
                "geometry": shapely.geometry.mapping(point),
                "properties": {}
            }
        old_zone.stop = Stop(
            location=location,
            status=new_zone.stop.status,
            capacity=new_zone.stop.capacity,
            is_virtual=new_zone.stop.is_virtual
        )
    elif new_zone.stop:
        if new_zone.stop.location:
            old_zone.stop.location = new_zone.stop.location
        if new_zone.stop.is_virtual != None:
            old_zone.stop.is_virtual = new_zone.stop.is_virtual
        if new_zone.stop.status:
            old_zone.stop.status = new_zone.stop.status
        if new_zone.stop.capacity:
            old_zone.stop.capacity = new_zone.stop.capacity

    merged_zone = old_zone
    merged_zone.last_modified_by = email

    merged_zone.modified_at = update_geography(cur, merged_zone)
    update_classic_zone(cur, merged_zone)
    if merged_zone.geography_type == "stop" and is_new_geography_type:
        create_stop(cur, merged_zone)
    elif merged_zone.geography_type == "stop":
        update_stop(cur, merged_zone)
    else: 
        merged_zone.stop = None
        delete_stops(cur, merged_zone.geography_id)
    return merged_zone

def update_stop(cur, merged_zone: Zone):
    stop = merged_zone.stop
    stmt = """
        UPDATE stops
        SET name = %s,
        location = ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326),
        status = %s, 
        capacity = %s,
        is_virtual = %s
        WHERE 
        geography_id = %s
    """
    cur.execute(stmt, (merged_zone.name, stop.location.geometry.model_dump_json(), 
        json.dumps(stop.status), json.dumps(stop.capacity), stop.is_virtual, str(merged_zone.geography_id)))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="No stop with this stop_id exists.")


def check_if_user_has_access(municipality, acl):
    if acl.is_admin:
        return True
    if municipality not in acl.municipalities:
        raise HTTPException(status_code=403, detail="User is not allowed to change zones in this municipality.")
    if not acl.is_allowed_to_edit:
        raise HTTPException(status_code=403, detail="User is not allowed to edit zones.")
    return True

def update_geography(cur, merged_zone: Zone):
    update_classic_zone(cur, merged_zone)
    return update_geography_record(cur, merged_zone)

def update_classic_zone(cur, zone: Zone):
    if not check_if_zone_is_valid(cur, zone.area.geometry.model_dump_json(), zone.municipality):
        raise HTTPException(status_code=403, detail="Zone not completely within borders municipality.")
    stmt = """
        UPDATE zones
        SET area = ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326),
        name = %s
        FROM geographies
        WHERE zones.zone_id = geographies.zone_id
        AND geographies.geography_id = %s
    """
    cur.execute(stmt, (zone.area.geometry.model_dump_json(), zone.name, str(zone.geography_id)))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="No zone for this geography_id.")

def update_geography_record(cur, zone: Zone):
    stmt = """
        UPDATE geographies
        SET name = %s,
        description = %s,
        geography_type = %s,
        internal_id = %s,
        modified_at = NOW(),
        last_modified_by = %s,
        affected_modalities = %s
        WHERE geography_id = %s
        RETURNING modified_at
    """
    cur.execute(stmt, (zone.name, zone.description, zone.geography_type, zone.internal_id, zone.last_modified_by, zone.affected_modalities, str(zone.geography_id)))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="No zone for this geography_id.")
    return cur.fetchone()["modified_at"]


