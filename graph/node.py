#!/usr/bin/python

from graph.edge import Edge

class Node(object):
    def __init__(self):
        self.outgoing = set() # {Edge}
        self.incoming = set() # {Edge}
        