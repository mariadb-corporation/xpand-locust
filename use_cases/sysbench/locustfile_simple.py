# -*- coding: utf-8 -*-
# Copyright (C) 2021 dvolkov@mariadb

# https://docs.locust.io/en/stable/configuration.html
# Run as
# locust  --locustfile examples/locustfile_simple  --headless -u 10 --run-time 1m --spawn-rate 10 --csv-full-history --csv mysql --reset-stats --params params.yaml


import numpy
from locust import between, constant_throughput, task
from xpand_locust import CustomLocust, CustomTasks

TOTAL_ROWS = 1000000  # Number of rows per table
BULK_ROWS = 500  # how many rows to use for range scan
TABLES = 2


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

    @task(1)
    def reconnect(self):
        self.client.connect()

    @task(10000)
    def point_selects(self):
        random_id = get_random_id()
        q = f"SELECT c FROM sbtest{get_table_num()} WHERE id=%s"
        r = self.client.query(
            q,
            (random_id,),
        )

    @task(3000)
    def simple_ranges(self):
        random_id = get_random_id()
        q = f"SELECT c FROM sbtest{get_table_num()} WHERE id BETWEEN %s AND %s"
        _ = self.client.query_all(
            q,
            (random_id, random_id + BULK_ROWS),
        )

    @task(3000)
    def ordered_ranges(self):
        random_id = get_random_id()
        q = f"SELECT c FROM sbtest{get_table_num()} WHERE id BETWEEN %s AND %s ORDER BY c"
        _ = self.client.query_all(
            q,
            (random_id, random_id + BULK_ROWS),
        )

    @task(2000)
    def non_index_updates(self):
        random_id = get_random_id()
        random_str = c_value()
        q = f"UPDATE sbtest{get_table_num()} SET c=%s WHERE id=%s"
        self.client.trx_begin()
        self.client.execute(q, (random_str, random_id))
        self.client.trx_commit()

    @task(2000)
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
    wait_time = constant_throughput(50)  # between(0.01, 0.05)
