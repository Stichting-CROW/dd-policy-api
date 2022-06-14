from pydantic import BaseModel, Field
from typing import Optional, Dict
from geojson_pydantic import Feature, Point
from uuid import UUID, uuid1

class RealtimeStopData(BaseModel):
    last_reported: int
    status: Dict[str, bool]
    num_vehicles_available: Dict[str, int] = {}
    num_vehicles_disabled: Dict[str, int] = {}
    num_places_available: Dict[str, int] = {}

PointFeatureModel = Feature[Point, Dict]
class Stop(BaseModel):
    stop_id: Optional[UUID] = Field(default_factory=uuid1)
    location: PointFeatureModel
    status: Dict[str, bool]
    capacity: Dict[str, int]
    realtime_data: Optional[RealtimeStopData]

