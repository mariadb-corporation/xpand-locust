#!/bin/bash

# Setup pyenv

# clean any previous installations
export PYENV_ROOT="${HOME}/.pyenv"
rm -rf ${PYENV_ROOT}

# From https://github.com/pyenv/pyenv-installer
curl https://pyenv.run | bash

# Todo update bashrc only if pyenv not in path already
#if command -v pyenv 1>/dev/null 2>&1; then
#  eval "$(pyenv init -)"
#fi

echo 'export PYENV_ROOT="$HOME/.pyenv"' >>~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >>~/.bashrc
echo 'eval "$(pyenv init --path)"' >>~/.bashrc

echo "Done with pyenv"
