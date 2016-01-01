#!/usr/bin/env python3
# Copyright 2015 Iain Peet
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import ast
import logging
import graph.edge as edge
import graph.node as node
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

class PyFile(node.File):
    def __init__(self, path, workspace, finder=imp.find_module, no_load=False):
        super(PyFile, self).__init__(path)
        self.workspace = workspace
        self.finder = finder
        self.imports = set() # {'path'}
        self.functions = [] # [node.Function]
        self.classes = [] # [node.Class]
        
        if not no_load:
            self._load()
        
    def _load(self):
        with open(self.path) as f:
            try:
                tree = ast.parse(f.read())
            except SyntaxError as e:
                logging.info("Couldn't parse {}: {}".format(self.path, e))
                return
            
        parsed_imports = [] #[(name, maybe_not_module), ...]
        self.functions = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for name in n.names:
                    parsed_imports.append((name.name, False))
            if isinstance(n, ast.ImportFrom):
                parsed_imports.append((n.module, False))
                for name in n.names:
                    parsed_imports.append(
                        ('{}.{}'.format(n.module, name.name), True))
            if isinstance(n, ast.FunctionDef):
                f = node.Function(n.name)
                f.declarations = [node.Location(self.path, n.lineno, n.col_offset)]
                self.functions.append(f)
            if isinstance(n, ast.ClassDef):
                c = node.Class(n.name)
                c.declarations = [node.Location(self.path, n.lineno, n.col_offset)]
                self.classes.append(c)     
        
        new_imports = set() 
        for name, maybe_not_module in parsed_imports:
            try:
                parent, paths = resolve_import(name, self.finder, self.workspace.python_path)
                new_imports.update(set(os.path.realpath(p) for p in paths))
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
            if not d:
                # This happens when python resolves a dependency on a file we
                # don't understand...
                continue
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
       
import tempfile
import unittest
import unittest.mock as mock
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
            
    def test_function_def(self):
        with open(self.src, 'w') as f:
            f.write('def foo():\n  pass\n')
        p = PyFile(self.src, self.ws)
        f, = p.functions
        self.assertEqual(f.name, 'foo')
        self.assertEqual(f.declarations, [node.Location(self.src, 1, 0)])
        
    def test_nested_function(self):
        with open(self.src, 'w') as f:
            f.write('\n'.join([
                'def foo():',
                '  def bar():',
                '    pass',
                '']))
        p = PyFile(self.src, self.ws)
        f1, f2 = p.functions
        self.assertEqual(f1.name, 'foo')
        self.assertEqual(f1.declarations, [node.Location(self.src, 1, 0)])
        self.assertEqual(f2.name, 'bar')
        self.assertEqual(f2.declarations, [node.Location(self.src, 2, 2)])
        
    def test_method(self):
        with open(self.src, 'w') as f:
            f.write('\n'.join([
                'class Foo(object):',
                '  def foo():',
                '    pass',
                '']))
        p = PyFile(self.src, self.ws)
        f, = p.functions
        self.assertEqual(f.name, 'foo')
        self.assertEqual(f.declarations, [node.Location(self.src, 2, 2)])
        
    def test_class(self):
        with open(self.src, 'w') as f:
            f.write('class Foo(object):\n  pass\n')
        p = PyFile(self.src, self.ws)
        c, = p.classes
        self.assertEqual(c.name, 'Foo')
        self.assertEqual(c.declarations, [node.Location(self.src, 1, 0)])        
        
if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR)
    unittest.main()
    
