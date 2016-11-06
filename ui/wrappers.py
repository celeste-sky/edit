#!/usr/bin/env python3
# Copyright 2016 Iain Peet
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

'''
These classes exist as a bit of a hack to reconcile the desire to pass
objects from workspace/ and graph/ around in GObject signals with the
desire to avoid entwining Gtk into those packages.
'''

from gi.repository import GObject

import os.path

class UILocation(GObject.GObject):
    'Wrap graph.node.Location in a GObject'
    
    def __init__(self, location):
        super(UILocation, self).__init__()
        self.path = location.file
        self.line = location.line
        self.column = location.column
        
class UIPath(GObject.GObject):
    'Wrap workspace.path.Path in a GObject'
    
    def __init__(self, path):
        super(UIPath, self).__init__()
        self.path = path
        