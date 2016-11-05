#!/usr/bin/env python3
# Copyright 2015 Iain Peet
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkSource', '3.0')

from gi.repository import Gtk
from graph.source_graph import SourceGraph
import logging
import os.path
import signal
import sys
from ui.main_window import MainWindow
from workspace.workspace import Workspace

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    ws_dir = '.workspace'
    if len(sys.argv) == 2:
        ws_dir = sys.argv[1]
    if not os.path.isdir(ws_dir):
        logging.warn(
        'Workspace doesn\'t exist: {}'.format(ws_dir))
    workspace = Workspace(ws_dir)
    src_graph = SourceGraph(workspace)
        
    win = MainWindow(workspace, src_graph)
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()
