#!/usr/bin/env python3
# Copyright 2018 Iain Peet
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from graph.db import DB
from graph.node import Location
from graph.symbol import Symbol
from typing import Optional

class Landmark(object):
    def __init__(self, loc: Location) -> None:
        self.location = loc

class Walker(object):
    def __init__(self, db: DB) -> None:
        self.db = db
        self._location : Optional[Location] = None
        
    @property
    def location(self) -> Location:
        pass
        
    @location.setter
    def location(self, loc : Location) -> None:
        self._location = loc
        
    @property
    def landmark(self) -> Landmark:
        pass
        
    @landmark.setter
    def landmark(self, loc : Landmark) -> None:
        pass
        
    def create_landmark(self) -> Landmark:
        '''
        Mark the current location as a landmark of interest, make it the current
        landmark, and create an edge to it from the previous landmark.
        '''
        pass
        
    def link_landmark(self,
            src: Optional[Landmark] = None,
            dest: Optional[Landmark] = None) -> None:
        '''
        Create an edge from the landmark at src to the one at dest.
        If src is not given, use the current landmark.  If dst is not given, use a 
        landmark near to the current location, or create one at the current 
        location.
        '''
        pass
        
    def find_nearest_landmark(self, loc: Location) -> Optional[Landmark]:
        '''
        Find the landmark nearest the given location, and return it.  If no nearby
        landmark is found, return None.
        '''
        pass
    