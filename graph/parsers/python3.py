#!/usr/bin/env python3
# Copyright 2017 Iain Peet
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import ast
from graph.db import Symbol, SymbolType
import imp
import logging
import os.path
from typing import Callable, Dict, IO, List, Optional, Tuple
from workspace.path import Path

# The signature of imp.find_module
# XXX: which is deprecated since 3.3...
FoundDesc = Tuple[Optional[str], Optional[str], int]
Finder = Callable[[str, List[str]], Tuple[IO, str, FoundDesc]]

def resolve_import(name:str, finder:Finder, extra_search:List[str]
        ) -> Tuple[Optional[str], List[str]]:
    '''
    Search for the given name using the given module finder, and optionally
    search in the given additional search dirs.  Return the path for the named
    module, and also a list of the paths for all of that module's parents.
    '''
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

class Py3Parser(object):
    def accept(self, path:Path) -> bool:
        '''
        Determine if this parser is suitable to parse the given path.
        '''
        return path.basename.lower().endswith(".py")

    def parse(self, path:Path) -> List[Symbol]:
        with open(path.abs) as f:
            try:
                tree = ast.parse(f.read())
            except SyntaxError as e:
                logging.info("Couldn't parse {}: {}".format(path, e))
                raise

        res:List[Symbol] = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for name in n.names:
                    res.append(Symbol(path, n.lineno, n.col_offset, None, None,
                        name.name, SymbolType.IMPORT))
            if isinstance(n, ast.ImportFrom):
                res.append(Symbol(path, n.lineno, n.col_offset, None, None,
                    n.module, SymbolType.IMPORT))
                for name in n.names:
                    res.append(Symbol(path, n.lineno, n.col_offset, None, None,
                        '{}.{}'.format(n.module, name.name), SymbolType.IMPORT))
            if isinstance(n, ast.FunctionDef):
                res.append(Symbol(path, n.lineno, n.col_offset, None, None,
                    n.name, SymbolType.FUNCTION))
            if isinstance(n, ast.ClassDef):
                res.append(Symbol(path, n.lineno, n.col_offset, None, None,
                    n.name, SymbolType.CLASS))
            if isinstance(n, ast.Call):
                s = self._visit_call(path, n)
                if s is not None:
                    res.append(s)
        return res

    def _visit_call(self, path:Path, call:ast.Call) -> Optional[Symbol]:
        # The most common cases are going to be calls of a name ("foo()") or
        # an attr ("obj.foo()").  Of course, the func could be any expression, but
        # won't attempt to do anything with the more obscure cases for now.
        if isinstance(call.func, ast.Name):
            return Symbol(path, call.lineno, call.col_offset, None, None,
                call.func.id, SymbolType.CALL)
        elif isinstance(call.func, ast.Attribute):
            return Symbol(path, call.lineno, call.col_offset, None, None,
                call.func.attr, SymbolType.CALL)
        else:
            return None

import shutil
import tempfile
import unittest

ModuleMap = Dict[
    Tuple[str, Optional[Tuple[str, ...]]], Tuple[str, int]]

def make_finder(modules:ModuleMap) -> Finder:
    def res(name:str, paths:List[str]) -> Tuple[Optional[IO], str, FoundDesc]:
        path_tup:Tuple[str, ...] = tuple(paths) if paths else None
        if (name, path_tup) in modules:
            path, typ = modules[(name, path_tup)]
            return (None, path, (None, None, typ))
        else:
            raise ImportError('Failed to find {} in {}'.format(
                name, path_tup))
    return res

class ResolveImportTest(unittest.TestCase):
    def test_resolve_top(self) -> None:
        mock_finder = make_finder({
            ('mod', None): ('mod.py', imp.PY_SOURCE)
        })
        parent, paths = resolve_import('mod', mock_finder, None)
        self.assertIsNone(parent)
        self.assertEqual(paths, ['mod.py'])

    def test_resolve_pkg(self) -> None:
        mock_finder = make_finder({
            ('pkg', None): ('pkg/', imp.PKG_DIRECTORY)
        })
        parent, paths = resolve_import('pkg', mock_finder, None)
        self.assertEqual(parent, 'pkg/')
        self.assertEqual(paths, ['pkg/__init__.py'])

    def test_resolve_in_pkg(self) -> None:
        mock_finder = make_finder({
            ('mod', ('pkg/',)): ('pkg/mod.py', imp.PY_SOURCE),
            ('pkg', None): ('pkg/', imp.PKG_DIRECTORY)
        })
        parent, paths = resolve_import('pkg.mod', mock_finder, None)
        self.assertIsNone(parent)
        self.assertEqual(paths, ['pkg/__init__.py', 'pkg/mod.py'])

class Py3ParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.mkdtemp()
        self.src = Path('src.py', self.dir)
        self.p = Py3Parser()

    def tearDown(self) -> None:
        shutil.rmtree(self.dir)

    def test_function_def(self) -> None:
        with open(self.src.abs, 'w') as f:
            f.write('def foo():\n  pass\n')
        self.assertEqual(self.p.parse(self.src),
            [Symbol(self.src, 1, 0, None, None, 'foo', SymbolType.FUNCTION)])

    def test_nested_function(self) -> None:
        with open(self.src.abs, 'w') as f:
            f.write('\n'.join([
                'def foo():',
                '  def bar():',
                '    pass',
                '']))
        self.assertEqual(self.p.parse(self.src), [
            Symbol(self.src, 1, 0, None, None, 'foo', SymbolType.FUNCTION),
            Symbol(self.src, 2, 2, None, None, 'bar', SymbolType.FUNCTION)])

    def test_class(self) -> None:
        with open(self.src.abs, 'w') as f:
            f.write('class Foo(object):\n  pass\n')
        self.assertEqual(self.p.parse(self.src), [
            Symbol(self.src, 1, 0, None, None, 'Foo', SymbolType.CLASS)])

    def test_method(self) -> None:
        with open(self.src.abs, 'w') as f:
            f.write('\n'.join([
                'class Foo(object):',
                '  def foo():',
                '    pass',
                '']))
        self.assertEqual(self.p.parse(self.src), [
            Symbol(self.src, 1, 0, None, None, 'Foo', SymbolType.CLASS),
            Symbol(self.src, 2, 2, None, None, 'foo', SymbolType.FUNCTION)])

    def test_call_name(self) -> None:
        with open(self.src.abs, 'w') as f:
            f.write('foo("bar", 42)')
        self.assertEqual(self.p.parse(self.src), [
            Symbol(self.src, 1, 0, None, None, 'foo', SymbolType.CALL)])

    def test_call_attr(self) -> None:
        with open(self.src.abs, 'w') as f:
            f.write('foo.bar.baz(1, 2, 3)')
        self.assertEqual(self.p.parse(self.src), [
            Symbol(self.src, 1, 0, None, None, 'baz', SymbolType.CALL)])

    def test_call_dict_item(self) -> None:
        with open(self.src.abs, 'w') as f:
            f.write('dict["key"](42)')
        self.assertEqual(self.p.parse(self.src), [])
