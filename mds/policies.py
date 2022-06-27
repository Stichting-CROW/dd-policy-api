from sre_constants import OP_IGNORE
from db_helper import db_helper
from fastapi import HTTPException
import time
from datetime import datetime, timezone

from pydantic import BaseModel
from typing import List
from mds.policy import Policy, convert_policy_row

class PoliciesData(BaseModel):
    policies: List[Policy]

class MDSPolicies(BaseModel):
    version: str = "1.2.0"
    updated: int
    data: PoliciesData

    class Config:
        json_encoders = {
            datetime: lambda v: int(v.replace(tzinfo=timezone.utc).timestamp() * 1000),
        }

def get_policies(municipality):
    with db_helper.get_resource() as (cur, _):
        try:
            result = query_policies(cur, municipality)
            return generate_policies_response(result=result)
        except Exception as e:
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")

def get_policy(policy_uuid):
    with db_helper.get_resource() as (cur, _):
        try:
            result = query_policy(cur, policy_uuid)
            return generate_policies_response(result=result)
        except Exception as e:
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")


def query_policies(cur, municipality):
    stmt = """
        SELECT policy_id, start_date, end_date, published_date, rules,
        gm_code, name, description
        FROM policies
        WHERE ((true = %s) or gm_code = %s)
        AND (end_date is null or end_date > NOW())
        ORDER BY start_date
    """
    cur.execute(stmt, (municipality == None, municipality))
    return cur.fetchall()

def query_policy(cur, policy_id):
    stmt = """
        SELECT policy_id, start_date, end_date, published_date, rules,
        gm_code, name, description
        FROM policies
        WHERE policy_id = %s
    """
    cur.execute(stmt, (str(policy_id),))
    return cur.fetchall()

def generate_policies_response(result):
    data = PoliciesData(policies = list(map(convert_policy_row, result)))
    return MDSPolicies(
        updated=time.time_ns() // 1_000_000,
        data = data
    )