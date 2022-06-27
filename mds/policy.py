
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, parse_obj_as
import datetime
from uuid import UUID, uuid1
import json
from datetime import timezone, datetime

class Rule(BaseModel):
    name: str
    rule_id: UUID = Field(default_factory=uuid1)
    rule_type: str
    geographies: List[UUID]
    states: Dict[str, List[str]]
    rule_units: Optional[str]
    minimum: Optional[int]
    maximum: Optional[int]

class Policy(BaseModel):
    policy_id: UUID = Field(default_factory=uuid1)
    start_date: datetime
    end_date: Optional[datetime]
    published_date: datetime = Field(default_factory=lambda: datetime.now().astimezone())
    name: str
    description: str
    rules: List[Rule]
    municipality: str
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.replace(tzinfo=timezone.utc).timestamp() * 1000,
        }

def convert_policy_row(row):
    # rules_json = json.loads(row["rules"])
    rules = parse_obj_as(List[Rule], row["rules"])
    return Policy(
        policy_id=row["policy_id"],
        start_date=row["start_date"],
        end_date=row["end_date"],
        published_date=row["published_date"],
        rules=rules,
        name=row["name"],
        description=row["description"],
        municipality=row["gm_code"]
    )