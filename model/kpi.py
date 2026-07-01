from pydantic import BaseModel, field_validator
from typing import Optional, Literal
from datetime import date, timedelta
from modalities import Modality, PropulsionType
import isodate


class KPIDescription(BaseModel):
    """Describes a KPI type with its metadata."""
    kpi_key: str
    bound: Literal["upper", "lower"]
    unit: Literal["number", "percentage"]
    precision: Optional[int] = 0
    title: str
    description: str
    bound_description: str


class KPIThresholdValue(BaseModel):
    """A single threshold value for a specific KPI."""
    kpi_key: str
    threshold: Optional[float] = None




# =============================================================================
# KPI Runtime Values - For reporting and compliance checking
# =============================================================================

class KPIValue(BaseModel):
    """A single measurement/threshold pair for a specific date."""
    date: date
    measured: float
    threshold: Optional[float] = None
    complies: Optional[bool] = None


class KPI(BaseModel):
    """A KPI with its values and statistics."""
    kpi_key: str
    granularity: Literal["day", "week", "month"] = "day"
    values: list[KPIValue] = []


class GeometryModalityOperatorKPI(BaseModel):
    """KPIs for a specific operator and form factor combination."""
    operator: str  # system_id
    form_factor: Modality
    propulsion_type: PropulsionType
    geometry_ref: Optional[str] = None
    kpis: list[KPI] = []


class KPIReport(BaseModel):
    """A complete KPI report with descriptions and operator/modality data."""
    performance_indicator_description: list[KPIDescription] = []
    municipality_modality_operators: list[GeometryModalityOperatorKPI] = []



# # =============================================================================
# # Predefined KPI Descriptions
# # =============================================================================

STANDARD_KPI_DESCRIPTIONS = [
    KPIDescription(kpi_key="vehicle_cap", bound="upper", unit="number", title="Aantal onverhuurde voertuigen", description="Het maximale aantal onverhuurde (defect, gereserveerd en te huur bij elkaar opgeteld) voertuigen in openbare ruimte op een dag. Dit is de maximale waarde van het aantal voertuigen op 6 tijdstippen.", bound_description="Het maximale aantal voertuigen dat geparkeerd mag zijn in de gemeente.", precision=0),
    KPIDescription(kpi_key="minimal_number_of_available_vehicles", bound="lower", unit="number", title="Beschikbare voertuigen", description="Het minimale aantal voertuigen dat beschikbaar is.", bound_description="Het minimale aantal voertuigen dat beschikbaar moet zijn in de gemeente.", precision=0),
    KPIDescription(kpi_key="number_of_wrongly_parked_vehicles", bound="upper", unit="number", title="Voertuigen in verbodsgebieden", description="Het aantal voertuigen dat op een dag verkeerd geparkeerd staat.", bound_description="Het maximale aantal verkeerd geparkeerde voertuigen dat is toegestaan per dag.", precision=0),
    KPIDescription(kpi_key="percentage_parked_longer_then_24_hours", bound="upper", unit="percentage", title="Parkeerduur > 1 dag", description="Het percentage van voertuigen dat langer dan 24 uur geparkeerd is.", bound_description="Het maximale percentage voertuigen dat langer dan 24 uur geparkeerd mag zijn.", precision=1),
    KPIDescription(kpi_key="percentage_parked_longer_then_3_days", bound="upper", unit="percentage", title="Parkeerduur > 3 dagen", description="Het percentage van voertuigen dat langer dan 3 dagen geparkeerd is.", bound_description="Het maximale percentage voertuigen dat langer dan 3 dagen geparkeerd mag zijn.", precision=1),
    KPIDescription(kpi_key="percentage_parked_longer_then_7_days", bound="upper", unit="percentage", title="Parkeerduur > 7 dagen", description="Het percentage van voertuigen dat langer dan 7 dagen geparkeerd is.", bound_description="Het maximale percentage voertuigen dat langer dan 7 dagen geparkeerd mag zijn.", precision=1),
    KPIDescription(kpi_key="percentage_parked_longer_then_14_days", bound="upper", unit="percentage", title="Parkeerduur > 14 dagen", description="Het percentage van voertuigen dat langer dan 14 dagen geparkeerd is.", bound_description="Het maximale percentage voertuigen dat langer dan 14 dagen geparkeerd mag zijn.", precision=1),
    KPIDescription(kpi_key="percentage_non_operational_longer_then_1_day", bound="upper", unit="percentage", title="Kapot > 24 uur", description="Het percentage van voertuigen dat langer dan 24 uur kapot is.", bound_description="Het maximale percentage voertuigen dat langer dan 24 uur kapot mag zijn.", precision=1),
    KPIDescription(kpi_key="percentage_non_operational_longer_then_7_days", bound="upper", unit="percentage", title="Kapot > 7 dagen", description="Het percentage van voertuigen dat langer dan 7 dagen kapot is.", bound_description="Het maximale percentage voertuigen dat langer dan 7 dagen kapot mag zijn.", precision=1),
    KPIDescription(kpi_key="usage_ratio", bound="lower", unit="number", title="Verhuringen per voertuig", description="Het aantal verhuringen per voertuig op een dag, berekend als count_trips_per_day gedeeld door count_vehicles_in_public_space.", bound_description="Het minimale aantal verhuringen dat per voertuig per dag gemaakt moet worden .", precision=2)
]
