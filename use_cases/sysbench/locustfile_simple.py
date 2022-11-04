# -*- coding: utf-8 -*-
# Copyright (C) 2021 dvolkov@mariadb

# https://docs.locust.io/en/stable/configuration.html
# Run as
# locust  --locustfile examples/locustfile_simple  --headless -u 10 --run-time 1m --spawn-rate 10 --csv-full-history --csv mysql --reset-stats --params params.yaml


import numpy
from locust import between, constant, constant_throughput, task
from xpand_locust import CustomLocust, CustomTasks
from locust import LoadTestShape


TOTAL_ROWS = 1000000  # Number of rows per table
BULK_ROWS = 100  # how many rows to use for range scan
TABLES = 10


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
    def on_start(self):  # For every new user
        super(MyTasks, self).on_start()

    @task(0)
    def reconnect(self):
        self.client.connect()

    @task(9)
    def point_selects(self):
        random_id = get_random_id()
        q = f"SELECT c FROM sbtest{get_table_num()} WHERE id=%s"
        r = self.client.query(
            q,
            (random_id,),
        )

    @task(0)
    def simple_ranges(self):
        random_id = get_random_id()
        q = f"SELECT c FROM sbtest{get_table_num()} WHERE id BETWEEN %s AND %s"
        _ = self.client.query_all(
            q,
            (random_id, random_id + BULK_ROWS),
        )

    @task(0)
    def ordered_ranges(self):
        random_id = get_random_id()
        q = f"SELECT c FROM sbtest{get_table_num()} WHERE id BETWEEN %s AND %s ORDER BY c"
        _ = self.client.query_all(
            q,
            (random_id, random_id + BULK_ROWS),
        )

    @task(1)
    def non_index_updates(self):
        random_id = get_random_id()
        random_str = c_value()
        q = f"UPDATE sbtest{get_table_num()} SET c=%s WHERE id=%s"
        self.client.trx_begin()
        self.client.execute(q, (random_str, random_id))
        self.client.trx_commit()

    @task(0)
    def index_updates(self):
        random_id = get_random_id()
        random_str = c_value()
        q = f"UPDATE sbtest{get_table_num()} SET k=k+1 WHERE id=%s"
        self.client.trx_begin()
        self.client.execute(q, (random_id,))
        self.client.trx_commit()

    @task(0)
    def delete_inserts(self):
        random_id = get_random_id()
        random_str = c_value()
        tab_num = get_table_num()
        q = f"DELETE from  sbtest{tab_num} WHERE id=%s"
        self.client.trx_begin()

        self.client.execute(q, (random_id,))
        q = f"INSERT INTO sbtest{tab_num} (id, k, c, pad) VALUES (%s, %s, %s, %s)"
        self.client.execute(q, (random_id, get_random_id(), c_value(), pad_value()))
        self.client.trx_commit()


class MyUser(CustomLocust):
    def on_start(self):
        pass

    def on_stop(self):
        self.client.conn.close()

    def __init__(self, *args, **kwargs):
        super(MyUser, self).__init__(*args, **kwargs)

    tasks = [MyTasks]
    wait_time = constant(0)  # constant_throughput(50)  # between(0.01, 0.05)


class StagesShape(LoadTestShape):
    """
    A simply load test shape class that has different user and spawn_rate at
    different stages.
    Keyword arguments:
        stages -- A list of dicts, each representing a stage with the following keys:
            duration -- When this many seconds pass the test is advanced to the next stage
            users -- Total user count
            spawn_rate -- Number of users to start/stop per second
            stop -- A boolean that can stop that test at a specific stage
        stop_at_end -- Can be set to stop once all stages have run.
    """

    stages = [
        {"duration": 120, "users": 256, "spawn_rate": 64},
        {"duration": 120, "users": 384, "spawn_rate": 64},
        {"duration": 120, "users": 512, "spawn_rate": 10},
        {"duration": 120, "users": 640, "spawn_rate": 10},
        {"duration": 120, "users": 1024, "spawn_rate": 10},
    ]

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data

        return None