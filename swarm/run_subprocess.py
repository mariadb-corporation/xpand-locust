# -*- coding: utf-8 -*-
# Copyright (C) 2021 dvolkov

"""Run suprocess 

"""
import logging
import shlex
import subprocess
from typing import Any, List, Optional

from .exceptions import CommandException, TimeoutException

DEFAULT_TIMEOUT = 5 * 60


class RunSubprocess:
    def __init__(self, cmd: str, timeout: int = DEFAULT_TIMEOUT):
        self.logger = logging
        self.cmd = cmd
        self.timeout = timeout

    def run(self, wait: bool = True):
        """[Split arguments into arrray and then executed it]

        Returns:
            tuple: stdout,stdin,error code
        """

        cmd = shlex.split(self.cmd)
        if wait:
            return self._run(cmd, shell=False)
        else:
            return self._run_no_wait(cmd, shell=False)

    def run_as_shell(self, wait: bool = True):
        """This version for complex commands like using | (shell only)

        Returns:
            tuple: stdout,stdin,error code
        """
        if wait:
            return self._run(self.cmd, shell=True)
        else:
            return self._run_no_wait(self.cmd, shell=True)

    def _run_no_wait(self, cmd, shell: bool = False):
        """Run process and return Popen object whiteout  waiting:

        Args:
            cmd ([type]): [description]
            shell (bool, optional): [description]. Defaults to False.
        """
        self.logger.debug(f"Executing command {self.cmd}")

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=shell,
                universal_newlines=True,
            )
            return proc

        except FileNotFoundError as e:
            raise CommandException(f"Command {cmd} failed with: {e}")

    def _run(self, cmd, shell: bool = False):
        """
        Run process and wait until completion
        Returns:
            tuple: stdout,stdin,error code
        """

        try:
            proc = self._run_no_wait(cmd, shell)

            stdout, stderr = proc.communicate(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            raise TimeoutException(
                f"Command {cmd} timed out after {self.timeout} seconds"
            )

        stdout_str = stdout.decode("utf-8")
        stderr_str = stderr.decode("utf-8")

        if proc.returncode != 0:
            raise CommandException(
                f"Command {cmd} failed with {stderr_str}, error code {proc.returncode}"
            )

        return (stdout_str, stderr_str, proc.returncode)
