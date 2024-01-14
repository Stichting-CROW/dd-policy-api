from pydantic import BaseModel, Field

from typing import Optional, Dict
from geojson_pydantic import Feature, Point
from uuid import UUID, uuid1
from datetime import datetime
from geojson_pydantic import FeatureCollection, Feature, geometries


class ServiceArea(BaseModel):
    service_area_version_id: int
    municipality: str
    operator: str
    valid_from: datetime
    valid_until: Optional[datetime]
    geometries: FeatureCollection

# PointFeatureModel = Feature[Point, Dict]
# class Stop(BaseModel):
#     stop_id: Optional[UUID] = Field(default_factory=uuid1)
#     location: PointFeatureModel
#     status: Dict[str, bool]
#     capacity: Dict[str, int]
#     realtime_data: Optional[RealtimeStopData]

