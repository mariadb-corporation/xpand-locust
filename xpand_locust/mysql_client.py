import random

import gevent.monkey  # https://github.com/PyMySQL/PyMySQL/issues/451
import pymysql
import pymysql.cursors  # https://github.com/PyMySQL/PyMySQL

from .custom_timer import custom_timer

gevent.monkey.patch_all()


class MySqlClient:
    def __init__(self, **kwargs):
        self.connect_params = kwargs.copy()
        hosts = kwargs.get("host").split(",")
        rnd = random.randint(0, len(hosts) - 1)
        self.connect_params["host"] = hosts[rnd]
        self.conn = pymysql.connect(**self.connect_params)
        self.cur = self.conn.cursor()

    def _query(self, query, params=None):
        self.cur.execute(query, params)
        row = self.cur.fetchone()
        return row

    def _query_all(self, query, params=None):
        self.cur.execute(query, params)
        rows = self.cur.fetchall()
        return rows

    def trx_begin(self):
        self.conn.begin()

    def trx_commit(self):
        self.conn.commit()

    def _execute(self, query, params):
        self.cur.execute(query, params)
        return self.cur.rowcount  # Return how many values has been updated

    def _executemany(self, query, params):
        self.cur.executemany(query, params)
        return self.cur.rowcount  # Return how many values has been updated

    @custom_timer
    def execute(self, query, params):
        return self._execute(query, params)

    @custom_timer
    def executemany(self, query, params):
        return self._executemany(self, query, params)

    @custom_timer
    def query_all(self, query, params=None):
        return self._query_all(query, params)
