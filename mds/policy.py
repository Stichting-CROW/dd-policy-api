
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, parse_obj_as
import datetime
from uuid import UUID, uuid1
import json
from datetime import timezone

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
    start_date: datetime.datetime
    end_date: Optional[datetime.datetime]
    published_date: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now().astimezone())
    name: str
    description: str
    rules: List[Rule]
    municipality: str

def convert_policy_row(row):
    # rules_json = json.loads(row["rules"])
    rules = parse_obj_as(List[Rule], row["rules"])
    return Policy(
        policy_id=row["policy_id"],
        start_date=convert_datetime_to_millis(row["start_date"]),
        end_date=convert_datetime_to_millis(row["end_date"]),
        published_date=convert_datetime_to_millis(row["published_date"]),
        rules=rules,
        name=row["name"],
        description=row["description"],
        municipality=row["gm_code"]
    )

def convert_datetime_to_millis(dt):
    if dt == None:
        return None
    return dt.replace(tzinfo=timezone.utc).timestamp() * 1000