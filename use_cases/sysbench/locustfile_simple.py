# -*- coding: utf-8 -*-
# Copyright (C) 2021 dvolkov@mariadb

# https://docs.locust.io/en/stable/configuration.html
# Run as
# locust  --locustfile examples/locustfile_simple  --headless -u 10 --run-time 1m --spawn-rate 10 --csv-full-history --csv mysql --reset-stats --params params.yaml


import numpy
from locust import between, task
from xpand_locust import CustomLocust, CustomTasks

TOTAL_ROWS = 1000000  # Number of rows per table
BULK_ROWS = 20  # how many rows to use for range scan
TABLES = 2


def get_random_id():
    """Return random record id"""
    return numpy.random.randint(0, TOTAL_ROWS - BULK_ROWS)


def get_table_num():
    """Return random table num"""
    return numpy.random.randint(1, TABLES + 1)


class MyTasks(CustomTasks):
    def on_start(self):  # For every new user
        super(MyTasks, self).on_start()

    @task(100)
    def reconnect(self):
        self.client.connect()

    @task(10)
    def point_selects(self):
        random_id = get_random_id()
        q = f"SELECT c FROM sbtest{get_table_num()} WHERE id=%s"
        r = self.client.query(
            q,
            (random_id,),
        )

    @task(1)
    def simple_ranges(self):
        random_id = get_random_id()
        q = f"SELECT c FROM sbtest{get_table_num()} WHERE id BETWEEN %s AND %s"
        _ = self.client.query_all(
            q,
            (random_id, random_id + BULK_ROWS),
        )


class MyUser(CustomLocust):
    def on_start(self):
        pass

    def on_stop(self):
        self.client.conn.close()

    def __init__(self, *args, **kwargs):
        super(MyUser, self).__init__(*args, **kwargs)

    tasks = [MyTasks]
    wait_time = between(0.1, 0.5)
