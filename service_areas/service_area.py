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

class ServiceAreaVersion(BaseModel):
    service_area_version_id: int
    municipality: str
    operator: str
    valid_from: datetime
    valid_until: Optional[datetime]
