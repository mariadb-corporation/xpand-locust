#!/bin/bash

# Setup Python 3 using pyenv
sudo yum -y install gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite \
    sqlite-devel openssl-devel xz xz-devel libffi-devel

pyenv update
pyenv install -f 3.9.5

# How to switch versions https://realpython.com/intro-to-pyenv/
echo "Installing Python-3.9.5..."
pyenv global 3.9.5
pip install --upgrade pip

python --version
echo "Done with python setup"
