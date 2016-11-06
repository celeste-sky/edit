#!/usr/bin/env python3
# Copyright 2016 Iain Peet
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from gi.repository import GObject

import os.path

class UILocation(GObject.GObject):
    '''
    Mirrors graph.node.Location, but a GObject so it may be sent in a
    signal.
    '''
    def __init__(self, location):
        super(UILocation, self).__init__()
        self.path = location.path
        self.line = location.line
        self.column = location.column
        
class UIPath(GObject.GOjbect):
    'Wrap workspace.path.Path in a GObject'
    
    def __init__(self, path):
        super(UIPath, self).__init__()
        self.path = path        
        