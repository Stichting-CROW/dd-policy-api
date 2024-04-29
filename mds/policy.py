
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
import datetime
from uuid import UUID, uuid1
import json
from datetime import timezone, datetime
import zones.zone as zone

class Rule(BaseModel):
    name: str
    rule_id: UUID = Field(default_factory=uuid1)
    rule_type: str
    geographies: List[UUID]
    states: Dict[str, List[str]]
    rule_units: Optional[str]
    minimum: Optional[int] = None
    maximum: Optional[int]

class Policy(BaseModel):
    policy_id: UUID = Field(default_factory=uuid1)
    start_date: datetime
    end_date: Optional[datetime]
    published_date: datetime = Field(default_factory=lambda: datetime.now().astimezone())
    name: str
    description: str
    rules: List[Rule]
    
    class Config:
        json_encoders = {
            datetime: lambda v: int(v.replace(tzinfo=timezone.utc).timestamp() * 1000),
        }

def convert_policy_row(zone):
    return Policy(
        policy_id=zone["geography_id"],
        start_date=zone["effective_date"],
        end_date=zone["retire_date"],
        published_date=zone["published_date"],
        rules=[Rule(
            name = "Disallow parking",
            description = "This rule forbids parking.",
            rule_type = "count",
            rule_units = "devices",
            geographies = [zone["geography_id"]],
            states = {"available": ["trip_end"]},
            maximum = 0
        )],
        name="This policy disallow parking",
        description="Parking is not allowed in this geography"
    )