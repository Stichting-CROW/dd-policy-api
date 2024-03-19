from pydantic import BaseModel, Field
from typing import Optional, Dict
from geojson_pydantic import Feature, Polygon
import zones.stop as stop_mod
import zones.no_parking as no_parking_mod
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
    
PolygonFeatureModel = Feature[Polygon, Dict]
class Zone(BaseModel):
    zone_id: int | None = None
    area: PolygonFeatureModel
    name: str
    municipality: str
    # variables relating to geography because there is a 1 to 1 relation
    geography_id: UUID | None = Field(default_factory=uuid1)
    description: str
    geography_type: GeographyType
    effective_date: datetime | None = None
    published_date: datetime | None = None
    retire_date: datetime | None = None
    stop: stop_mod.Stop | None = None
    no_parking: no_parking_mod.NoParking | None = None
    published: bool | None = False

def convert_zones(zone_rows):
    results = []
    for zone_row in zone_rows: 
        results.append(convert_zone(zone_row))
    return results

def convert_zone(zone_row):
    result = Zone(
        zone_id=zone_row["zone_id"],
        area=zone_row["area"],
        name=zone_row["name"],
        municipality=zone_row["municipality"],
        geography_id=zone_row["geography_id"],
        description=zone_row["description"],
        geography_type=zone_row["geography_type"],
        effective_date=str(zone_row["effective_date"]),
        published_date=str(zone_row["published_date"]),
        retire_date=zone_row["retire_date"],
        published=zone_row["publish"]
    )
    if result.geography_type == "stop":
        result.stop = convert_stop(stop_row=zone_row)
    elif result.geography_type == "no_parking":
        result.no_parking = convert_no_parking(no_parking_row=zone_row)
    return result

def convert_stop(stop_row):
    return stop_mod.Stop(
        stop_id=stop_row["stop_id"],
        location=stop_row["location"],
        status=stop_row["status"],
        capacity=stop_row["capacity"]
    )

def convert_no_parking(no_parking_row):
    return no_parking_mod.NoParking(
        start_date=no_parking_row["start_date"],
        end_date=no_parking_row["end_date"]
    )

def set_realtime_data(result, zone):
    if result == None:
        return zone
    stop_dict = json.loads(result)
    mdsStop = MDSStop(**stop_dict)
    zone.stop.realtime_data = stop.RealtimeStopData(
        last_reported = mdsStop.last_reported,
        status = mdsStop.status,
        num_vehicles_available = mdsStop.num_vehicles_available,
        num_vehicles_disabled = mdsStop.num_vehicles_disabled,
        num_places_available = mdsStop.num_places_available
    )
    return zone

def look_up_realtime_data(zones):
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
        