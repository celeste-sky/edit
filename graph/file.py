#!/usr/bin/python

import ast
import graph.edge as edge
from graph.node import Node
import imp
import os.path

def resolve_import(name, finder):
    if "." in name:
        pkg, mod = name.rsplit(".", 1)
        parent, paths = resolve_import(pkg, finder)
    else:
        mod = name
        parent = None
        paths = []
    
    search = [parent] if parent else None
    f, pathname, desc = finder(mod, search)
    if f:
        f.close()
    
    if desc[2] == imp.PY_SOURCE:
        assert pathname
        paths.append(pathname)
        return None, paths
    elif desc[2] == imp.PKG_DIRECTORY:
        assert pathname
        paths.append(os.path.join(pathname, '__init__.py'))
        return pathname, paths
    else:
        raise ImportError('Unknown module type: {}'.format(desc[2]))

class PyFile(Node):
    def __init__(self, path, finder=imp.find_module):
        super(PyFile, self).__init__()
        self.path = path
        self._load()
        
    def _load(self):
        with open(self.path) as f:
            tree = ast.parse(f.read())
            
        imports = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for name in n.names:
                    imports.append(name.name)
         
        for name in imports:
            pass
        
import tempfile
import unittest
import shutil

class ResolveImportTest(unittest.TestCase):
    def make_finder(self, modules):
        def res(name, paths):
            paths = tuple(paths) if paths else None
            if (name, paths) in modules:
                path, typ = modules[(name, paths)]
                return (None, path, (None, None, typ))
            else:
                raise ImportError('Failed to find {} in {}'.format(
                    name, paths))
        return res
        
    def test_resolve_top(self):
        mock_finder = self.make_finder({
            ('mod', None): ('mod.py', imp.PY_SOURCE)
        })
        parent, paths = resolve_import('mod', mock_finder)
        self.assertIsNone(parent)
        self.assertEqual(paths, ['mod.py'])
        
    def test_resolve_pkg(self):
        mock_finder = self.make_finder({
            ('pkg', None): ('pkg/', imp.PKG_DIRECTORY)
        })
        parent, paths = resolve_import('pkg', mock_finder)
        self.assertEqual(parent, 'pkg/')
        self.assertEqual(paths, ['pkg/__init__.py'])
        
    def test_resolve_in_pkg(self):
        mock_finder = self.make_finder({
            ('mod', ('pkg/',)): ('pkg/mod.py', imp.PY_SOURCE),
            ('pkg', None): ('pkg/', imp.PKG_DIRECTORY)
        })
        parent, paths = resolve_import('pkg.mod', mock_finder)
        self.assertIsNone(parent)
        self.assertEqual(paths, ['pkg/__init__.py', 'pkg/mod.py'])

class PyFileTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.src = os.path.join(self.dir, 'src.py')
        
    def tearDown(self):
        shutil.rmtree(self.dir)
        
    def test_load_empty(self):
        open(self.src, 'w').close()
        p = PyFile(self.src)
        
    def test_load_import(self):
        with open(self.src, 'w') as f:
            f.write("import graph.file")
        p = PyFile(self.src)
        self.assertEqual(p.outgoing, 
            {os.path.abspath('graph/file.py')})

if __name__ == '__main__':
    unittest.main()
    