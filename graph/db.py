#!/usr/bin/env python3
# Copyright 2017 Iain Peet
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from graph.symbol import Symbol, SymbolType
import os.path
import sqlite3
from typing import Any, Dict, List, NamedTuple, Optional, Tuple
from workspace.path import Path

class DBException(Exception):
    def __init__(self, msg: str) -> None:
        super(DBException, self).__init__(msg)
        
class DB(object):
    '''
    Defines the interface of a symbol database.
    '''
    def find_symbol_at(
            self, path: Path, line: int, col: int=None) -> Optional[Symbol]:
        '''
        Find a symbol at the current location in the file.  If there are
        multiple symbols on the line and col is provided, the last symbol to
        start before col is returned.  If col is not provided, the first symbol
        on the line is returned.
        '''
        raise NotImplementedError()
        
    def find_definitions(self,
            name:str, typ:SymbolType=None, path_root:str='/', max_num:int=100
            ) -> List[Symbol]:
        '''
        Find symbols that are definitions.
        @param typ search for a specific one of CLASS, FUNCTION, or VALUE
        @param path_root the cwd to use in returned symbol Path
        '''
        raise NotImplementedError()

    def find_references(self,
            name:str, typ:SymbolType=None, path_root:str='/', max_num:int=100
            ) -> List[Symbol]: 
        '''
        Find sybmols that are references.
        @param typ search for a specific one of REFERENCE or CALL
        @param path_root the cwd to use in the returned symbol Path
        '''
        raise NotImplementedError()

