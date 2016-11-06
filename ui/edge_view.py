#!/usr/bin/env python3
# Copyright 2016 Iain Peet
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject

import graph.node as node
import os.path

class EdgeView(Gtk.VBox):        
    '''
    Displays a list of edges connecting to paricular vertex in the graph.
    '''
    
    OUTGOING = "outgoing"
    INCOMING = "incoming"
    
    __gsignals__ = {
        'location_selected': (GObject.SIGNAL_ACTION, None, (str,))
    }
    
    def __init__(self, edge_type):
        super(EdgeView, self).__init__()
        self.edge_type = edge_type
        self.cur_node = None
        
        self.label = Gtk.Label('Edges: '+edge_type)
        self.pack_start(self.label, expand=False, fill=False, padding=0)
        
        self.tree_view = Gtk.TreeView(headers_visible=False)
        self.list_store = Gtk.ListStore(str)
        self.tree_view.set_model(self.list_store)
        self.tree_view.append_column(Gtk.TreeViewColumn(
            'Reference', Gtk.CellRendererText(), text=0))
        self.tree_view.connect('row-activated', self.on_activate_row)
        self.pack_start(self.tree_view, expand=True, fill=True, padding=0)
        
    def set_current_node(self, node):
        self.list_store.clear()
        self.cur_node = node
        if not node:
            # There may not be a node for the current loc
            return
            
        paths = []
        for e in getattr(self.cur_node, self.edge_type):
            # XXX cheesy assumption edge is an import:
            if self.edge_type is self.OUTGOING:
                paths.append(e.dest.path)
            elif self.edge_type is self.INCOMING:
                paths.append(e.source.path)
        
        for p in sorted(paths):
            self.list_store.append([p.shortest])
        
    def on_activate_entry(self, widget):
        # XXX cheesy assumption text is a path:
        self.emit('location_selected', self.entry.get_text())
        
    def on_activate_row(self, widget, iterator, column):
        self.emit('location_selected', self.list_store[iterator][0])

def sandbox():        
    import unittest.mock as mock
    from workspace.path import Path

    win = Gtk.Window()
    n = mock.MagicMock()
    n.outgoing = []
    for p in ['foo', 'bar', 'baz']:
        e = mock.MagicMock()
        e.dest.path = Path(p, '.')
        n.outgoing.append(e)
        
    edge_view = EdgeView(EdgeView.OUTGOING)
    edge_view.connect('location_selected', lambda w, f: print('select '+f))
    edge_view.set_current_node(n)
    win.add(edge_view)
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()
    
if __name__ == '__main__':
    sandbox()
    