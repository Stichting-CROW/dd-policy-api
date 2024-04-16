
import jwt
from pydantic import BaseModel
from typing import Union, Optional
from fastapi import Header
from db_helper import db_helper
from fastapi import HTTPException

class ACL(BaseModel):
    is_admin: bool
    is_allowed_to_edit: bool
    municipalities: Optional[set] = set()

class User(BaseModel):
    email: str
    token: str
    acl: ACL

def get_user_acl(cur, token):
    encoded_token = token.split(" ")[1]
    # Verification is performed by kong (reverse proxy), 
    # therefore token is not verified for a second time so that the secret is only stored there.
    result = jwt.decode(encoded_token, options={"verify_signature": False})
    return query_acl(cur, result["email"]), result["email"]

async def get_current_user(authorization: Union[str, None] = Header(None)):
    if not authorization:
        raise HTTPException(401, "authorization header missing.")
    with db_helper.get_resource() as (cur, _):
        try:
            result, email = get_user_acl(cur, authorization)
            return User(
                email=email,
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
    SELECT user_id, type_of_organisation, 
    privileges, data_owner_of_municipalities 
    FROM user_account 
    JOIN organisation USING(organisation_id) 
    WHERE user_id = %s;
    """

    cur.execute(stmt, (email,))
    if cur.rowcount < 1:
        raise HTTPException(status_code=403, detail="User is not known in ACL")
    
    user = cur.fetchone()
    is_allowed_to_edit = user["type_of_organisation"] == "ADMIN" or "MICROHUB_EDIT" in user["privileges"]
    acl_user = ACL(
        is_admin = user["type_of_organisation"] == "ADMIN",
        municipalities = user["data_owner_of_municipalities"],
        is_allowed_to_edit=is_allowed_to_edit
    )
    return acl_user
