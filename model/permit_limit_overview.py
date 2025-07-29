from pydantic import BaseModel
from pydantic import BaseModel, field_validator
from typing import Optional
import isodate
from modalities import Modality
from model import operator
from model.municipality import Municipality
from datetime import date, timedelta
from model.permit_limit import PermitLimit

class PermitLimitStats(BaseModel):
    number_of_vehicles_in_public_space: int
    number_of_vehicles_in_public_space_parked_to_long: int
    number_of_rentals_per_vehicle: float | None = None


class PermitLimitOverview(BaseModel):
    municipality:Municipality | None = None 
    operator: operator.Operator
    permit_limit: PermitLimit | None = None
    stats: PermitLimitStats | None = None

