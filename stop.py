from pydantic import BaseModel
from typing import Optional, Dict
from geojson_pydantic import Feature, Point
import uuid

    # zone_id: int
    # area: Feature
    # name: str
    # municipality: str
    # # variables relating to geography because there is a 1 to 1 relation
    # geography_id: str
    # description: str
    # geography_type: str
    # effective_date: Optional(str)
    # published_date: Optional(str)
    # retire_data: Optional(str)

PointFeatureModel = Feature[Point, Dict]
class Stop(BaseModel):
    stop_id: Optional[str] = str(uuid.uuid1())
    location: PointFeatureModel
    status: Dict
    capacity: Dict

# CREATE TABLE stops (
# 	stop_id UUID NOT NULL,
# 	name VARCHAR(255) NOT NULL,
# 	location GEOMETRY NOT NULL,
# 	status JSONB NOT NULL,
# 	capacity JSONB NOT NULL,
# 	geography_id NOT NULL
# );