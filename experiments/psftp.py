#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 dvolkov

import os
from datetime import datetime

from gevent import joinall
from pssh.clients import ParallelSSHClient

client = ParallelSSHClient(
    hosts=["yin01a"], user="root", password="", timeout=1, num_retries=1, pkey=None
)
local_file = "/Users/dmitryvolkov/GitHub/xpand-locust/examples"
remote_file = "/tmp"
cmd = client.copy_file(local_file, remote_file, recurse=True)
joinall(cmd, raise_error=True)
