# -*- coding: utf-8 -*-
# Copyright (C) 2021 dvolkov@mariadb

import os
import random

from locust import between, task
from xpand_locust import CustomLocust, CustomTasks, custom_timer
from xpand_locust.custom_timer import custom_timer

NUM_RECORDS_REQUIRED = 10000


class MyTasks(CustomTasks):
    def on_start(self):  # For every new user
        super(MyTasks, self).on_start()

    @task(1)
    @custom_timer
    def my_trans(self):
        self.client.trx_begin()  # Transaction begin
        _ = self.client._execute(
            "insert into t1 (a,b,c,d) values (%s, %s,%s,%s)",
            (
                random.randrange(-2147483648, 2147483647),
                random.randrange(-2147483648, 2147483647),
                random.randrange(-2147483648, 2147483647),
                random.randrange(-2147483648, 2147483647),
            ),
        )
        _ = self.client._execute(
            "insert into t1 (a,b,c,d) values (%s, %s,%s,%s)",
            (
                random.randrange(-2147483648, 2147483647),
                random.randrange(-2147483648, 2147483647),
                random.randrange(-2147483648, 2147483647),
                random.randrange(-2147483648, 2147483647),
            ),
        )
        _ = self.client._execute(
            "update t1 set  b=0 where col_pk = last_insert_id()", ()
        )
        row = self.client._query(
            "select count(*) from t1 where col_pk = last_insert_id()"
        )
        self.client.trx_commit() # Transaction commit


class MyUser(CustomLocust):
    def on_start(self):
        pass

    def __init__(self, *args, **kwargs):
        super(MyUser, self).__init__(*args, **kwargs)

    tasks = [MyTasks]
    wait_time = between(0.5, 1)
