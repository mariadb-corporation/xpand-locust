import logging
import sys
import time

import gevent
import locust.stats
from gevent.lock import Semaphore
from locust import TaskSet, User, events
from locust.runners import (
    STATE_CLEANUP,
    STATE_STOPPED,
    STATE_STOPPING,
    MasterRunner,
    WorkerRunner,
)

from .locust_utils import histogram, load_yaml_config
from .mysql_client import MySqlClient

all_users_spawned = Semaphore()
all_users_spawned.acquire()


logger = logging.getLogger(__name__)

# TODO
# 'total_content_length': 0  - I need to send number of rows returned by methods

# ToDO socket.setdefaulttimeout(150)

# TODO
# https://docs.locust.io/en/stable/configuration.html
# PERCENTILES_TO_REPORT
# CONSOLE_STATS_INTERVAL_SEC
# locust.stats.CSV_STATS_INTERVAL_SEC = 1  # default is 1 second
# locust.stats.CSV_STATS_FLUSH_INTERVAL_SEC = 10  # how often the data is flushed to disk

# Global custom params
class CustomParams:
    """Singleton class to hold global settings for the project

    Returns:
        Dict: all params from yaml file
    """

    __instance = None

    def __new__(cls, *args, **kwargs):
        if not CustomParams.__instance:
            CustomParams.__instance = object.__new__(cls)
        return CustomParams.__instance

    def __init__(self):
        self.params = None

    def load_config(self, yaml_config_file):
        self.params = load_yaml_config(yaml_config_file)

    def get_params(self, key):
        return self.params.get(key)

    def get_weight(self, name):
        weights = self.get_params("weights")
        return weights.get(name, 0)


custom_params = CustomParams()

# https://github.com/locustio/locust/blob/87b6dbc2e74047ce7ad10912f58e8c7a509386f7/locust/argument_parser.py
@events.init_command_line_parser.add_listener
def _(parser):
    parser.add_argument("--params", include_in_web_ui=False, default="params.yaml")
    parser.add_argument(
        "--histogram",
        action="store_true",
        default=False,
        include_in_web_ui=False,
        help="produce latency histogram after test end",
    )


@events.init.add_listener
def _(environment, **kw):
    @environment.events.spawning_complete.add_listener
    def on_spawning_complete(**kw):
        all_users_spawned.release()


@events.init.add_listener
def _(environment, **kw):
    if not isinstance(environment.runner, MasterRunner):
        custom_params.load_config(environment.parsed_options.params)

    # TODO: stop for certain fail % or latency or number of requests
    # https://docs.locust.io/en/stable/extending-locust.html#run-a-background-greenlet
    # https://github.com/locustio/locust/issues/414
    # only run this on master & standalone
    # if not isinstance(environment.runner, WorkerRunner):
    #    gevent.spawn(checker, environment)


def checker(environment):
    while not environment.runner.state in [
        STATE_STOPPING,
        STATE_STOPPED,
        STATE_CLEANUP,
    ]:
        time.sleep(1)
        if environment.runner.stats.total.num_requests > sys.maxsize:
            print(
                f"Num of requests was {environment.runner.stats.total.fail_ratio}, quitting"
            )
            environment.runner.quit()
            return


# Print histogram if requested
@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    if environment.parsed_options.histogram and isinstance(
        environment.runner, MasterRunner
    ):

        stats = environment.stats.serialize_stats()
        for i in range(len(stats)):
            print(f'==========   Historgram for {stats[i].get("name")} ==============')
            response_times = stats[i].get("response_times")
            data = [key for key in response_times for i in range(response_times[key])]
            histogram(data, 25)


class CustomTasks(TaskSet):
    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        super(CustomTasks, self).__init__(*args, **kwargs)

    def on_start(self):  # For every new user

        # Assign weights from custom parameters (command line parameter)
        custom_weights = custom_params.get_params("weights")
        new_tasks = []
        for func in set(self.tasks):
            weight = custom_weights.get(
                func.__name__, func.locust_task_weight
            )  # If no weight specified leave default
            self.logger.debug(f"applying weight {weight} for function {func.__name__} ")
            for _ in range(weight):
                new_tasks.append(func)
            else:
                new_tasks.append(func)
        # Should I shuffle as well ?
        self.tasks = new_tasks

        all_users_spawned.wait()
        self.wait()
        # From https://github.com/locustio/locust/blob/c3d1a49cda02660de14ddc25130673db9fae440a/locust/web.py
        self.user.environment.events.reset_stats.fire()
        self.user.environment.runner.stats.reset_all()
        self.user.environment.runner.exceptions = {}


# TODO - wait for all users
# https://github.com/locustio/locust/blob/master/examples/semaphore_wait.py


class CustomLocust(User):
    abstract = True

    def __init__(self, *args, **kwargs):
        super(CustomLocust, self).__init__(*args, **kwargs)
        db_config = custom_params.get_params("db_config")
        try:
            self.client = CustomClient(**db_config)
        except Exception as e:
            logger.error(f"Fatal error has happened {e}")
            self.environment.runner.stop()


class CustomClient(MySqlClient):
    def __init__(self, *args, **kwargs):
        super(CustomClient, self).__init__(*args, **kwargs)
