#!/usr/bin/env python3
# Copyright 2017 Iain Peet
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from enum import Enum
import os.path
import sqlite3
from typing import Any, List, NamedTuple, Optional, Tuple
from workspace.path import Path

class DBException(Exception):
    def __init__(self, msg: str) -> None:
        super(DBException, self).__init__(msg)

class SymbolType(Enum):
    CLASS = 1
    FUNCTION = 2
    VALUE = 3

    CALL = 100
    REFERENCE = 101
    IMPORT = 102

class Symbol(NamedTuple):
    path: Path
    line: int
    column: int
    end_line: Optional[int]
    end_column: Optional[int]
    name: str
    sym_type: SymbolType

class Sqlite(object):
    SCHEMA_VERSION = "0"

    def __init__(self, db_path: Path, create: bool=False) -> None:
        need_create = False
        if not os.path.exists(db_path.abs):
            if not create:
                raise DBException('DB does not exist: '.format(db_path.abs))
            need_create = True


        self.conn: sqlite3.Connection = sqlite3.connect(db_path.abs)
        try:
            if need_create:
                self._create_db()
            else:
                self._check_version()
        except:
            self.conn.close()
            raise

    def _create_db(self) -> None:
        with self.conn:
            self.conn.execute('''
                CREATE TABLE meta
                (key text PRIMARY KEY, value text NOT NULL)''')
            self.conn.execute('''
                CREATE TABLE files (
                    id integer PRIMARY KEY,
                    path text UNIQUE NOT NULL,
                    hash text)''')
            # XXX: type should be a foreign key into an enum table.
            self.conn.execute('''
                CREATE TABLE symbols (
                    file integer NOT NULL,
                    line integer NOT NULL,
                    column integer NOT NULL,
                    end_line integer,
                    end_col integer,
                    name text NOT NULL,
                    type integer NOT NULL,
                    FOREIGN KEY (file) REFERENCES files(id)
                )''')
            self.conn.execute('CREATE INDEX sym_by_file ON symbols(file)')
            self.conn.execute('CREATE INDEX sym_by_name ON symbols(name)')
            self.conn.execute('INSERT INTO meta VALUES ("version", ?)',
                Sqlite.SCHEMA_VERSION)

    def _check_version(self) -> None:
        vers = self.get_schema_version()
        if vers != Sqlite.SCHEMA_VERSION:
            raise DBException('Schema version mismatch: want {}, is {}'.format(
                Sqlite.SCHEMA_VERSION, vers))

    def get_schema_version(self) -> str:
        with self.conn:
            ((vers,),) = self.conn.execute(
                'SELECT (value) FROM meta WHERE key="version"')
            return vers

    def _get_file_id(self, path: Path) -> Optional[int]:
        '''
        Look up the file id for the given path.
        This is intended to be run within a larger transaction.
        '''
        res = self.conn.execute(
            'SELECT id FROM files WHERE path = ?', [path.abs]).fetchone()
        if res is None:
            return None
        else:
            (fid,) = res
            return fid

    def update_file(self, path: Path, symbols: List[Symbol]) -> None:
        '''
        Update db with new symbols for the given file.
        '''
        assert all([s.path == path for s in symbols])
        with self.conn:
            # Check if this path is known:
            file_id = self._get_file_id(path)
            if file_id is None:
                # It isn't, add it to the files table to get a file id
                self.conn.execute('INSERT INTO files (path) VALUES (?)',
                    [path.abs])
                file_id = self._get_file_id(path)
            else:
                # The file is known, delete all old symbols for it:
                self.conn.execute('DELETE FROM symbols WHERE file=?', [file_id])
            assert file_id is not None

            self.conn.executemany(
                'INSERT INTO symbols VALUES (?,?,?,?,?,?,?)',
                [(file_id, s.line, s.column, s.end_line, s.end_column,
                    s.name, s.sym_type.value) for s in symbols])

    def dump_file(self, path: Path) -> List[Symbol]:
        '''
        Fetch all symbols for the given file.
        XXX: limit + pagination?
        '''
        with self.conn:
            file_id = self._get_file_id(path)
            if file_id is None:
                raise DBException('File is not indexed: {}'.format(path))
            c = self.conn.cursor()
            c.execute(
                '''
                    SELECT line, column, end_line, end_col, name, type
                    FROM symbols
                    WHERE file=?
                    ORDER BY line
                ''',
                (file_id,))
            res = c.fetchall()
        return [
            Symbol(path, r[0], r[1], r[2], r[3], r[4], SymbolType(r[5]))
            for r in res
        ]

    def find_symbol_at(
            self, path: Path, line: int, col: int=None) -> Optional[Symbol]:
        '''
        Find a symbol at the current location in the file.  If there are
        multiple symbols on the line and col is provided, the last symbol to
        start before col is returned.  If col is not provided, the first symbol
        on the line is returned.
        '''
        with self.conn:
            file_id = self._get_file_id(path)
            if file_id is None:
                return None
            c = self.conn.cursor()
            c.execute('''SELECT * FROM symbols
                WHERE file=? AND line=? ORDER BY column''', (file_id, line))

            res = c.fetchone()
            while (col is not None) and (res is not None) and (res[2] < col):
                next = c.fetchone()
                if next is None or next[2] > col:
                    break
                res = next

        if res is None:
            return None
        else:
            return Symbol(path, res[1], res[2], res[3], res[4], res[5],
                SymbolType(res[6]))

    def _do_search(self, filter:str, params:Tuple, path_root:str
            ) -> List[Symbol]:
        '''
        Symbol search.  Filter is a query fragment for the WHERE clause.
        param[0] is the symbol name, param[-1] is the fetch limit.
        '''
        with self.conn:
            c = self.conn.cursor()
            c.execute(
                '''
                    SELECT path, line, column, end_line, end_col, name, type
                    FROM symbols
                    INNER JOIN files ON symbols.file=files.id
                    WHERE name=? {}
                    LIMIT ?
                '''.format(filter),
                params)
            res = c.fetchall()
        if res is None:
            return []
        return [Symbol(Path(r[0], path_root), r[1], r[2], r[3], r[4], r[5],
            SymbolType(r[6])) for r in res]


    def find_definitions(self,
            name:str, typ:SymbolType=None, path_root:str='/', max_num:int=100
            ) -> List[Symbol]:
        '''
        Find symbols that are definitions.
        @param typ search for a specific one of CLASS, FUNCTION, or VALUE
        @param path_root the cwd to use in returned symbol Path
        '''
        if typ is None:
            return self._do_search(
                'AND type>=? AND type<=?',
                (name, SymbolType.CLASS.value, SymbolType.VALUE.value, max_num),
                path_root)
        else:
            return self._do_search(
                'AND type=?', (name, typ.value, max_num), path_root)

    def find_references(self,
            name:str, typ:SymbolType=None, path_root:str='/', max_num:int=100
            ) -> List[Symbol]:
        '''
        Find sybmols that are references.
        @param typ search for a specific one of REFERENCE or CALL
        @param path_root the cwd to use in the returned symbol Path
        '''
        if typ is None:
            return self._do_search(
                'AND type>=? AND type<=?',
                (name, SymbolType.CALL.value, SymbolType.IMPORT.value,
                    max_num),
                path_root)
        else:
            return self._do_search(
                'AND type=?', (name, typ.value, max_num), path_root)

    def close(self) -> None:
        if self.conn:
            self.conn.close()

