#!/usr/bin/env python3
# Copyright 2017 Iain Peet
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import argparse
from graph.db import Sqlite
from graph.indexer import Indexer
from graph.parsers.python3 import Py3Parser
import logging
import os.path
import shutil
import sys
from typing import List
from workspace import Workspace
from workspace.path import Path

def do_create(args:argparse.Namespace) -> None:
    if os.path.exists(args.dir):
        if args.clobber:
            shutil.rmtree(args.dir)
        else:
            raise Exception("Index already exists")

    os.makedirs(args.dir)
    ws = Workspace(args.dir, must_exist=True)
    if args.root is not None:
        ws.root_dir = os.path.realpath(args.root)

    Sqlite(ws.symbol_index, create=True)
    print('Created index in working dir: {}'.format(ws.workspace_dir))

def do_update(args:argparse.Namespace)->None:
    ws = Workspace(args.dir, must_exist=True)
    path = Path(args.path, ws.root_dir)
    syms, imports = Py3Parser().parse(path)
    db = Sqlite(ws.symbol_index)
    try:
        db.update_file(path, syms, imports)
    finally:
        db.close()

def do_update_all(args:argparse.Namespace) -> None:
    ws = Workspace(args.dir, must_exist=True)
    db = Sqlite(ws.symbol_index)
    i = Indexer(ws, db, [Py3Parser()])
    i.update()

def do_dump(args:argparse.Namespace)->None:
    ws = Workspace(args.dir, must_exist=True)
    path = Path(args.path, ws.root_dir)
    db = Sqlite(ws.symbol_index)
    try:
        syms = db.dump_file(path)
        last_line = 0
        for s in syms:
            line = s.line if s.line != last_line else '|'
            last_line = s.line
            print('{line:>3}: {indent}{sym.sym_type.name} {sym.name}'.format(
                line=line, sym=s, indent=" "*s.column))
    finally:
        db.close()

def do_imports(args:argparse.Namespace)->None:
    ws = Workspace(args.dir, must_exist=True)
    path = Path(args.path, ws.root_dir)
    db = Sqlite(ws.symbol_index)
    try:
        imports = db.dump_imports(path)
        for name, path in sorted(imports.items()):
            print('{} -> {}'.format(name, path.abs if path else '???'))
    finally:
        db.close()

def main(argv:List[str]) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', '-d', type=str, required=True,
        help='Working dir for symbol index')
    parser.set_defaults(func=lambda _: parser.error('sub-command required'))
    subparsers = parser.add_subparsers()

    create = subparsers.add_parser('create')
    create.add_argument('--root', '-r', type=str, default=None,
        help='Root directory to index.  [default: parent(--dir)]')
    create.add_argument('--clobber', action='store_true', default=False,
        help='Replace an existing index')
    create.set_defaults(func=do_create)

    update = subparsers.add_parser('update')
    update.add_argument('path', type=str,
        help='Path to update in the index.  Abs, or relative to index root.')
    update.set_defaults(func=do_update)

    update_all = subparsers.add_parser('update-all')
    update_all.set_defaults(func=do_update_all)

    dump = subparsers.add_parser('dump',
        help="Dump all indexed symbols for a file")
    dump.add_argument('path', type=str)
    dump.set_defaults(func=do_dump)

    imports = subparsers.add_parser('imports',
        help='Dump all resolved imports for a file')
    imports.add_argument('path', type=str)
    imports.set_defaults(func=do_imports)

    args = parser.parse_args(argv)
    args.func(args)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main(sys.argv[1:])