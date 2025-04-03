from pydantic import BaseModel, Field
from typing import Dict, Union
from geojson_pydantic import Feature, Polygon, MultiPolygon
import zones.stop as stop_mod
from uuid import UUID, uuid1
from enum import Enum
from datetime import datetime
from redis_helper import redis_helper
import json
from mds.stop import MDSStop

class GeographyType(str, Enum):
    monitoring = "monitoring"
    stop = "stop"
    no_parking = "no_parking"

class Phase(str, Enum):
    concept = "concept"
    retirement_concept = "retirement_concept"
    committed_concept = "committed_concept"
    committed_retire_concept = "committed_retirement_concept"
    published = "published"
    published_retirement = "published_retirement"
    active = "active"
    archived = "archived"
    
PolygonFeatureModel = Feature[Union[Polygon, MultiPolygon], Dict]
class Zone(BaseModel):
    zone_id: int | None = None
    area: PolygonFeatureModel
    name: str
    municipality: str
    # variables relating to geography because there is a 1 to 1 relation
    geography_id: UUID | None = Field(default_factory=uuid1)
    internal_id: str | None = None
    description: str
    geography_type: GeographyType
    prev_geographies: list[UUID] = []
    effective_date: datetime | None = None
    propose_retirement: bool | None = False
    published_date: datetime | None = None
    published_retire_date: datetime | None = None
    retire_date: datetime | None = None
    stop: stop_mod.Stop | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    created_by: str | None = None
    last_modified_by: str | None = None
    phase: str | None = None

class EditZone(BaseModel):
    geography_id: UUID
    area: PolygonFeatureModel | None = None
    name: str | None = None
    # variables relating to geography because there is a 1 to 1 relation
    internal_id: str | None = None
    description: str | None = None
    geography_type: GeographyType | None = None
    stop: stop_mod.EditStop | None = None

class BulkEditZone(BaseModel):
    geography_type: GeographyType | None = None
    stop: stop_mod.EditStop | None = None

def convert_to_edit_zone(bulk_edit_zone: BulkEditZone, geography_id: UUID):
    stop = None
    if bulk_edit_zone.stop:
        stop = stop_mod.EditStop(
            status=bulk_edit_zone.stop.status,
            capacity=bulk_edit_zone.stop.capacity,
            is_virtual=bulk_edit_zone.stop.is_virtual,
        )
    return EditZone(
        geography_id=geography_id,
        geography_type=bulk_edit_zone.geography_type,
        stop=stop,
    ) 

def convert_zones(zone_rows, include_private_data=False):
    results = []
    for zone_row in zone_rows: 
        print(zone_row)
        results.append(convert_zone(zone_row, include_private_data))
    return results

def convert_zone(zone_row, include_private_data=False):
    result = Zone(
        zone_id=zone_row["zone_id"],
        internal_id=zone_row["internal_id"],
        area=zone_row["area"],
        name=zone_row["name"],
        municipality=zone_row["municipality"],
        geography_id=zone_row["geography_id"],
        description=zone_row["description"],
        geography_type=zone_row["geography_type"],
        effective_date=zone_row["effective_date"],
        published_date=zone_row["published_date"],
        retire_date=zone_row["retire_date"],
        published_retire_date=zone_row["published_retire_date"],
        stop=None,
        created_at=zone_row["created_at"],
        modified_at=zone_row["modified_at"],
        phase=zone_row["phase"]
    )
    if zone_row["prev_geographies"]:
        result.prev_geographies = zone_row["prev_geographies"]
    if result.geography_type == "stop":
        result.stop = convert_stop(stop_row=zone_row)
    if include_private_data:
        result.created_by=zone_row["created_by"]
        result.last_modified_by=zone_row["last_modified_by"]
    return result

def convert_stop(stop_row):
    return stop_mod.Stop(
        stop_id=stop_row["stop_id"],
        location=stop_row["location"],
        status=stop_row["status"],
        capacity=stop_row["capacity"],
        is_virtual=stop_row["is_virtual"],
    )

def set_realtime_data(result, zone):
    if result == None:
        return zone
    stop_dict = json.loads(result)
    mdsStop = MDSStop(**stop_dict)
    zone.stop.realtime_data = stop_mod.RealtimeStopData(
        last_reported = mdsStop.last_reported,
        status = mdsStop.status,
        num_vehicles_available = mdsStop.num_vehicles_available,
        num_vehicles_disabled = mdsStop.num_vehicles_disabled,
        num_places_available = mdsStop.num_places_available
    )
    return zone

def look_up_realtime_data(zones: list[Zone]):
    with redis_helper.get_resource() as r:
        pipe = r.pipeline()
        for zone in zones:
            if zone.stop != None: 
                pipe.get("stop:" + str(zone.stop.stop_id))
        results = pipe.execute()

        result_index = 0
        for zone_index, zone in enumerate(zones):
            if zone.stop != None:
                zones[zone_index] = set_realtime_data(results[result_index], zone)
                result_index += 1
    return zones

def check_if_user_has_access_to_zone_based_on_municipality(municipality, acl):
    if acl.is_admin:
        return True
    if not acl.is_allowed_to_edit:
        raise HTTPException(status_code=403, detail="User is not allowed to modify zones in this municipality, check ACL.")
    if municipality in acl.municipalities:
        return True
    raise HTTPException(status_code=403, detail="User is not allowed to modify zones in this municipality, check ACL.")