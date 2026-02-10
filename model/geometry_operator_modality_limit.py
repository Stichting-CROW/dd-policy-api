from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any
from datetime import date
from modalities import Modality, PropulsionType


class LimitValues(BaseModel):
    """The actual limit values stored in the limits JSONB column.
    
    These keys match the KPI indicators used in the statistics tables.
    """
    # Day statistics indicators
    vehicle_cap: Optional[int] = None  # indicator 1
    number_of_wrongly_parked_vehicles: Optional[int] = None  # indicator 6
    
    # Moment statistics indicators (percentages)
    percentage_parked_longer_then_24_hours: Optional[float] = None  # indicator 2
    percentage_parked_longer_then_3_days: Optional[float] = None  # indicator 3
    percentage_parked_longer_then_7_days: Optional[float] = None  # indicator 4
    percentage_parked_longer_then_14_days: Optional[float] = None  # indicator 5


class GeometryOperatorModalityLimit(BaseModel):
    """
    Model for geometry_operator_modality_limit table.
    
    This replaces the old permit_limit/kpi_threshold model.
    Includes optional ID for create/update operations.
    """
    geometry_operator_modality_limit_id: Optional[int] = None
    geometry_ref: str
    operator: str
    form_factor: Modality
    propulsion_type: PropulsionType
    effective_date: date
    limits: LimitValues
    
    @field_validator('form_factor', mode='before')
    @classmethod
    def validate_form_factor(cls, v):
        if isinstance(v, str):
            return Modality(v.lower())
        return v
    
    @field_validator('propulsion_type', mode='before')
    @classmethod
    def validate_propulsion_type(cls, v):
        if isinstance(v, str):
            return PropulsionType(v.lower())
        return v
    
    def to_db_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for database insertion."""
        return {
            'geometry_ref': self.geometry_ref,
            'operator': self.operator,
            'form_factor': self.form_factor.value.lower(),
            'propulsion_type': self.propulsion_type.value.lower(),
            'effective_date': self.effective_date,
            'limits': self.limits.model_dump(exclude_none=True)
        }


class GeometryOperatorModalityLimitResponse(BaseModel):
    """Response model that requires the ID."""
    geometry_operator_modality_limit_id: int
    geometry_ref: str
    operator: str
    form_factor: Modality
    propulsion_type: PropulsionType
    effective_date: date
    limits: LimitValues
    
    @field_validator('form_factor', mode='before')
    @classmethod
    def validate_form_factor(cls, v):
        if isinstance(v, str):
            return Modality(v.lower())
        return v
    
    @field_validator('propulsion_type', mode='before')
    @classmethod
    def validate_propulsion_type(cls, v):
        if isinstance(v, str):
            return PropulsionType(v.lower())
        return v
