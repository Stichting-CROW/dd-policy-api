from pydantic import BaseModel
from typing import Optional, Dict
from geojson_pydantic import Feature, Point
import uuid

PointFeatureModel = Feature[Point, Dict]
class Stop(BaseModel):
    stop_id: Optional[str] = str(uuid.uuid1())
    location: PointFeatureModel
    status: Dict
    capacity: Dict