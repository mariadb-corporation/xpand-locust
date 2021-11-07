#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 dvolkov

# Swarm is a tool for running locust in a distributed fashion on a set of load generator servers.
# Inspired by https://github.com/locustio/locust/blob/master/scripts/run-disributed-headless.sh
# Examples:

# Standalone
# ./bin/swarm_runner.py --swarm-config swarm_config.yaml --log-level DEBUG -f examples/locustfile_simple run_standalone --run-time 100 --users 10 --spawn-rate 10 --csv mysql --params params.yaml

# Workers and master on the same host
# ./bin/swarm_runner.py --swarm-config swarm_config.yaml --log-level DEBUG -f examples/locustfile_simple run_workers --num-workers 2 --drivers 127.0.0.1 --master-host=127.0.0.1
# ./bin/swarm_runner.py --swarm-config swarm_config.yaml --log-level DEBUG -f examples/locustfile_simple run_master --run-time 100 --users 10 --spawn-rate 10 --csv mysql --params params.yaml --expected-workers 2

import argparse
import logging
import os
import sys
import traceback

from swarm import Swarm, SwarmException


class Main(Swarm):
    def __init__(self):
        parser = argparse.ArgumentParser(
            description="A tool for running locust in a distributed fashion."
        )
        parser.add_argument(
            "--swarm-config",
            action="store",
            default="swarm_config.yaml",
            dest="swarm_config",
            help="swarm config file",
            required=True,
        )

        parser.add_argument(
            "--log-level",
            action="store",
            dest="log_level",
            default="INFO",
            help="Log Level: INFO|DEBUG|ERROR",
        )

        parser.add_argument(
            "-f",
            "--locustfile",
            action="store",
            dest="locustfile",
            help="Specify locust file to run test",
            required=True,
        )

        subparsers = parser.add_subparsers()

        configure_subparser = subparsers.add_parser(
            "configure",
            help="configure the drivers",
            description="Start locust master and distributed slaves with one command",
        )
        configure_subparser.set_defaults(func="main_configure")

        # Workers
        run_workers_subparser = subparsers.add_parser(
            "run_workers",
            help="run workers",
            description="run master and wait for workers to connect",
        )

        run_workers_subparser.add_argument(
            "--num-workers",
            action="store",
            dest="num_workers",
            type=int,
            help="number of workers processes per load generator. Default: number of cores",
            required=True,
        )

        run_workers_subparser.add_argument(
            "--master-host",
            action="store",
            dest="master_host",
            help="Master host IP. If it is 127.0.0.1 all workers will start locally",
            default="127.0.0.1",
            required=True,
        )

        run_workers_subparser.add_argument(
            "--drivers",
            action="store",
            dest="drivers_list",
            help="List fo drivers. Use 127.0.0.1 for local worker. If missing will read from yaml file",
        )

        run_workers_subparser.set_defaults(func="main_workers")

        # Master
        run_master_subparser = subparsers.add_parser(
            "run_master",
            help="run master",
            description="run master process",
        )

        run_master_subparser.add_argument(
            "--run-time",
            action="store",
            dest="run_time",
            default="10m",
            help="Run time formats are: 20, 20s, 3m, 2h, 1h20m, 3h30m10s, etc",
            required=True,
        )

        run_master_subparser.add_argument(
            "-u",
            "--users",
            action="store",
            dest="users",
            type=int,
            help="number of users",
            required=True,
        )

        run_master_subparser.add_argument(
            "-r",
            "--spawn-rate",
            action="store",
            dest="spawn_rate",
            type=int,
            help="spawn rate",
            required=True,
        )

        run_master_subparser.add_argument(
            "--csv",
            action="store",
            dest="csv",
            help="csv prefix",
            required=True,
        )

        run_master_subparser.add_argument(
            "--expected-workers",
            action="store",
            dest="expected_workers",
            type=int,
            help="number of workers processes to expect",
            required=True,
        )

        run_master_subparser.add_argument(
            "--params",
            action="store",
            dest="xpand_params",
            help="xpand params config file",
            required=True,
        )

        run_master_subparser.set_defaults(func="main_master")

        # Standalone
        run_stanalone_subparser = subparsers.add_parser(
            "run_standalone",
            help="run master",
            description="run master process",
        )

        run_stanalone_subparser.add_argument(
            "--run-time",
            action="store",
            dest="run_time",
            default="10m",
            help="Run time formats are: 20, 20s, 3m, 2h, 1h20m, 3h30m10s, etc",
            required=True,
        )

        run_stanalone_subparser.add_argument(
            "-u",
            "--users",
            action="store",
            dest="users",
            type=int,
            help="number of users",
            required=True,
        )

        run_stanalone_subparser.add_argument(
            "-r",
            "--spawn-rate",
            action="store",
            dest="spawn_rate",
            type=int,
            help="spawn rate",
            required=True,
        )

        run_stanalone_subparser.add_argument(
            "--csv",
            action="store",
            dest="csv",
            help="csv prefix",
            required=True,
        )

        run_stanalone_subparser.add_argument(
            "--params",
            action="store",
            dest="xpand_params",
            help="xpand params config file",
            required=True,
        )

        run_stanalone_subparser.set_defaults(func="main_standalone")

        self.args = parser.parse_args()

        super().__init__(self.args.swarm_config, self.args.log_level)

    def __call__(self, *args, **kws):
        method = self.args.func
        return getattr(self, method)(*args, **kws)


if __name__ == "__main__":

    xpand_locust_home = os.environ.get("XPAND_LOCUST_HOME", "./")
    if xpand_locust_home not in sys.path:
        sys.path.insert(0, xpand_locust_home)

    logger = logging.getLogger(__name__)
    exit_status = 0

    try:
        main = Main()
        main()
    except SwarmException as e:  # I already printed out the message
        print(e)
        exit_status = 1
    except KeyboardInterrupt:
        logger.error("Keyboard interrupt, exiting now.. ")
        exit_status = 2
    except Exception as e:
        logger.error(f"Unhandled Exception has happened: {e}")
        if main.log_level == "DEBUG":
            traceback.print_tb(e.__traceback__)
        exit_status = 127
    finally:
        exit(exit_status)
