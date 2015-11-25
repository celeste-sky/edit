#!/usr/bin/python

from graph.edge import Edge, EdgeType
import graph.file
import logging
import workspace.workspace as workspace

class SourceGraph(object):
    def __init__(self, workspace):
        self.workspace = workspace
        # {abspath: FileNode}
        self.files, self.ext_files = self._load_files()
        
        # connect all workspace files
        for f in self.files.values():
            f.visit(self)
        
    def _load_files(self):
        # First, load all the files in the workspace
        files = {}
        for p in self.workspace.files:
            f = graph.file.new_file(p, self.workspace)
            if f:
                logging.info('Loaded file: {}'.format(p))
                files[p] = f
        
        # Now, check each files for imports external to the workspace
        ext_files = {}
        for f in files.values():
            ext = f.imports.difference(self.workspace.files)
            ext_files.update({e: None for e in ext})
        
        # Load all the external files
        for p in ext_files.keys():
            ext_files[p] = graph.file.new_file(p, self.workspace, external=True)
            if not ext_files[p]:
                del ext_files[p]
                
        return files, ext_files
    
    def find_file(self, path):
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
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.ws = os.path.join(self.dir, '.workspace')
        os.mkdir(self.ws)
        with open(os.path.join(self.ws, 'config'), 'w') as f:
            f.write('{"python_path": [ "'+self.dir+'" ] }')
        
    def tearDown(self):
        shutil.rmtree(self.dir)
        
    def test_src_graph(self):
        with open(os.path.join(self.dir, 'foo.py'), 'w') as f:
            f.write('import bar, baz')
        with open(os.path.join(self.dir, 'bar.py'), 'w') as f:
            f.write('import foo, baz')
        with open(os.path.join(self.dir, 'baz.py'), 'w') as f:
            f.write('import shutil')
        w = workspace.Workspace(self.ws)
        sg = SourceGraph(w)
        
        self.assertEqual(set(sg.files.keys()),
            set(os.path.join(self.dir, f) for f in [
                'foo.py', 'bar.py', 'baz.py'])) 
        self.assertEqual(sg.ext_files.keys(), [
            shutil.__file__.replace('.pyc', '.py')])
        
        foon = sg.find_file(os.path.join(self.dir, 'foo.py'))
        barn = sg.find_file(os.path.join(self.dir, 'bar.py'))
        bazn = sg.find_file(os.path.join(self.dir, 'baz.py'))
        shutiln = sg.find_file(os.path.join(shutil.__file__.replace('.pyc', '.py')))
        
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
