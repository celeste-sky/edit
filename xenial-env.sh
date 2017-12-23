# Initial config:
# - sudo apt install python3-pip 
# - python3 -m pip install -U mypy
# - install https://github.com/pyenv/pyenv per README.  This script assumes you 
#   clone to $HOME/git/pyenv
#   - sudo apt-get install -y build-essential libbz2-dev libssl-dev libreadline-dev libsqlite3-dev tk-dev
#   - pyenv install 3.6.3 && pyenv install 2.7.11
# - source this file
# - Add gtk3 to the 3.6.3 pyenv:
#   - sudo apt install libcairo2-dev libglib2.0-dev libgirepository1.0-dev
#   - git clone git@github.com:pygobject/pycairo; install using setup.py install
#   - git clone git://git.gnome.org/pygobject; install using setup.py install

# Where pip puts mypy:
export PATH=$PATH:$HOME/.local/bin

export PYENV_ROOT=$HOME/git/pyenv
export PATH=$PYENV_ROOT/bin:$PATH
eval "$(pyenv init -)"
# 2.7.11 to roughly match current xenial default, 3.6.3 as current release.
pyenv shell 2.7.11 3.6.3

