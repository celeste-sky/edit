#!/usr/bin/python

import ast
import logging
import graph.edge as edge
from graph.node import Node
import imp
import os.path

def resolve_import(name, finder, extra_search):
    if 'os.path' == name:
        # paper over dynamic import hijinks 
        return None, [i.replace('.pyc', '.py') for i in [
            os.__file__, os.path.__file__]]
        
    if '.' in name:
        pkg, mod = name.rsplit(".", 1)
        parent, paths = resolve_import(pkg, finder, extra_search)
    else:
        mod = name
        parent = None
        paths = []
    
    if parent:
        f, pathname, desc = finder(mod, [parent])
    else:
        try:
            f, pathname, desc = finder(mod, None)
        except ImportError:
            if not extra_search:
                raise
            f, pathname, desc = finder(mod, extra_search)
         
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
    elif desc[2] == imp.C_BUILTIN:
        return None, paths
    else:
        raise ImportError('Unknown module type: {}'.format(desc[2]))

class PyFile(Node):
    def __init__(self, path, workspace, finder=imp.find_module, no_load=False):
        super(PyFile, self).__init__()
        self.path = path
        self.workspace = workspace
        self.finder = finder
        self.imports = set()
        
        if not no_load:
            self._load_imports()
        
    def _load_imports(self):
        with open(self.path) as f:
            try:
                tree = ast.parse(f.read())
            except SyntaxError as e:
                logging.info("Couldn't parse {}: {}".format(self.path, e))
                return
            
        parsed = [] #[(name, maybe_not_module), ...]
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for name in n.names:
                    parsed.append((name.name, False))
            if isinstance(n, ast.ImportFrom):
                parsed.append((n.module, False))
                for name in n.names:
                    parsed.append(
                        ('{}.{}'.format(n.module, name.name), True))
        
        new_imports = set() 
        for name, maybe_not_module in parsed:
            try:
                parent, paths = resolve_import(name, self.finder, self.workspace.python_path)
                new_imports.update(set(os.path.abspath(p) for p in paths))
            except ImportError as e:
                if not maybe_not_module:
                    # ImportError is not interesting if this is a name in 
                    # "from mod import names", as it's probably a non-module
                    # name.
                    logging.info('Failed to resolve {}:{}: {}'.format(
                        self.path, name, e))
        self.imports = new_imports
        
    def visit(self, source_graph):
        for i in self.imports:
            d = source_graph.find_file(i)
            e = edge.Edge(edge.EdgeType.IMPORT, self, d)
            self.outgoing.add(e)
            d.incoming.add(e)
        
def new_file(path, workspace, external=False):
    if path.endswith('.py'):
        return PyFile(path, workspace, no_load=external)
    elif path.endswith('.pyc'):
        return None
    elif os.path.isdir(path):
        return None
    else:
        logging.debug('Unrecognized file type: {}'.format(path))
        return None            

import mock        
import tempfile
import unittest
import shutil

def make_finder(modules):
    def res(name, paths):
        paths = tuple(paths) if paths else None
        if (name, paths) in modules:
            path, typ = modules[(name, paths)]
            return (None, path, (None, None, typ))
        else:
            raise ImportError('Failed to find {} in {}'.format(
                name, paths))
    return res

class ResolveImportTest(unittest.TestCase):        
    def test_resolve_top(self):
        mock_finder = make_finder({
            ('mod', None): ('mod.py', imp.PY_SOURCE)
        })
        parent, paths = resolve_import('mod', mock_finder, None)
        self.assertIsNone(parent)
        self.assertEqual(paths, ['mod.py'])
        
    def test_resolve_pkg(self):
        mock_finder = make_finder({
            ('pkg', None): ('pkg/', imp.PKG_DIRECTORY)
        })
        parent, paths = resolve_import('pkg', mock_finder, None)
        self.assertEqual(parent, 'pkg/')
        self.assertEqual(paths, ['pkg/__init__.py'])
        
    def test_resolve_in_pkg(self):
        mock_finder = make_finder({
            ('mod', ('pkg/',)): ('pkg/mod.py', imp.PY_SOURCE),
            ('pkg', None): ('pkg/', imp.PKG_DIRECTORY)
        })
        parent, paths = resolve_import('pkg.mod', mock_finder, None)
        self.assertIsNone(parent)
        self.assertEqual(paths, ['pkg/__init__.py', 'pkg/mod.py'])

class PyFileTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.src = os.path.join(self.dir, 'src.py')
        self.modules = {
            ('mod', ('/root/pkg/',)): ('/root/pkg/mod.py', imp.PY_SOURCE),
            ('pkg', ('/root/',)): ('/root/pkg/', imp.PKG_DIRECTORY),
            ('root', None): ('/root/', imp.PKG_DIRECTORY)
        }
        self.ws = mock.MagicMock()
        
    def tearDown(self):
        shutil.rmtree(self.dir)
        
    def test_load_empty(self):
        open(self.src, 'w').close()
        p = PyFile(self.src, self.ws)
        self.assertEqual(p.imports, set())
        
    def test_load_malformed(self):
        with open(self.src, 'w') as f:
            f.write('invalid python')
        p = PyFile(self.src, self.ws, make_finder({}))
        self.assertEqual(p.imports, set())
        
    def test_load_import(self):
        with open(self.src, 'w') as f:
            f.write('import root.pkg.mod')
        mock_finder = make_finder(self.modules)
        p = PyFile(self.src, self.ws, mock_finder)
        self.assertEqual(p.imports, 
            {'/root/__init__.py', '/root/pkg/__init__.py', '/root/pkg/mod.py'})
            
    def test_load_multi_import_as(self):
        with open(self.src, 'w') as f:
            f.write('import root.foo as f, root.pkg.mod as m')
        self.modules.update({
            ('foo', ('/root/',)): ('/root/foo.py', imp.PY_SOURCE)
        })
        p = PyFile(self.src, self.ws, make_finder(self.modules))
        self.assertEqual(p.imports,  {
            '/root/__init__.py', 
            '/root/foo.py',
            '/root/pkg/__init__.py', 
            '/root/pkg/mod.py'
        })
        
    def test_load_from_import_nonmod(self):
        with open(self.src, 'w') as f:
            f.write('from root.pkg import Classy')
        p = PyFile(self.src, self.ws, make_finder(self.modules))
        self.assertEqual(p.imports, 
            {'/root/__init__.py', '/root/pkg/__init__.py'})
            
    def test_load_from_import_mod(self):
        with open(self.src, 'w') as f:
            f.write('from root.pkg import mod')
        p = PyFile(self.src, self.ws, make_finder(self.modules))
        self.assertEqual(p.imports, 
            {'/root/__init__.py', '/root/pkg/__init__.py', '/root/pkg/mod.py'})
        
if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR)
    unittest.main()
    
