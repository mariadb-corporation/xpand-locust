#!/bin/bash

# Setup env variables
[[ ${XPAND_LOCUST_HOME} ]] || {
    echo 'export XPAND_LOCUST_HOME="$HOME/tools/xpand-locust"' >>~/.bashrc
    echo 'export PYTHONPATH="$XPAND_LOCUST_HOME"' >>~/.bashrc
    echo 'export PATH="$XPAND_LOCUST_HOME/bin:$PATH"' >>~/.bashrc
}
