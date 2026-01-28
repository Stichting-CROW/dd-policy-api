"""
DEPRECATED: This module is deprecated. Use model.kpi instead.

This module provides backwards compatibility aliases for the old PermitLimit model.
New code should use KPIThreshold from model.kpi.
"""
import warnings
from model.kpi import KPIThreshold

# Backwards compatibility alias
PermitLimit = KPIThreshold

warnings.warn(
    "model.permit_limit is deprecated, use model.kpi.KPIThreshold instead",
    DeprecationWarning,
    stacklevel=2
)