import shutil
import tempfile
import unittest

class SqliteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.maxDiff = 2000
        self.temp_dir = tempfile.mkdtemp()
        self.db: Sqlite = None

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)
        if self.db:
            self.db.close()

    def create_db(self) -> None:
        self.db = Sqlite(Path('test.db', self.temp_dir), create=True)

    def test_no_create_no_exist(self) -> None:
        with self.assertRaisesRegexp(DBException, "DB does not exist"):
            Sqlite(Path('test.db', self.temp_dir), create=False)

    def test_create_no_exist(self) -> None:
        self.db = Sqlite(Path('test.db', self.temp_dir), create=True)
        self.assertEqual(self.db.get_schema_version(), Sqlite.SCHEMA_VERSION)

    def test_open_version_mismatch(self) -> None:
        path = Path('test.db', self.temp_dir)
        conn = sqlite3.connect(path.abs)
        with conn:
            conn.execute('''CREATE TABLE meta
                (key text primary key, value text)''')
            conn.execute('INSERT INTO meta VALUES ("version", "foof")')
        conn.close()

        with self.assertRaisesRegexp(DBException, "Schema version mismatch"):
            Sqlite(path)

    def test_update_file(self) -> None:
        self.create_db()
        p = Path('foo', self.temp_dir)
        self.db.update_file(p,
            [Symbol(p, 42, 12, None, None, 'foo', SymbolType.CLASS)])
        with self.db.conn:
            s = self.db.conn.execute('SELECT * FROM symbols').fetchall()
            self.assertEqual(s, [
                (1, 42, 12, None, None, 'foo', SymbolType.CLASS.value)])

    def test_double_update_file(self) -> None:
        self.create_db()
        p = Path('foo', self.temp_dir)
        self.db.update_file(p,
            [Symbol(p, 42, 12, None, None, 'foo', SymbolType.CLASS)])
        self.db.update_file(p,
            [Symbol(p, 42, 12, None, None, 'bar', SymbolType.FUNCTION)])
        with self.db.conn:
            s = self.db.conn.execute('SELECT * FROM symbols').fetchall()
            self.assertEqual(s, [
                (1, 42, 12, None, None, 'bar', SymbolType.FUNCTION.value)])

    def test_find_single_symbol(self) -> None:
        self.create_db()
        p = Path('foo', self.temp_dir)
        self.db.update_file(p,
            [Symbol(p, 42, 12, None, None, 'foo', SymbolType.CLASS)])
        self.assertEqual(self.db.find_symbol_at(p, 42),
            Symbol(p, 42, 12, None, None, 'foo', SymbolType.CLASS))

    def test_find_no_symbol(self) -> None:
        self.create_db()
        p = Path('foo', self.temp_dir)
        self.db.update_file(p,
            [Symbol(p, 42, 12, None, None, 'foo', SymbolType.CLASS)])
        self.assertIsNone(self.db.find_symbol_at(p, 43))

    def test_find_symbol_with_col(self) -> None:
        self.create_db()
        p = Path('foo', self.temp_dir)
        self.db.update_file(p, [
            Symbol(p, 42, 12, None, None, 'foo', SymbolType.CLASS),
            Symbol(p, 42, 20, None, None, 'bar', SymbolType.FUNCTION),
            Symbol(p, 42, 40, None, None, 'baz', SymbolType.REFERENCE)])
        self.assertEqual(self.db.find_symbol_at(p, 42, 30),
            Symbol(p, 42, 20, None, None, 'bar', SymbolType.FUNCTION))

    def create_sybmols(self) -> None:
        p = Path('foo', self.temp_dir)
        self.db.update_file(p, [
            Symbol(p, 1, 0, 100, 40, 'Foo', SymbolType.CLASS),
            Symbol(p, 2, 4, 4, 10, '__init__', SymbolType.FUNCTION),
            Symbol(p, 3, 8, 3, 20, 'foo', SymbolType.VALUE),
            Symbol(p, 4, 8, 4, 20, 'bar', SymbolType.VALUE),
            Symbol(p, 6, 4, 8, 20, 'frobnosticate', SymbolType.FUNCTION),
            Symbol(p, 7, 8, 7, 30, 'clobber', SymbolType.CALL),
            Symbol(p, 7, 20, 7, 24, 'BOOP', SymbolType.REFERENCE),
            Symbol(p, 8, 0, 8, 10, 'bar', SymbolType.IMPORT)])
        p = Path('bar', self.temp_dir)
        self.db.update_file(p, [
            Symbol(p, 1, 0, 1, 4, 'BOOP', SymbolType.VALUE),
            Symbol(p, 2, 0, 40, 50, 'bar', SymbolType.CLASS),
            Symbol(p, 3, 4, 4, 40, '__init__', SymbolType.FUNCTION),
            Symbol(p, 4, 8, 4, 20, 'bar', SymbolType.VALUE),
            Symbol(p, 6, 4, 10, 30, 'frobnosticate', SymbolType.FUNCTION),
            Symbol(p, 7, 8, 7, 20, 'bar', SymbolType.REFERENCE),
            Symbol(p, 9, 4, 10, 20, 'bar', SymbolType.FUNCTION),
            Symbol(p, 10, 8, 10, 20, 'bar', SymbolType.CALL)])

    def test_find_no_def(self) -> None:
        self.create_db()
        self.create_sybmols()
        self.assertEqual(self.db.find_definitions('bad'), [])

    def test_find_single_class_def(self) -> None:
        self.create_db()
        self.create_sybmols()
        p = Path('foo', self.temp_dir)
        self.assertEqual(
            self.db.find_definitions('Foo', path_root=self.temp_dir),
            [Symbol(p, 1, 0, 100, 40, 'Foo', SymbolType.CLASS)])

    def test_find_multiple_defs(self) -> None:
        self.create_db()
        self.create_sybmols()
        p = Path('bar', self.temp_dir)
        self.assertEqual(
            set(self.db.find_definitions('bar', path_root=self.temp_dir)),
            set([
                Symbol(Path('foo', self.temp_dir), 4, 8, 4, 20, 'bar',
                    SymbolType.VALUE),
                Symbol(p, 2, 0, 40, 50, 'bar', SymbolType.CLASS),
                Symbol(p, 4, 8, 4, 20, 'bar', SymbolType.VALUE),
                Symbol(p, 9, 4, 10, 20, 'bar', SymbolType.FUNCTION)
            ]))

    def test_find_fn_def(self) -> None:
        self.create_db()
        self.create_sybmols()
        p = Path('bar', self.temp_dir)
        self.assertEqual(
            self.db.find_definitions(
                'bar', path_root=self.temp_dir, typ=SymbolType.CLASS),
            [Symbol(p, 2, 0, 40, 50, 'bar', SymbolType.CLASS)])

    def test_find_multiple_refs(self) -> None:
        self.create_db()
        self.create_sybmols()
        p = Path('bar', self.temp_dir)
        self.assertEqual(
            set(self.db.find_references('bar', path_root=self.temp_dir)),
            set([
                Symbol(p, 7, 8, 7, 20, 'bar', SymbolType.REFERENCE),
                Symbol(p, 10, 8, 10, 20, 'bar', SymbolType.CALL),
                Symbol(Path('foo', self.temp_dir),
                    8, 0, 8, 10, 'bar', SymbolType.IMPORT)
            ]))

    def test_find_call(self) -> None:
        self.create_db()
        self.create_sybmols()
        p = Path('bar', self.temp_dir)
        self.assertEqual(
            self.db.find_references(
                'bar', path_root=self.temp_dir, typ=SymbolType.CALL),
            [Symbol(p, 10, 8, 10, 20, 'bar', SymbolType.CALL)])

    def test_multi_syms_at_location(self) -> None:
        self.create_db()
        p = Path('foo', self.temp_dir)
        self.db.update_file(p, [
            Symbol(p, 1, 0, None, None, 'graph', SymbolType.IMPORT),
            Symbol(p, 1, 0, None, None, 'graph.db', SymbolType.IMPORT)])
        # XXX: figure out what the UI really wants when there are multiple
        # symbols at the same location.
        self.assertEqual(self.db.find_symbol_at(p, 1, 0),
            Symbol(p, 1, 0, None, None, 'graph', SymbolType.IMPORT))

    def test_dump_no_such_file(self) -> None:
        self.create_db()
        p = Path('foo', self.temp_dir)
        with self.assertRaisesRegexp(DBException, "File is not indexed"):
            self.db.dump_file(p)

    def test_dump_empty_file(self) -> None:
        self.create_db()
        p = Path('foo', self.temp_dir)
        self.db.update_file(p, [])
        self.assertEqual(self.db.dump_file(p), [])

    def test_dump_file(self) -> None:
        self.create_db()
        p = Path('foo', self.temp_dir)
        self.db.update_file(p,
            [Symbol(p, 42, 12, None, None, 'foo', SymbolType.CLASS)])
        self.assertEqual(self.db.dump_file(p),
            [Symbol(p, 42, 12, None, None, 'foo', SymbolType.CLASS)])