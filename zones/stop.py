from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict
from geojson_pydantic import Feature, Point
from uuid import UUID, uuid1

class RealtimeStopData(BaseModel):
    last_reported: int
    status: Dict[str, bool]
    num_vehicles_available: Dict[str, int] = {}
    num_vehicles_disabled: Dict[str, int] = {}
    num_places_available: Dict[str, int] = {}

def has_positive_capacity(capacity: Dict[str, int] | None) -> bool:
    return bool(capacity) and any(value is not None and value > 0 for value in capacity.values())

def validate_capacity_is_not_negative(capacity: Dict[str, int] | None) -> Dict[str, int] | None:
    if capacity is None:
        return None
    for modality, value in capacity.items():
        if value < 0:
            raise ValueError(f"capacity for '{modality}' cannot be negative.")
    return capacity

PointFeatureModel = Feature[Point, Dict]
class Stop(BaseModel):
    stop_id: UUID | None = Field(default_factory=uuid1)
    location: PointFeatureModel
    status: Dict[str, bool]
    capacity: Dict[str, int]
    realtime_data: RealtimeStopData | None = None
    is_virtual: bool

    @field_validator("capacity")
    @classmethod
    def capacity_cannot_be_negative(cls, capacity):
        return validate_capacity_is_not_negative(capacity)

class EditStop(BaseModel):
    location: PointFeatureModel | None = None
    is_virtual: bool | None = None
    status: Dict[str, bool] | None = None
    capacity: Dict[str, int] | None = None

    @field_validator("capacity")
    @classmethod
    def capacity_cannot_be_negative(cls, capacity):
        return validate_capacity_is_not_negative(capacity)

class BulkEditStop(BaseModel):
    is_virtual: bool | None = None
    status: Dict[str, bool] | None = None
    capacity: Dict[str, int] | None = None

    @field_validator("capacity")
    @classmethod
    def capacity_cannot_be_negative(cls, capacity):
        return validate_capacity_is_not_negative(capacity)
