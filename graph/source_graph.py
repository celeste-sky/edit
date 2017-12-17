#!/usr/bin/env python3
# Copyright 2015 Iain Peet
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from graph.edge import Edge, EdgeType
from graph.py_file import PyFile, new_file
from graph.node import Node
import logging
from typing import Dict, List, Tuple
from workspace import Workspace
from workspace.path import Path

class SourceGraph(object):
    def __init__(self, workspace:Workspace) -> None:
        self.workspace = workspace
        self.files, self.ext_files = self._load_files()

        # connect all workspace files
        for f in self.files.values():
            f.visit(self)

    def _load_files(self) -> Tuple[Dict[Path, PyFile], Dict[Path, PyFile]]:
        # First, load all the files in the workspace
        files = {}
        for p in self.workspace.files:
            f = new_file(p, self.workspace)
            if f:
                logging.debug('Loaded file: {}'.format(p))
                files[p] = f

        # Now, check each files for imports external to the workspace
        ext_files:Dict = {}
        for f in files.values():
            ext = [i for i in f.imports if not i in files]
            ext_files.update({e: None for e in ext})

        # Load all the external files
        for p in ext_files.keys():
            ext_files[p] = new_file(p, self.workspace, external=True)
            if not ext_files[p]:
                del ext_files[p]

        return files, ext_files

    def find_file(self, path:Path) -> PyFile:
        assert isinstance(path, Path), str(path)
        if path in self.files:
            return self.files[path]
        elif path in self.ext_files:
            return self.ext_files[path]
        else:
            return None

import os.path
import shutil
import sys
import tempfile
import unittest

class SourceGraphTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.mkdtemp()
        self.ws = os.path.join(self.dir, '.workspace')
        os.mkdir(self.ws)
        with open(os.path.join(self.ws, 'config'), 'w') as f:
            f.write('{"python_path": [ "'+self.dir+'" ] }')

    def tearDown(self) -> None:
        shutil.rmtree(self.dir)

    def test_src_graph(self) -> None:
        with open(os.path.join(self.dir, 'foo.py'), 'w') as f:
            f.write('import bar, baz')
        with open(os.path.join(self.dir, 'bar.py'), 'w') as f:
            f.write('import foo, baz')
        with open(os.path.join(self.dir, 'baz.py'), 'w') as f:
            f.write('import shutil')
        w = Workspace(self.ws)
        sg = SourceGraph(w)

        self.assertEqual(set(sg.files.keys()),
            set(Path(f, self.dir) for f in ['foo.py', 'bar.py', 'baz.py']))
        self.assertEqual(
            list(sg.ext_files.keys()),
            [Path(shutil.__file__.replace('.pyc', '.py'), self.dir)])

        foon = sg.find_file(Path('foo.py', self.dir))
        barn = sg.find_file(Path('bar.py', self.dir))
        bazn = sg.find_file(Path( 'baz.py', self.dir))
        shutiln = sg.find_file(Path(
            shutil.__file__.replace('.pyc', '.py'), self.dir))

        self.assertEqual(foon.outgoing, set([
            Edge(EdgeType.IMPORT, foon, barn),
            Edge(EdgeType.IMPORT, foon, bazn)]))
        self.assertEqual(foon.incoming, set([
            Edge(EdgeType.IMPORT, barn, foon)]))

        self.assertEqual(barn.outgoing, set([
            Edge(EdgeType.IMPORT, barn, foon),
            Edge(EdgeType.IMPORT, barn, bazn)]))
        self.assertEqual(barn.incoming, set([
            Edge(EdgeType.IMPORT, foon, barn)]))

        self.assertEqual(bazn.outgoing, set([
            Edge(EdgeType.IMPORT, bazn, shutiln)]))
        self.assertEqual(bazn.incoming, set([
            Edge(EdgeType.IMPORT, foon, bazn),
            Edge(EdgeType.IMPORT, barn, bazn)]))


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
