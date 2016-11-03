#!/usr/bin/env python3
# Copyright 2015 Iain Peet
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkSource', '3.0')

import logging
import os.path
import unittest

if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR)
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.dirname(__file__), '*.py')
    unittest.TextTestRunner(verbosity=2).run(suite)
    
