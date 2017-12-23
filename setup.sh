#!/bin/bash
#
# Install needed dependencies.  Obviously Debian-specific, and probably
# Ubuntu-specific.  Tested on Ubuntu 17.10, which is probably the current
# minimum, for python 3.6.

set -e

if ! dpkg -s libgtksourceview-3.0-dev >/dev/null 2>&1; then
    echo 'Installing libgtksourceview-3.0-dev'
    sudo apt-get install libgtksourceview-3.0-dev
fi

if ! dpkg -s mypy >/dev/null 2>&1; then
    echo 'Installing mypy'
    sudo apt-get install mypy
fi
