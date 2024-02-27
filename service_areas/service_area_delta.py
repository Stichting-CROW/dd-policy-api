from pydantic import BaseModel

from typing import Optional
from datetime import datetime
from geojson_pydantic import FeatureCollection

class ServiceAreaDelta(BaseModel):
    service_area_version_id: int
    previous_service_area_version_id: Optional[int]
    timestamp: datetime
    added_geometries: Optional[FeatureCollection]
    removed_geometries: Optional[FeatureCollection]
    unchanched_geometries: Optional[FeatureCollection]