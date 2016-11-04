#!/usr/bin/env python3
# Copyright 2015 Iain Peet
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, GObject

import os.path

class QuickOpen(Gtk.VBox):
    __gsignals__ = {
        'file_selected': (GObject.SIGNAL_ACTION, None, (str,))
    }
    
    def __init__(self, workspace):
        super(QuickOpen, self).__init__()
        self.workspace = workspace
        self.entry = Gtk.Entry(placeholder_text='Quick Open')
        self.entry.connect('changed', self.on_entry_changed)
        self.entry.connect('activate', self.on_activate_entry)
        self.pack_start(self.entry, expand=False, fill=False, padding=0)
        
        self.tree_view = Gtk.TreeView(headers_visible=False)
        self.list_store = Gtk.ListStore(str)
        for f in self._prettify_files():
                self.list_store.append([f])
        self.filter = self.list_store.filter_new()
        self.filter.set_visible_func(self.file_filter)
        self.tree_view.set_model(self.filter)
        self.tree_view.append_column(Gtk.TreeViewColumn(
            'Filename', Gtk.CellRendererText(), text=0))
        self.tree_view.connect('row-activated', self.on_activate_row)
        self.pack_start(self.tree_view, expand=True, fill=True, padding=0)
    
    def _prettify_files(self):
        # Sorts, removes dirs, makes paths relative.
        res = []
        abs_root_dir = os.path.abspath(self.workspace.root_dir)
        for f in sorted(self.workspace.files):
            if not os.path.isdir(f):
                if f.startswith(abs_root_dir):
                    f = f[len(abs_root_dir)+1:]
                res.append(f)
        return res
        
    def file_filter(self, model, iterator, data):
        search = self.entry.get_text()
        if not search:
            return False
        if search == '*':
            return True
        return search in model[iterator][0]
        
    def on_entry_changed(self, widget):
        self.filter.refilter()
        
    def on_activate_entry(self, widget):
        self.emit('file_selected', self.entry.get_text())
        
    def on_activate_row(self, widget, iterator, column):
        self.emit('file_selected', self.filter[iterator][0])
        
import unittest.mock as mock

if __name__ == '__main__':
    win = Gtk.Window()
    ws = mock.MagicMock()
    ws.files = [
        'foo.py', 
        'bar.py', 
        'baz.py', 
        'dir/foobar.py', 
        'dir/inner/coffee.py', 
        'other/bat.py'
    ]
    quick_open = QuickOpen(ws)
    quick_open.connect('file_selected', lambda w, f: print('select '+f))
    win.add(quick_open)
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()
    