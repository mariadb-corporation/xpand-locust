# -*- coding: utf-8 -*-
# Copyright (C) 2021 dvolkov@mariadb

import logging
import multiprocessing
import os
import sys
import time

import pssh
from gevent import joinall
from locust.util.timespan import parse_timespan
from pssh.clients import ParallelSSHClient
from pssh.exceptions import (
    AuthenticationError,
    ConnectionError,
    ShellError,
    UnknownHostError,
)
from xpand_locust import YamlConfigException, load_yaml_config

from .exceptions import CommandException, ProcessExecutonException, SwarmException
from .run_subprocess import RunSubprocess, TimeoutException

LOCALHOST = "127.0.0.1"
DEFAULT_REMOTE_DIR = "/tmp/locust"


class Swarm:
    def __init__(self, swarm_config, log_level):

        self.log_level = log_level
        # TODO https://stackoverflow.com/questions/13733552/logger-configuration-to-log-to-file-and-print-to-stdout
        # handlers=[
        # logging.FileHandler("debug.log"),  # I can add --output dir here
        # logging.StreamHandler()
        # ]

        logging.basicConfig(
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            level=log_level,  # args.log_level,
        )
        self.logger = logging.getLogger(__name__)

        # Drivers list can come from config or command line
        if hasattr(self.args, "drivers_list"):
            self.drivers_list = (
                self.args.drivers_list.split(",")
                if self.args.drivers_list
                else self.config.get("drivers")
            )
        else:
            self.drivers_list = None

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
        pssh_config["hosts"] = self.drivers_list

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

        except (UnknownHostError, ConnectionError, AuthenticationError) as e:
            self.logger.error(e)
            raise SwarmException()

    def run_master_command(self, cmd, timeout: int = 0):
        """
        run command (master or standalone) and print output in real time
        """
        try:
            proc = RunSubprocess(cmd=cmd).run(wait=False)
            while True:
                # TODO implement timeout - locust could wait forever; Look for the line  "Currently 2 clients ready to swarm"
                line = proc.stdout.readline()
                if proc.poll() is not None:
                    break
                if line:
                    print(line.rstrip())
            retcode = proc.poll()
            if retcode != 0:
                self.logger.error(
                    f"Error return code {retcode} from command: {proc.args}"
                )
                raise SwarmException()

        except KeyboardInterrupt as e:
            self.logger.error("Keyboard interrupt, exiting now.. ")
            self.kill_workers()
            raise SwarmException()
        except CommandException as e:
            self.logger.error("Command failed with {e}")
            raise SwarmException()
        except TimeoutException as e:
            self.logger.error("Timeout occurred while running command {proc.args}")
            raise SwarmException()

    def kill_workers(self):
        """Kill either local or remote workers

        # TODO can I send shutdown message instead?
        # Can I see where workers are coming from?

        """
        if self.drivers_list is not None:
            self.logger.info(f"Cleaning up the workers..")

            cmd = self.kill_workers_cmd()

            if self.drivers_list == [LOCALHOST]:  # Run kill command locally
                try:
                    _ = RunSubprocess(cmd=cmd).run_as_shell(wait=True)
                    self.logger.info("Done")
                except CommandException as e:
                    pass
            else:

                pssh_config = self.config.get("pssh_options")
                pssh_config["hosts"] = self.drivers_list

                client = ParallelSSHClient(**pssh_config)
                _ = client.run_command(cmd, stop_on_errors=True)
                client.join()

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

    def distribute_locustfile_dir(self, drivers_list: list):
        """Dstribute locustfile directory between all workers
        From  https://parallel-ssh.readthedocs.io/en/latest/advanced.html#sftp-and-scp
        """

        try:
            self.logger.info("Distributing workload dir bentween drivers")
            local_dir, file = os.path.split(self.args.locustfile)
            pssh_config = self.config.get("pssh_options")
            pssh_config["hosts"] = drivers_list

            client = ParallelSSHClient(**pssh_config)

            remote_dir = DEFAULT_REMOTE_DIR
            self.logger.debug(f"Copying from {local_dir} to {remote_dir}")
            cmd = client.copy_file(local_dir, remote_dir, recurse=True)

            joinall(cmd, raise_error=True)
            self.logger.info("Done")

        except (UnknownHostError, ConnectionError, AuthenticationError) as e:
            self.logger.error(e)
            raise SwarmException()

    def start_ssh_tunnels(self, drivers_list: list):
        """Start ssh tunnel between master and all drivers

        Args:
            drivers_list ([list]): list of all drivers
        """
        master_options = self.config.get("locust_master_options")
        master_bind_port = master_options.get("master-bind-port")
        pssh_config = self.config.get("pssh_options")

        # TODO add pem file to the command
        # TODO check if I should just call .run and not .run_as_shell
        # https://github.com/SvenskaSpel/locust-swarm/blob/be3f848df3b93bc018acd8ffbd9bfc83493fdb54/bin/swarm#L221
        # ssh: -f: go to background; -N: don't execute a command;  -R:  map ports
        running_procs = []
        for driver in drivers_list:
            cmd = f'ssh -l {pssh_config.get("user")} -N {driver} -R {master_bind_port}:localhost:{master_bind_port}'
            self.logger.debug(f"Starting ssh tunnel for {driver}:  {cmd}")
            proc = RunSubprocess(cmd=cmd).run(wait=False)
            running_procs.append(proc.pid)  # run_as_shell(wait=False))

        self.logger.debug(f"ssh tunnel pids {running_procs}")
        # TODO Check that tunnels has started OK

    def main_run(self):
        """Run master and workers all together in distributed fashion"""

        # Run workers
        if self.drivers_list == [LOCALHOST]:
            self.run_workers_locally()
        else:
            self.run_workers_remotely(self.drivers_list)

        # Run master
        self.main_master()

    def main_master(self):
        """
        https://docs.locust.io/en/stable/configuration.html
        """
        self.logger.info("About to start master")

        # MASTER_CMD="locust -f ${LOCUSTFILE} -u ${NUM_USERS} -r 10 --run-time ${RUNTIME}m --master ${STEP_LOAD} --master-bind-port=5557 --headless --expect-workers ${NUM_WORKERS} --csv=${RUN_DIR}/${STAT_PREFIX} --csv-full-history --reset-stats"
        master_options = self.config.get("locust_master_options")

        # Expected workers can be set by either of two parameters
        workers = (
            getattr(self.args, "expected_workers")
            if hasattr(self.args, "expected_workers")
            else getattr(self.args, "num_workers")
        )

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
                str(workers),
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
        """Run workers locally (on the current host)
        https://docs.locust.io/en/stable/running-locust-distributed.html#running-locust-distributed
        """
        self.run_workers_locally()

    """
    def run_workers(self, drivers_list: str):
        
        Main run worker. Depend on drivers_list it will decide how to run workers
        
        if drivers_list is None:
            self.run_workers_remotely(self.config.get("drivers"))
        elif drivers_list == LOCALHOST:
            self.run_workers_locally()
        else:
            self.run_workers_remotely(drivers_list.split(","))
    """

    def kill_workers_cmd(self):
        """Return command to kill workers on the host"""
        master_options = self.config.get("locust_master_options")
        master_bind_port = master_options.get("master-bind-port")
        # TODO pkill has pgrep pattern built in
        return f"kill -9 $(pgrep -f '[w]orker --master-port {master_bind_port}')"

    def run_workers_remotely(self, drivers_list: list):
        """Run drivers remotely

        WORKER_CMD="locust -f ${LOCUSTFILE} --worker --master-host=${MASTERHOST} --master-port=5557"

        Args:
            drivers_list (str): [description]
        """

        local_dir, locustfile = os.path.split(self.args.locustfile)

        # Copy local locustfile to all drivers
        if self.config.get("distribute_locustfile_directory"):
            self.distribute_locustfile_dir(drivers_list)
            local_dir = DEFAULT_REMOTE_DIR

        # start ssh tunnels? this should change master_host to localhost for workers
        if self.config.get("use_ssh_tunnel"):
            self.start_ssh_tunnels(drivers_list)
            master_host = LOCALHOST
        else:
            master_host = self.config.get("master")

        # Divide total number of workers between drivers
        self.logger.info("About to start workers on the remote drivers")
        # Expected workers can be set by either of two parameters
        workers = (
            getattr(self.args, "expected_workers")
            if hasattr(self.args, "expected_workers")
            else getattr(self.args, "num_workers")
        )
        num_workers_per_driver = workers // len(drivers_list)
        master_options = self.config.get("locust_master_options")

        # Don't forget to change directory on remote workers
        cmd = [f"cd {local_dir}"]

        # ./bin/swarm_runner.py --swarm-config swarm_config.yaml --log-level DEBUG -f examples/locustfile_simple run_workers --num-workers 2 --master-host=127.0.0.1
        worker_cmd = " ".join(
            [
                "swarm_runner.py",
                "--swarm-config",
                "swarm_config.yaml",
                "--log-level",
                "DEBUG",
                "-f",
                f"./{locustfile}",
                "run_workers",
                "--num-workers",
                str(num_workers_per_driver),
                "--master-host",
                master_host,
                "--params",
                f"./{os.path.basename(self.args.xpand_params)}",  # This assumes that xpand_params has been copied to the remote dir
            ]
        )
        cmd.append(worker_cmd)

        self.logger.debug(cmd)
        pssh_config = self.config.get("pssh_options")
        pssh_config["hosts"] = drivers_list

        try:
            client = ParallelSSHClient(**pssh_config)
            shells = client.open_shell()
            client.run_shell_commands(
                shells,
                cmd,
            )
            client.join_shells(shells)
        except ShellError as e:
            self.logger.error(e)
            # ToDO clean up remote workers
            raise SwarmException()

    def run_workers_locally(self):
        """Run workers on the current host"""

        self.logger.info("About to start local workers")
        master_options = self.config.get("locust_master_options")

        cpu_count = multiprocessing.cpu_count()
        if self.args.num_workers > cpu_count:
            self.logger.warning(
                f"Number of workers greater than number of cores: {cpu_count}"
            )

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
                self.args.master_host,
                "--params",
                self.args.xpand_params,
            ]
        )
        self.logger.info(f"Starting all {self.args.num_workers} workers")
        # TODO This should be instance variable and master should check that there is no fatal errors in workers (see below) and they are still running
        # This will required non blocking read from Popen - https://pypi.org/project/python-nonblock/
        running_procs = []
        for i in range(self.args.num_workers):
            cmd = worker_cmd + f" </dev/null >worker{i}.out 2>&1"
            self.logger.debug(f"Running {cmd}")
            running_procs.append(RunSubprocess(cmd=cmd).run_as_shell(wait=False))
            # TODO check that they has started at least
            # Fatal error has happened (2003, "Can't connect to MySQL server

    # TODO clean up
    def cleanup(self):
        """Clean up workers before starting new one"""
