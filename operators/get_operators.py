from db_helper import db_helper
from model.operator import Operator, OperatorResponse
from fastapi import HTTPException

def get_operators():
    with db_helper.get_resource() as (cur, conn):
        try:
            query_rows = query_operators(cur)
            operators = convert_operators(query_rows)
            return OperatorResponse(
                operators=operators
            )
        except HTTPException as e:
            conn.rollback()
            raise e
        except Exception as e:
            conn.rollback()
            print(e)
            raise HTTPException(status_code=500, detail="DB problem, check server log for details.")

def convert_operators(rows):
    operators = []
    print(rows)
    for row in rows:
        operators.append(Operator(
            system_id=row["system_id"],
            name=row["name"],
            color=row["color"],
            operator_url=row["operator_url"],
            logo_url=row["logo_url"]
        ))
    return operators

def query_operators(cur):
    cur.execute("""
        SELECT system_id, name, color, operator_url, logo_url
        FROM operators
        ORDER BY name;
                """)
    return cur.fetchall()