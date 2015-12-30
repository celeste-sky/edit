#!/usr/bin/env python3
# Copyright 2015 Iain Peet
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import collections
from graph.edge import Edge

class Node(object):
    def __init__(self):
        self.outgoing = set() # {Edge}
        self.incoming = set() # {Edge}

class File(Node):
    def __init__(self, path):
        super(Function, self).__init__()
        self.path = path

Location = collections.namedtuple('Location', ['file', 'line', 'column'])
        
class Name(Node):
    '''
    Something which has a name and is declared in a a file.
    (variable, function, class, etc.)
    '''
    def __init__(self, name):
        super(Function, self).__init__()
        self.name = name
        # List of Location this name is declared (multiple being expected,
        # considering current lack of any namespace comprehension)
        self.declarations = []
        
 class Function(Name):
    pass
    
class Variable(Name):
    pass
    
class Class(Name):
    pass
    
class Call(Name):
    pass
    
class Reference(Name):
    '''
    An assignment / load of some variable.
    '''
    pass
