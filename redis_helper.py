import redis
from contextlib import contextmanager
import os


class RedisHelper:
    def __init__(self):
        self._conn = None

    def get_conn_str(self):
        # Initialisation
        conn_str = os.getenv("REDIS_URL", "localhost")

        return conn_str

    def initialize_connection(self):
        conn_str = self.get_conn_str()
        self._conn = redis.Redis(host=conn_str, port=6379, db=0)

    @contextmanager
    def get_resource(self):
        if self._conn is None:
            self.initialize_connection()
        yield self._conn


redis_helper = RedisHelper()