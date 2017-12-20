#!/usr/bin/env python3
# Copyright 2017 Iain Peet
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from graph.db import Sqlite
from graph.parsers.python3 import Py3Parser
import logging
from typing import List
from workspace import Workspace
from workspace.path import Path

log = logging.getLogger(__name__)

class Indexer(object):
    def __init__(self,
            ws:Workspace,
            # XXX: generalize:
            db:Sqlite,
            parsers:List[Py3Parser]
            ) -> None:
        self.ws = ws
        self.parsers = parsers
        self.db = db

    def update(self) -> None:
        for path in self.ws.files:
            if path.isdir:
                continue

            try:
                self._update_one(path)
            except Exception as e:
                log.warning('Indexing failed: {}: {}'.format(path.abs), e)

    def _update_one(self, path:Path) -> None:
        candidates = [p for p in self.parsers if p.accept(path)]
        if not candidates:
            log.info('No parser for file: {}'.format(path.abs))
            return
        elif len(candidates) > 1:
            log.info('Multiple parsers for file: {}'.format(path.abs))

        syms, imports = candidates[0].parse(path)
        self.db.update_file(path, syms)
        log.debug('Indexed: {}'.format(path.abs))
