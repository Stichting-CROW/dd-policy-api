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
    stop_id: UUID | None = Field(default_factory=uuid1)
    location: PointFeatureModel
    status: Dict[str, bool]
    capacity: Dict[str, int]
    realtime_data: RealtimeStopData | None = None
    is_virtual: bool

class EditStop(BaseModel):
    location: PointFeatureModel | None = None
    is_virtual: bool | None = None
    status: Dict[str, bool] | None = None
    capacity: Dict[str, int] | None = None

class BulkEditStop(BaseModel):
    is_virtual: bool | None = None
    status: Dict[str, bool] | None = None
    capacity: Dict[str, int] | None = None