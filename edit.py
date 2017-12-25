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

import argparse
from gi.repository import Gtk, Gdk
from graph.source_graph import SourceGraph
import logging
import os.path
import signal
import sys
from typing import List
from ui.main_window import MainWindow
from workspace.workspace import Workspace, initialize_workspace

def open_workspace(args:argparse.Namespace) -> Workspace:    
    if args.create:
        initialize_workspace(args.workspace)
    if not os.path.isdir(args.workspace):
        logging.warn(
        'Workspace doesn\'t exist: {}'.format(args.workspace))
    return Workspace(args.workspace)
    
def load_css(ws:Workspace) -> None:
    '''
    Check if an override stylesheet exists, and apply it if it does.
    '''
    css = ws.get_stylesheet()
    if not css:
        return
    style_provider = Gtk.CssProvider()
    style_provider.load_from_data(css)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), style_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

def main(argv:List[str]) -> None:
    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', '-w', type=str, default='.workspace',
        help='Workspace directory')
    parser.set_defaults(create=False)
    
    subparsers = parser.add_subparsers()
    create = subparsers.add_parser('create-workspace')
    create.set_defaults(create=True)
    
    args = parser.parse_args(argv)
    
    workspace = open_workspace(args)
    src_graph = SourceGraph(workspace)
 
    load_css(workspace)
    win = MainWindow(workspace, src_graph)
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == '__main__':
    main(sys.argv[1:])
