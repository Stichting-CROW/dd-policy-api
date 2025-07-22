from pydantic import BaseModel

from typing import Optional
from datetime import datetime
from geojson_pydantic import FeatureCollection
from modalities import Modality

class GenerateServiceAreaRequest(BaseModel):
    service_area: FeatureCollection
    modality: Modality
    effective_date: datetime
    include_microhubs_in_service_area: bool = False

class GenerateServiceAreaResponse(BaseModel):
    modality: Modality
    generated_service_area: FeatureCollection
    microhubs: Optional[FeatureCollection] = None

def generate_service_area(
    service_area: GenerateServiceAreaRequest
):
    return GenerateServiceAreaResponse(
        generated_service_area=service_area.service_area,
        modality=service_area.modality
    )