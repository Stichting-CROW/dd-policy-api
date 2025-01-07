from pydantic import BaseModel

from typing import Optional
from datetime import datetime
from geojson_pydantic import FeatureCollection

class ServiceAreaDelta(BaseModel):
    service_area_version_id: int
    previous_service_area_version_id: int | None = None
    timestamp: datetime
    added_geometries: FeatureCollection | None = None
    removed_geometries: FeatureCollection | None = None
    unchanched_geometries: FeatureCollection | None = None