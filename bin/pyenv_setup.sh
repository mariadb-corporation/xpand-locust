#!/bin/bash

# Setup Pyhton 3 using pyenv
sudo yum install gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite \
    sqlite-devel openssl-devel xz xz-devel libffi-devel

sudo yum -y remove git-*
sudo yum -y remove git-*
sudo yum -y install https://packages.endpoint.com/rhel/7/os/x86_64/endpoint-repo-1.9-1.x86_64.rpm

sudo yum -y install git

# clean any previous installations
export PYENV_ROOT="${HOME}/.pyenv"
rm -rf ${PYENV_ROOT}

# From https://github.com/pyenv/pyenv-installer
curl https://pyenv.run | bash

echo 'export PYENV_ROOT="$HOME/.pyenv"' >>~/.bash_profile
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >>~/.bash_profile
echo 'eval "$(pyenv init --path)"' >>~/.bash_profile

echo "Done with pyenv"
