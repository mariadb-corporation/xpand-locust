# -*- coding: utf-8 -*-
# Copyright (C) 2021 dvolkov@mariadb

# https://docs.locust.io/en/stable/configuration.html
# Run as
# locust  --locustfile examples/locustfile_simple  --headless -u 10 --run-time 1m --spawn-rate 10 --csv-full-history --csv mysql --reset-stats --params params.yaml


import math

import locust.runners
import locust.stats
import numpy
from locust import LoadTestShape, between, constant, constant_throughput, task

from xpand_locust import CustomLocust, CustomTasks, custom_timer

locust.runners.WORKER_REPORT_INTERVAL = 1.0
locust.stats.CONSOLE_STATS_INTERVAL_SEC = 1
locust.stats.STATS_AUTORESIZE = False

TOTAL_ROWS = 1000000  # Number of rows per table
BULK_ROWS = 100  # how many rows to use for range scan
TABLES = 10
RECONNECT_RATE = 10000


def get_random_id():
    """Return random record id"""
    return numpy.random.randint(0, TOTAL_ROWS - BULK_ROWS)


def get_table_num():
    """Return random table num"""
    return numpy.random.randint(1, TABLES + 1)


def c_value():
    s = str(numpy.random.randint(1, 10))
    one_group = s * 11
    all_groups = [one_group] * 10
    return "-".join(all_groups)


def pad_value():
    s = str(numpy.random.randint(1, 10))
    one_group = s * 11
    all_groups = [one_group] * 5
    return "-".join(all_groups)


class MyTasks(CustomTasks):
    # def __init__(self):
    #    self.request_count = 0

    def on_start(self):  # For every new user
        self.request_count = 0
        # super(MyTasks, self).on_start()

    def reconnect(self):
        self.request_count += 1
        if self.request_count % RECONNECT_RATE == 0:
            self.client.connect()

    def point_selects(self):
        random_id = get_random_id()
        q = f"SELECT c FROM sbtest{get_table_num()} WHERE id=%s"
        r = self.client._query(
            q,
            (random_id,),
        )

    def simple_ranges(self):
        random_id = get_random_id()
        q = f"SELECT c FROM sbtest{get_table_num()} WHERE id BETWEEN %s AND %s"
        _ = self.client._query_all(
            q,
            (random_id, random_id + BULK_ROWS),
        )

    def ordered_ranges(self):
        random_id = get_random_id()
        q = f"SELECT c FROM sbtest{get_table_num()} WHERE id BETWEEN %s AND %s ORDER BY c"
        _ = self.client._query_all(
            q,
            (random_id, random_id + BULK_ROWS),
        )

    def non_index_updates(self):
        random_id = get_random_id()
        random_str = c_value()
        q = f"UPDATE sbtest{get_table_num()} SET c=%s WHERE id=%s"
        self.client.trx_begin()
        self.client._execute(q, (random_str, random_id))
        self.client.trx_commit()

    def index_updates(self):
        random_id = get_random_id()
        random_str = c_value()
        q = f"UPDATE sbtest{get_table_num()} SET k=k+1 WHERE id=%s"
        self.client.trx_begin()
        self.client._execute(q, (random_id,))
        self.client.trx_commit()

    def delete_inserts(self):
        random_id = get_random_id()
        random_str = c_value()
        tab_num = get_table_num()
        q = f"DELETE from  sbtest{tab_num} WHERE id=%s"
        self.client.trx_begin()

        self.client._execute(q, (random_id,))
        q = f"INSERT INTO sbtest{tab_num} (id, k, c, pad) VALUES (%s, %s, %s, %s)"
        self.client._execute(q, (random_id, get_random_id(), c_value(), pad_value()))
        self.client.trx_commit()

    @task(1)
    def new_order(self):
        self._new_order()

    @custom_timer
    def _new_order(self):
        for _ in range(9):
            self.point_selects()

        self.non_index_updates()
        self.index_updates()
        self.reconnect()

    @task(1)
    def credit_check(self):
        self._credit_check()

    @custom_timer
    def _credit_check(self):
        for _ in range(9):
            self.simple_ranges()

        self.delete_inserts()
        self.reconnect()


class MyUser(CustomLocust):
    def on_start(self):
        pass

    def on_stop(self):
        self.client.conn.close()

    def __init__(self, *args, **kwargs):
        super(MyUser, self).__init__(*args, **kwargs)

    tasks = [MyTasks]
    wait_time = constant(0)  # between(1,2)


# class StepLoadShape(LoadTestShape):
#     """
#     A step load shape
#     Keyword arguments:
#         step_time -- Time between steps
#         step_load -- User increase amount at each step
#         spawn_rate -- Users to stop/start per second at every step
#         time_limit -- Time limit in seconds
#     """

#     step_time = 120
#     step_load = 64
#     spawn_rate = 8
#     time_limit = 480

#     def tick(self):
#         run_time = self.get_run_time()

#         if run_time > self.time_limit:
#             return None

#         current_step = math.floor(run_time / self.step_time) + 1
#         return (current_step * self.step_load, self.spawn_rate)
