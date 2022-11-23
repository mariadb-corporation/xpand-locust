import random
from typing import Tuple

import gevent.monkey  # https://github.com/PyMySQL/PyMySQL/issues/451
import pymysql
import pymysql.cursors  # https://github.com/PyMySQL/PyMySQL
from retry import retry

from .custom_timer import custom_timer

gevent.monkey.patch_all()

lost_connection_codes = ["1927", "2006", "2013", "1927"]
retry_transaction_codes = ["16388"]


class MySqlClient:
    def __init__(self, **kwargs):
        self.connect_params = kwargs.copy()
        hosts = kwargs.get("host").split(",")
        rnd = random.randint(0, len(hosts) - 1)
        self.connect_params["host"] = hosts[
            rnd
        ]  # ToDo: random.choice or https://pypi.org/project/roundrobin/
        self.connect_params["cursorclass"] = pymysql.cursors.DictCursor
        self.conn, self.cur = self.connect()

    @retry((pymysql.Error), tries=30, delay=1)
    def connect(self) -> Tuple:

        self.conn = pymysql.connect(**self.connect_params)
        self.cur = self.conn.cursor()
        return (self.conn, self.cur)

    def handle_exception(self, e):
        do_reconnect = False

        if e is pymysql.InterfaceError:  # connection closed from driver side
            do_reconnect = True

        for (
            code
        ) in (
            lost_connection_codes
        ):  # This is a database problem and I've lost connection
            if code in str(e):
                do_reconnect = True

        if do_reconnect:
            self.conn, self.cur = self.connect()

        raise e  # Now I am ready to repeat the transaction again

    @retry((pymysql.Error), tries=10, delay=1)
    def _query(self, query, params=None):
        try:
            self.cur.execute(query, params)
            row = self.cur.fetchone()
            return row
        except (pymysql.Error) as e:
            self.handle_exception(e)

    @retry((pymysql.OperationalError, pymysql.InternalError), tries=10, delay=1)
    def _query_all(self, query, params=None):
        try:
            self.cur.execute(query, params)
            rows = self.cur.fetchall()
            return rows
        except (pymysql.Error) as e:
            self.handle_exception(e)

    def trx_begin(self):
        self.conn.begin()

    def trx_commit(self):
        self.conn.commit()

    @retry((pymysql.OperationalError, pymysql.InternalError), tries=10, delay=1)
    def _execute(self, query, params):
        try:
            self.cur.execute(query, params)
            return self.cur.rowcount  # Return how many values has been updated
        except (pymysql.Error) as e:
            self.handle_exception(e)

    @retry((pymysql.OperationalError, pymysql.InternalError), tries=10, delay=1)
    def _executemany(self, query, params):
        try:
            self.cur.executemany(query, params)
            return self.cur.rowcount  # Return how many values has been updated
        except (pymysql.Error) as e:
            self.handle_exception(e)

    @custom_timer
    def execute(self, query, params):
        return self._execute(query, params)

    @custom_timer
    def executemany(self, query, params):
        return self._executemany(query, params)

    @custom_timer
    def query_all(self, query, params=None):
        return self._query_all(query, params)

    @custom_timer
    def query(self, query, params=None):
        return self._query(query, params)
