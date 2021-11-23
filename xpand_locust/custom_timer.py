#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 dvolkov

import inspect
import sys
import time

from locust import events


def custom_timer(func):
    """
    Measure time and send to Locust
    https://docs.locust.io/en/stable/api.html#events
    """

    def func_wrapper(*args, **kwargs):
        """wrap functions and measure time"""

        previous_frame = inspect.currentframe().f_back
        (filename, line_number, function_name, lines, index) = inspect.getframeinfo(
            previous_frame
        )

        start_time = time.time()
        result = None
        clf = args[0]  # Class instance og the calling function.
        try:
            result = func(*args, **kwargs)
            result_len = result if isinstance(result, int) else len(result)

        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            events.request_failure.fire(
                request_type="CUSTOM",
                name=function_name,
                response_time=total_time,
                exception=e,
                response_length=0,
                request_id="none",
            )  ##   clf.ps.request_id or "none")
        else:
            total_time = int((time.time() - start_time) * 1000)
            events.request_success.fire(
                request_type="CUSTOM",
                name=function_name,
                response_time=total_time,
                response_length=result_len,  # clf.ps.content_length
                request_id="none",
            )
        return result

    return func_wrapper
