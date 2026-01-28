from pydantic import BaseModel
from typing import Optional
from modalities import Modality
from model import operator
from model.municipality import Municipality
from model.kpi import KPIThreshold


class KPICurrentStats(BaseModel):
    """Current statistics for KPI compliance checking."""
    number_of_vehicles_in_public_space: int
    number_of_vehicles_in_public_space_parked_too_long: int
    number_of_rentals_per_vehicle: Optional[float] = None


class KPIOverview(BaseModel):
    """Overview of KPIs for a specific operator/municipality combination."""
    municipality: Optional[Municipality] = None
    operator: operator.Operator
    threshold: Optional[KPIThreshold] = None
    stats: Optional[KPICurrentStats] = None


# Backwards compatibility aliases
PermitLimitStats = KPICurrentStats
PermitLimitOverview = KPIOverview