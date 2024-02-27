from pydantic import BaseModel

from typing import Optional
from datetime import datetime
from geojson_pydantic import FeatureCollection


class ServiceArea(BaseModel):
    service_area_version_id: int
    municipality: str
    operator: str
    valid_from: datetime
    valid_until: Optional[datetime]
    geometries: FeatureCollection

class ServiceAreaVersion(BaseModel):
    service_area_version_id: int
    municipality: str
    operator: str
    valid_from: datetime
    valid_until: Optional[datetime]
