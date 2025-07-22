from pydantic import BaseModel
from pydantic import BaseModel, field_validator
from typing import Optional
import isodate
from modalities import Modality
from datetime import date, timedelta
from model.permit_limit import PermitLimit

class PermitLimitStats(BaseModel):
    current_vehicle_count: int
    number_of_vehicles_illegally_parked_last_month: int
    duration_correct_percentage: float
    number_of_rentals_per_vehicle: float

class PermitLimitOverview(BaseModel):
    permit_limit: PermitLimit | None
    stats: PermitLimitStats | None = None

