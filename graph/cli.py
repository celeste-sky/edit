#!/usr/bin/env python3
# Copyright 2017 Iain Peet
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import argparse
from graph.db import Sqlite
from graph.parsers.python3 import Py3Parser
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
    syms = Py3Parser().parse(path)
    db = Sqlite(ws.symbol_index)
    try:
        db.update_file(path, syms)
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
    update.add_argument('--path', '-p', type=str, required=True,
        help='Path to update in the index.  Abs, or relative to index root.')
    update.set_defaults(func=do_update)

    args = parser.parse_args(argv)
    args.func(args)

if __name__ == '__main__':
    main(sys.argv[1:])