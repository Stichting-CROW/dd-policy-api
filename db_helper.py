from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import os

class DBHelper:
    def __init__(self):
        self._connection_pool = None

    def get_conn_str(self):
        # Initialisation
        conn_str = "dbname=deelfietsdashboard"
        if "dev" in os.environ:
            conn_str = "dbname=deelfietsdashboard4"

        if "ip" in os.environ:
            conn_str += " host={} ".format(os.environ['ip'])
        if "password" in os.environ:
            conn_str += " user=deelfietsdashboard password={}".format(os.environ['password'])
        return conn_str

    def initialize_connection_pool(self):
        conn_str = self.get_conn_str()
        self._connection_pool = pool.ThreadedConnectionPool(2, 10 , conn_str)

    @contextmanager
    def get_resource(self):
        if self._connection_pool is None:
            self.initialize_connection_pool()

        conn = self._connection_pool.getconn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor, conn
        finally:
            cursor.close()
            self._connection_pool.putconn(conn)

    def shutdown_connection_pool(self):
        if self._connection_pool is not None:
            self._connection_pool.closeall()

db_helper = DBHelper()