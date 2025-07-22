from pydantic import BaseModel, field_validator
from typing import Optional
import isodate
from modalities import Modality
from datetime import date, timedelta

class PermitLimit(BaseModel):
    permit_limit_id: Optional[int] = None
    municipality: str
    system_id: str
    modality: Modality
    effective_date: date
    end_date: Optional[date] = None
    minimum_vehicles: Optional[int] = None
    maximum_vehicles: Optional[int] = None
    minimal_number_of_trips_per_vehicle: Optional[float] = None
    max_parking_duration: Optional[timedelta] = None  # in days
    future_permit: 'Optional[PermitLimit]' = None


    @field_validator('max_parking_duration', mode='before')
    @classmethod
    def parse_iso8601_duration(cls, value):
        if isinstance(value, str):
            return isodate.parse_duration(value)
        return value
