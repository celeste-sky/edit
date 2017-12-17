#!/usr/bin/env python3
# Copyright 2015 Iain Peet
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import collections
from graph.edge import Edge
from typing import Set
from workspace.path import Path

class Node(object):
    def __init__(self) -> None:
        self.outgoing: Set[Edge] = set() 
        self.incoming: Set[Edge] = set()

class File(Node):
    def __init__(self, path:Path) -> None:
        super(File, self).__init__()
        self.path = path

Location = collections.namedtuple('Location', ['file', 'line', 'column'])