class Sqlite(DB):
    SCHEMA_VERSION = "2"

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
                    name text NOT NULL,
                    type integer NOT NULL,
                    FOREIGN KEY (file) REFERENCES files(id)
                )''')
            self.conn.execute('''
                CREATE TABLE imports (
                    file integer NOT NULL,
                    name text NOT NULL,
                    resolved_path text,
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

    def update_file(self, path: Path, symbols: List[Symbol],
            imports: List[Tuple[str, Path]]) -> None:
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
                self.conn.execute('DELETE FROM imports WHERE file=?', [file_id])
            assert file_id is not None

            self.conn.executemany(
                'INSERT INTO symbols VALUES (?,?,?,?,?)',
                [(file_id, s.line, s.column, s.name, s.sym_type.value) for s in symbols])
            self.conn.executemany(
                'INSERT INTO imports VALUES (?,?,?)',
                [(file_id, name, path.abs) for name, path in imports])

    def dump_file(self, path: Path) -> List[Symbol]:
        '''
        Fetch all symbols for the given file.
        XXX: limit + pagination?
        '''
        with self.conn:
            file_id = self._get_file_id(path)
            if file_id is None:
                raise DBException('File is not indexed: {}'.format(path.abs))
            c = self.conn.cursor()
            c.execute(
                '''
                    SELECT line, column, name, type
                    FROM symbols
                    WHERE file=?
                    ORDER BY line, column
                ''',
                (file_id,))
            res = c.fetchall()
        return [
            Symbol(path, r[0], r[1], r[2], SymbolType(r[3]))
            for r in res
        ]

    def dump_imports(self, path: Path) -> Dict[str, Optional[Path]]:
        '''
        Fetch all import resolutions for the given file.
        XXX: limit + pagination?
        @return A map from all imported names to their resolved paths (or None
          if resolution failed)
        '''
        with self.conn:
            file_id = self._get_file_id(path)
            if file_id is None:
                raise DBException('File is not indexed: {}'.format(path.abs))
            all_imp_c = self.conn.cursor()
            all_imp_c.execute(
                'SELECT name FROM symbols WHERE file=? AND type=?',
                (file_id, SymbolType.IMPORT.value))
            all_imports = set([i for (i,) in all_imp_c.fetchall()])

            all_res_c = self.conn.cursor()
            all_res_c.execute(
                'SELECT name, resolved_path FROM imports WHERE file=?',
                (file_id,))
            all_resolutions = all_res_c.fetchall()

        resolved_map = {n: Path(p, path.ws_root) for n, p in all_resolutions}
        return {n: resolved_map.get(n, None) for n in all_imports}

    def dump_stats(self) -> Dict:
        res: Dict = {}

        with self.conn:
            c = self.conn.cursor()
            c.execute('SELECT path FROM files')
            files = c.fetchall()
        res['files'] = set([i for (i,) in files])

        with self.conn:
            c = self.conn.cursor()
            c.execute(
                '''
                    SELECT path, count(*)
                    FROM symbols
                    INNER JOIN files ON symbols.file=files.id
                    GROUP BY path
                ''')
            syms_by_file = c.fetchall()
        res['symbols'] = {p: c for p, c in syms_by_file}
        res['symbols']['total'] = sum([i[1] for i in syms_by_file])

        with self.conn:
            c = self.conn.cursor()
            c.execute(
                '''
                    SELECT path, count(*)
                    FROM imports
                    INNER JOIN files ON imports.file=files.id
                    GROUP BY path
                ''')
            imps_by_file = c.fetchall()
        res['imports'] = {p: c for p, c in imps_by_file}
        res['imports']['total'] = sum([i[1] for i in imps_by_file])
        return res

    def find_symbol_at(
            self, path: Path, line: int, col: int=None) -> Optional[Symbol]:
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
            return Symbol(path, res[1], res[2], res[3], SymbolType(res[4]))

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
                    SELECT path, line, column, name, type
                    FROM symbols
                    INNER JOIN files ON symbols.file=files.id
                    WHERE name=? {}
                    LIMIT ?
                '''.format(filter),
                params)
            res = c.fetchall()
        if res is None:
            return []
        return [Symbol(Path(r[0], path_root), r[1], r[2], r[3],
            SymbolType(r[4])) for r in res]


    def find_definitions(self,
            name:str, typ:SymbolType=None, path_root:str='/', max_num:int=100
            ) -> List[Symbol]:
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
            [Symbol(p, 42, 12, 'foo', SymbolType.CLASS)],
            [('bar', Path('bar', self.temp_dir))])
        with self.db.conn:
            s = self.db.conn.execute('SELECT * FROM symbols').fetchall()
            self.assertEqual(s, [
                (1, 42, 12, 'foo', SymbolType.CLASS.value)])
            i = self.db.conn.execute('SELECT * FROM imports').fetchall()
            self.assertEqual(i, [
                (1, 'bar', os.path.join(self.temp_dir, 'bar'))])

    def test_double_update_file(self) -> None:
        self.create_db()
        p = Path('foo', self.temp_dir)
        self.db.update_file(p,
            [Symbol(p, 42, 12, 'foo', SymbolType.CLASS)],
            [('bar', Path('bar', self.temp_dir))])
        self.db.update_file(p,
            [Symbol(p, 42, 12, 'bar', SymbolType.FUNCTION)],
            [('bar', Path('bar', self.temp_dir))])
        with self.db.conn:
            s = self.db.conn.execute('SELECT * FROM symbols').fetchall()
            self.assertEqual(s, [
                (1, 42, 12, 'bar', SymbolType.FUNCTION.value)])
            i = self.db.conn.execute('SELECT * FROM imports').fetchall()
            self.assertEqual(i, [
                (1, 'bar', os.path.join(self.temp_dir, 'bar'))])

    def test_find_single_symbol(self) -> None:
        self.create_db()
        p = Path('foo', self.temp_dir)
        self.db.update_file(p,
            [Symbol(p, 42, 12, 'foo', SymbolType.CLASS)], [])
        self.assertEqual(self.db.find_symbol_at(p, 42),
            Symbol(p, 42, 12, 'foo', SymbolType.CLASS))

    def test_find_no_symbol(self) -> None:
        self.create_db()
        p = Path('foo', self.temp_dir)
        self.db.update_file(p,
            [Symbol(p, 42, 12, 'foo', SymbolType.CLASS)], [])
        self.assertIsNone(self.db.find_symbol_at(p, 43))

    def test_find_symbol_with_col(self) -> None:
        self.create_db()
        p = Path('foo', self.temp_dir)
        self.db.update_file(p,
            [
                Symbol(p, 42, 12, 'foo', SymbolType.CLASS),
                Symbol(p, 42, 20, 'bar', SymbolType.FUNCTION),
                Symbol(p, 42, 40, 'baz', SymbolType.REFERENCE)
            ],[])
        self.assertEqual(self.db.find_symbol_at(p, 42, 30),
            Symbol(p, 42, 20, 'bar', SymbolType.FUNCTION))

    def create_sybmols(self) -> None:
        p = Path('foo', self.temp_dir)
        self.db.update_file(p,
            [
                Symbol(p, 1, 0, 'Foo', SymbolType.CLASS),
                Symbol(p, 2, 4, '__init__', SymbolType.FUNCTION),
                Symbol(p, 3, 8, 'foo', SymbolType.VALUE),
                Symbol(p, 4, 8, 'bar', SymbolType.VALUE),
                Symbol(p, 6, 4,  'frobnosticate', SymbolType.FUNCTION),
                Symbol(p, 7, 8, 'clobber', SymbolType.CALL),
                Symbol(p, 7, 20, 'BOOP', SymbolType.REFERENCE),
                Symbol(p, 8, 0, 'bar', SymbolType.IMPORT)
            ],[])
        p = Path('bar', self.temp_dir)
        self.db.update_file(p,
            [
                Symbol(p, 1, 0, 'BOOP', SymbolType.VALUE),
                Symbol(p, 2, 0, 'bar', SymbolType.CLASS),
                Symbol(p, 3, 4, '__init__', SymbolType.FUNCTION),
                Symbol(p, 4, 8,  'bar', SymbolType.VALUE),
                Symbol(p, 6, 4, 'frobnosticate', SymbolType.FUNCTION),
                Symbol(p, 7, 8, 'bar', SymbolType.REFERENCE),
                Symbol(p, 9, 4, 'bar', SymbolType.FUNCTION),
                Symbol(p, 10, 8, 'bar', SymbolType.CALL)
            ], [])

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
            [Symbol(p, 1, 0, 'Foo', SymbolType.CLASS)])

    def test_find_multiple_defs(self) -> None:
        self.create_db()
        self.create_sybmols()
        p = Path('bar', self.temp_dir)
        self.assertEqual(
            set(self.db.find_definitions('bar', path_root=self.temp_dir)),
            set([
                Symbol(Path('foo', self.temp_dir), 4, 8, 'bar',
                    SymbolType.VALUE),
                Symbol(p, 2, 0, 'bar', SymbolType.CLASS),
                Symbol(p, 4, 8, 'bar', SymbolType.VALUE),
                Symbol(p, 9, 4, 'bar', SymbolType.FUNCTION)
            ]))

    def test_find_fn_def(self) -> None:
        self.create_db()
        self.create_sybmols()
        p = Path('bar', self.temp_dir)
        self.assertEqual(
            self.db.find_definitions(
                'bar', path_root=self.temp_dir, typ=SymbolType.CLASS),
            [Symbol(p, 2, 0, 'bar', SymbolType.CLASS)])

    def test_find_multiple_refs(self) -> None:
        self.create_db()
        self.create_sybmols()
        p = Path('bar', self.temp_dir)
        self.assertEqual(
            set(self.db.find_references('bar', path_root=self.temp_dir)),
            set([
                Symbol(p, 7, 8, 'bar', SymbolType.REFERENCE),
                Symbol(p, 10, 8, 'bar', SymbolType.CALL),
                Symbol(Path('foo', self.temp_dir),
                    8, 0,  'bar', SymbolType.IMPORT)
            ]))

    def test_find_call(self) -> None:
        self.create_db()
        self.create_sybmols()
        p = Path('bar', self.temp_dir)
        self.assertEqual(
            self.db.find_references(
                'bar', path_root=self.temp_dir, typ=SymbolType.CALL),
            [Symbol(p, 10, 8, 'bar', SymbolType.CALL)])

    def test_multi_syms_at_location(self) -> None:
        self.create_db()
        p = Path('foo', self.temp_dir)
        self.db.update_file(p,
            [
                Symbol(p, 1, 0, 'graph', SymbolType.IMPORT),
                Symbol(p, 1, 0, 'graph.db', SymbolType.IMPORT)
            ], [])
        # XXX: figure out what the UI really wants when there are multiple
        # symbols at the same location.
        self.assertEqual(self.db.find_symbol_at(p, 1, 0),
            Symbol(p, 1, 0, 'graph', SymbolType.IMPORT))

    def test_dump_no_such_file(self) -> None:
        self.create_db()
        p = Path('foo', self.temp_dir)
        with self.assertRaisesRegexp(DBException, "File is not indexed"):
            self.db.dump_file(p)

    def test_dump_empty_file(self) -> None:
        self.create_db()
        p = Path('foo', self.temp_dir)
        self.db.update_file(p, [], [])
        self.assertEqual(self.db.dump_file(p), [])

    def test_dump_file(self) -> None:
        self.create_db()
        p = Path('foo', self.temp_dir)
        self.db.update_file(p,
            [Symbol(p, 42, 12, 'foo', SymbolType.CLASS)],
            [])
        self.assertEqual(self.db.dump_file(p),
            [Symbol(p, 42, 12, 'foo', SymbolType.CLASS)])

    def test_dump_no_imports(self) -> None:
        self.create_db()
        p = Path('foo', self.temp_dir)
        self.db.update_file(p, [], [])
        self.assertEqual(self.db.dump_imports(p), {})

    def test_dump_imports(self) -> None:
        self.create_db()
        p = Path('foo', self.temp_dir)
        self.db.update_file(p, [
                Symbol(p, 1, 0, 'foo', SymbolType.IMPORT),
                Symbol(p, 2, 0, 'bar', SymbolType.IMPORT)
            ],
            [
                ('foo', p),
                ('baz', Path('baz', self.temp_dir))
            ])
        self.assertEqual(self.db.dump_imports(p), {'foo': p, 'bar': None })

    def test_dump_stats(self) -> None:
        self.create_db()
        p = Path('foo', self.temp_dir)
        self.db.update_file(p, [
                Symbol(p, 1, 0, 'foo', SymbolType.IMPORT),
                Symbol(p, 2, 0, 'bar', SymbolType.IMPORT)
            ],
            [
                ('foo', p),
                ('baz', Path('baz', self.temp_dir))
            ])
        self.assertEqual(self.db.dump_stats(),
            {
                'files': {p.abs},
                'symbols': {p.abs: 2, 'total': 2},
                'imports': {p.abs: 2, 'total': 2}
            })
