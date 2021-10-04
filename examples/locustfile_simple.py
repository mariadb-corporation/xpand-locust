# -*- coding: utf-8 -*-
# Copyright (C) 2021 dvolkov@mariadb

# https://docs.locust.io/en/stable/configuration.html
# Run as
# locust  --locustfile examples/locustfile_simple  --headless -u 10 --run-time 1m --spawn-rate 10 --csv-full-history --csv mysql --reset-stats --params params.yaml

import os
import random

from locust import between, task
from xpand_locust import CustomLocust, CustomTasks, load_seed_file

NUM_RECORDS_REQUIRED = 10000


class MyTasks(CustomTasks):
    def on_start(self):  # For every new user
        super(MyTasks, self).on_start()
        self.products_iterator = load_seed_file(
            "seed_values/products.csv", num_rows_required=NUM_RECORDS_REQUIRED
        )

    # This is a default weight - see CustomTasks which applies custom weights
    @task(10)
    def insert_order(self):
        _ = self.client.execute(
            "insert into orders (product_name, amount) values (%s, %s)",
            (
                next(self.products_iterator),
                10,
            ),
        )

    @task(1)
    def count_by_product(self):
        _ = self.client.query_all(
            "select count(*) from orders where product_name=%s",
            (next(self.products_iterator),),
        )


class MyUser(CustomLocust):
    def on_start(self):
        pass

    def __init__(self, *args, **kwargs):
        super(MyUser, self).__init__(*args, **kwargs)

    tasks = [MyTasks]
    wait_time = between(1, 5)
