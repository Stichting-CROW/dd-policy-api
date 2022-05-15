
import jwt
from pydantic import BaseModel
from typing import Union
from fastapi import Header
from db_helper import db_helper
from fastapi import HTTPException

class ACL(BaseModel):
    is_admin: bool
    municipalities: set

class User(BaseModel):
    token: str
    acl: ACL

def get_user_acl(cur, token):
    encoded_token = token.split(" ")[1]
    # Verification is performed by kong (reverse proxy), 
    # therefore token is not verified for a second time so that the secret is only stored there.
    print(encoded_token)
    result = jwt.decode(encoded_token, options={"verify_signature": False})
    print(result)
    return query_acl(cur, result["email"])

async def get_current_user(authorization: Union[str, None] = Header(None)):
    with db_helper.get_resource() as (cur, _):
        try:
            result = get_user_acl(cur, authorization)
            print(result)
            return User(
                token=authorization,
                acl=result
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")

def query_acl(cur, email):
    stmt = """
    SELECT username, is_admin
    FROM acl
    WHERE username=%s;
    """

    cur.execute(stmt, (email,))
    if cur.rowcount < 1:
        raise HTTPException(status_code=403, detail="User is not known in ACL")
    
    user = cur.fetchone()
    acl_user = ACL(
        is_admin = user["is_admin"],
        municipalities = retrieve_municipalities(cur, email)
    )
    return acl_user

def retrieve_municipalities(cur, email):
    stmt = """SELECT acl_municipalities.municipality as municipality_code
        FROM acl_municipalities
        WHERE username = %s"""
    cur.execute(stmt, (email,))
    results = cur.fetchall()
    municipalities = set()
    for item in results:
        municipalities.add(item["municipality_code"])
    print(municipalities)
    return municipalities
