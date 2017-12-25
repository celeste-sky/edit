#!/usr/bin/env python3
# Copyright 2017 Iain Peet
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from enum import Enum
from typing import NamedTuple, Optional
from workspace.path import Path

class SymbolType(Enum):
    '''
    Symbol type.  Note that values may be persisted to disk in indexes; changes
    in existing values may be a schema change.
    '''
    CLASS = 1
    FUNCTION = 2
    VALUE = 3

    CALL = 100
    REFERENCE = 101
    IMPORT = 102

class Symbol(NamedTuple):
    path: Path
    line: int
    column: int
    name: str
    sym_type: SymbolType