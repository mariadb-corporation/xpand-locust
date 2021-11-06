# -*- coding: utf-8 -*-
# Copyright (C) 2021 dvolkov


class SwarmException(Exception):
    """An Swarm generic error occurred."""


class ProcessExecutonException(Exception):
    """An HTTP error occurred."""

    def __init__(self, err_message=None):
        self.err_message = err_message

    def __str__(self):
        return "{err_message}".format(err_message=self.err_message)


class CommandException(ProcessExecutonException):
    """A process failed"""


class TimeoutException(ProcessExecutonException):
    """A process timeout"""
