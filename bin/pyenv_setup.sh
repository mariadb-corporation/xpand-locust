#!/bin/bash

# Setup pyenv

# clean any previous installations
export PYENV_ROOT="${HOME}/.pyenv"
rm -rf ${PYENV_ROOT}

# From https://github.com/pyenv/pyenv-installer
curl https://pyenv.run | bash

# update bashrc only if pyenv not in path already
if ! command -v pyenv 1>/dev/null 2>&1; then
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >>~/.bashrc
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >>~/.bashrc
    echo 'eval "$(pyenv init --path)"' >>~/.bashrc
fi

echo "Done with pyenv"
