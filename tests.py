#!/usr/bin/python

import logging
import os.path
import unittest

if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR)
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.dirname(__file__), '*.py')
    unittest.TextTestRunner(verbosity=2).run(suite)
    