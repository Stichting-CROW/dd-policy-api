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
    
PointFeatureModel = Feature[Polygon, Dict]
class Zone(BaseModel):
    zone_id: Optional[int]
    area: PointFeatureModel
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
    publish: Optional[bool] = False
