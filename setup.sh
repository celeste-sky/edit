#!/bin/bash
#
# Install needed dependencies.  Obviously debian-specific.

set -e

if ! dpkg -s libgtksourceview-3.0-dev >/dev/null 2>&1; then
    echo 'Installing libgtksourceview-3.0-dev'
    sudo apt-get install libgtksourceview-3.0-dev
fi

