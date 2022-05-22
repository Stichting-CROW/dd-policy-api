from pydantic import BaseModel, Field
from typing import Optional, Dict
from geojson_pydantic import Feature, Polygon
import zones.stop as stop
import zones.no_parking as no_parking
from uuid import UUID, uuid1
from enum import Enum

class GeographyType(str, Enum):
    monitoring = "monitoring"
    stop = "stop"
    no_parking = "no_parking"
    
PolygonFeatureModel = Feature[Polygon, Dict]
class Zone(BaseModel):
    zone_id: Optional[int]
    area: PolygonFeatureModel
    name: str
    municipality: str
    # variables relating to geography because there is a 1 to 1 relation
    geography_id: Optional[UUID] = Field(default_factory=uuid1)
    description: str
    geography_type: GeographyType
    effective_date: Optional[str]
    published_date: Optional[str]
    retire_data: Optional[str]
    stop: Optional[stop.Stop]
    no_parking: Optional[no_parking.NoParking]
    published: Optional[bool] = False

def convert_zones(zone_rows):
    results = []
    for zone_row in zone_rows: 
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
            retire_data=zone_row["retire_date"],
            published=zone_row["publish"]
        )
        if result.geography_type == "stop":
            result.stop = convert_stop(stop_row=zone_row)
        elif result.geography_type == "no_parking":
            result.no_parking = convert_no_parking(no_parking_row=zone_row)
        results.append(result)
    return results

def convert_stop(stop_row):
    return stop.Stop(
        stop_id=stop_row["stop_id"],
        location=stop_row["location"],
        status=stop_row["status"],
        capacity=stop_row["capacity"]
    )

def convert_no_parking(no_parking_row):
    return no_parking.NoParking(
        start_date=no_parking_row["start_date"],
        end_date=no_parking_row["end_date"]
    )