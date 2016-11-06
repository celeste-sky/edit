#!/usr/bin/env python3
# Copyright 2016 Iain Peet
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import os.path

class Path(object):
    '''
    Represents a particular location in the filesystem.  Also knows where the
    workspace root is, enabling useful abs-relative transformations, etc.
    '''
    
    def __init__(self, path, ws_root):
        super(Path, self).__init__()
        if os.path.isabs(path):
            self.abs = path
        else:
            self.abs = os.path.join(ws_root, path)
        self._ws_root = ws_root
           
    @property
    def rel(self):
        return os.path.relpath(self.abs, self._ws_root)
        
    @property
    def in_workspace(self):
        return self.abs.startswith(self._ws_root)
        
    def abbreviate(self, max_len=32, require_basename=True):
        '''
        Returns the shortest possible path (whether abs or relative), removing 
        characters from the middle if required to meet the given maximum.
        If require_basename is True, the abbreviation will always include the 
        full basename.  If the basename is longer than max_len, max_len is not
        respected.
        '''
        assert max_len >= 16
        res = self.rel if len(self.rel)  < len(self.abs) else self.abs
        if len(res) <= max_len:
            return res
        else:
            # Trim some out of the middle.  On the basis that the suffix is
            # probably most  important, and then the prefix, allocate 2/3 
            # of our chars to the suffix, with remaining third less the '..' 
            # going to the prefix.
            suffix_count = int(max_len * 2 / 3)
            if require_basename:
                if suffix_count < len(os.path.basename(res)):
                    suffix_count = len(os.path.basename(res))
            prefix_count = max_len - suffix_count - 2
            if prefix_count < 0:
                # Can occur with a long basename and require_basename
                prefix_count = 0
            return res[:prefix_count] + '..' + res[-suffix_count:]
            
import unittest

class PathTest(unittest.TestCase):
    def test_abbrev_rel_shorter(self):
        p = Path('/foo/bar', '/foo')
        self.assertEqual(p.abbreviate(), 'bar')
        
    def test_abbrev_abs_shorter(self):
        p = Path('/foo/bar', '/baz')
        self.assertEqual(p.abbreviate(), '/foo/bar')
        
    def test_abbrev_shortest(self):
        p = Path('/this/isareally/very/annoyingly/perversely/even/path', 'foo')
        self.assertEqual(p.abbreviate(max_len=16), '/thi../even/path')
        
    def test_abbrev_require_long_basename(self):
        p = Path('/foo/this_is_a_very_long_basename', '/bar')
        self.assertEqual(p.abbreviate(max_len=16), 
            '..this_is_a_very_long_basename')

if __name__ == '__main__':
    unittest.main()
    