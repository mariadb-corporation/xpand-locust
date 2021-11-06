# -*- coding: utf-8 -*-
# Copyright (C) 2021 dvolkov@mariadb

import logging
import multiprocessing
import sys
import time

import pssh
from locust.util.timespan import parse_timespan
from pssh.clients import ParallelSSHClient
from xpand_locust import YamlConfigException, load_yaml_config

from .exceptions import CommandException, ProcessExecutonException, SwarmException
from .run_subprocess import RunSubprocess, TimeoutException


class Swarm:
    def __init__(self, swarm_config, log_level):

        self.log_level = log_level
        logging.basicConfig(
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            level=log_level,  # args.log_level,
        )
        self.logger = logging.getLogger(__name__)
        try:
            self.config = load_yaml_config(swarm_config)
        except YamlConfigException as e:
            self.logger.error(e)
            raise SwarmException(e)

    def main_configure(self):
        """Configure all drivers

        Raises:
            SwarmException: [description]

        Returns:
            [type]: [description]
        """
        self.logger.info(f"Configure has been started")

        pssh_config = self.config.get("pssh_options")
        pssh_config["hosts"] = self.config.get("drivers")

        client = ParallelSSHClient(**pssh_config)

        try:
            cmds = self.config.get("configure")
            for cmd in cmds:
                self.logger.info(f"Running {cmd}")
                output = client.run_command(cmd, stop_on_errors=True)
                client.join()
                if self.log_level == "DEBUG":
                    for host_out in output:
                        for line in host_out.stdout:
                            print(line)
                    for line in host_out.stderr:
                        print(line)
                for host_out in output:
                    if host_out.exit_code > 0:
                        self.logger.error(
                            f"Host {host_out.host}, Command {cmd} failed with code {host_out.exit_code}"
                        )
                        raise SwarmException()
                    else:
                        self.logger.info(f"Host {host_out.host}: Success")

        except pssh.exceptions.UnknownHostError as e:
            self.logger.error(e)
            raise SwarmException()

    def run_master_command(self, cmd, timeout: int = 0):
        """
        run command (master or standalone) and print output in real time
        """
        try:
            proc = RunSubprocess(cmd=cmd).run(wait=False)
            while True:
                # TODO implement timeout - locust could wait forever
                line = proc.stdout.readline()
                if proc.poll() is not None:
                    break
                if line:
                    print(line.strip())
            retcode = proc.poll()
            if retcode != 0:
                self.logger.error(
                    f"Error return code {retcode} from command: {proc.args}"
                )
                raise SwarmException()

        except CommandException as e:
            self.logger.error("Command failed with {e}")
            raise SwarmException()
        except TimeoutException as e:
            self.logger.error("Timeout occurred while running command {proc.args}")
            raise SwarmException()

    def main_standalone(self):
        """
        Run locust standalone - both masters and workers in the same process
        """
        self.logger.debug("About to start standalone")
        standalone_options = self.config.get("locust_master_options")
        standalone_cmd = " ".join(
            [
                "locust",
                "--locustfile",
                self.args.locustfile,
                "--run-time",
                self.args.run_time,
                "--users",
                str(self.args.users),
                "--spawn-rate",
                str(self.args.spawn_rate),
                "--csv",
                self.args.csv,
                "--params",
                self.args.xpand_params,
                "--loglevel",
                self.log_level,
                standalone_options.get("extra_options"),
            ]
        )
        self.logger.debug(standalone_cmd)

        self.run_master_command(standalone_cmd)

    def main_master(self):
        """
        https://docs.locust.io/en/stable/configuration.html
        """
        self.logger.debug("About to start master")

        # MASTER_CMD="locust -f ${LOCUSTFILE} -u ${NUM_USERS} -r 10 --run-time ${RUNTIME}m --master ${STEP_LOAD} --master-bind-port=5557 --headless --expect-workers ${NUM_WORKERS} --csv=${RUN_DIR}/${STAT_PREFIX} --csv-full-history --reset-stats"
        master_options = self.config.get("locust_master_options")
        master_cmd = " ".join(
            [
                "locust",
                "--locustfile",
                self.args.locustfile,
                "--master",
                "--run-time",
                self.args.run_time,
                "--users",
                str(self.args.users),
                "--spawn-rate",
                str(self.args.spawn_rate),
                "--headless",
                "--master-bind-host",
                master_options.get("master-bind-host"),
                "--master-bind-port ",
                str(master_options.get("master-bind-port")),
                "--expect-workers",
                str(self.args.expected_workers),
                "--csv",
                self.args.csv,
                "--loglevel",
                self.log_level,
                master_options.get("extra_options"),
            ]
        )
        self.logger.debug(master_cmd)
        self.run_master_command(master_cmd)

    def main_workers(self):
        """
        https://docs.locust.io/en/stable/running-locust-distributed.html#running-locust-distributed

        """
        # WORKER_CMD="locust -f ${LOCUSTFILE} --worker --master-host=${MASTERHOST} --master-port=5557"
        # ToDo for every self.config.get("drivers")
        master_options = self.config.get("locust_master_options")
        
        cpu_count = multiprocessing.cpu_count()
        if self.args.num_workers > cpu_count:
            self.logger.warning(f"Reducing number of workers to {cpu_count}")
            num_workers = cpu_count
        else:
            num_workers = self.args.num_workers

        worker_cmd = " ".join(
            [
                "nohup",
                "locust",
                "--locustfile",
                self.args.locustfile,
                "--worker",
                "--master-port",
                str(master_options.get("master-bind-port")),
                "--master-host",
                "127.0.0.1",
            ]
        )
        self.logger.info(f"Starting all {num_workers} workers")
        running_procs = []
        for i in range(num_workers):
            cmd = worker_cmd + f" </dev/null >worker{i}.out 2>&1"
            self.logger.debug(f"Running {cmd}")
            running_procs.append(RunSubprocess(cmd=cmd).run_as_shell(wait=False))

        """
        while running_procs:
            for process in running_procs:
                retcode = process.poll()
                if retcode is not None:  # Process finished.
                    running_procs.remove(process)
                    if retcode != 0:
                        self.logger.error(
                            f"Bad return code {retcode} from command: {process.args}"
                        )
                        raise SwarmException()
                    else:
                        while True:
                            line = process.stdout.readline()
                            if line == b"":
                                break
                            else:
                                sys.stdout.write(
                                    f"{process.pid}: {line.decode('utf-8')}"
                                )
        """
