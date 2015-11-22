#!/usr/bin/python

from argparse import Namespace
import collections

EdgeType = Namespace(
    IMPORT='import'
)

Edge = collections.namedtuple('Edge', ['type', 'node'])
