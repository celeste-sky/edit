#!/usr/bin/env python3
# Copyright 2015 Iain Peet
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import collections
from gi.repository import Gtk, GObject, GtkSource
import logging
import os.path
from ui.wrappers import UIPath
from workspace.path import Path

Tab = collections.namedtuple('Tab', ['src_view', 'buffer', 'path'])

class EditPane(Gtk.Notebook):
    __gsignals__ = {
        'switch-file': (GObject.SIGNAL_ACTION, None, (UIPath,))
    }
    
    def __init__(self, root_window, workspace, src_graph, *args, **kwargs):
        super(EditPane, self).__init__(*args, **kwargs)
        self.root_window = root_window
        self.workspace = workspace
        self.src_graph = src_graph
        self.language_manager = GtkSource.LanguageManager()
        self.tabs = []
        self.connect('switch-page', self.change_page_handler)
        
        for path in self.workspace.open_files:
            self._open_file(path)
        if not self.workspace.open_files:
            self._open_file(None)
    
    def _to_display_path(self, path):
        if not path:
            return "Unnamed"
        return path.abbreviate(16)
            
    def open_file(self, path=None):
        assert (path is None) or isinstance(path, Path)
        for i, t in enumerate(self.tabs):
            if path == t.path:
                self.set_current_page(i)
                return
        self._open_file(path)
        self._update_open_files()
        
    def get_current_path(self):
        return self.tabs[self.get_current_page()].path
    
    def _update_open_files(self):
        self.workspace.open_files = [i.path for i in self.tabs if i.path]
             
    def _open_file(self, path):
        if path:
            try:
                with open(path.abs) as f:
                    content = f.read()
            except IOError as e:
                content = ''
                logging.info("Couldn't open {}: {}".format(path, e))
            
        view = GtkSource.View(**self.workspace.editor_options)
        
        buf = GtkSource.Buffer()
        if path:
            buf.set_text(content)
        buf.set_language(self.language_manager.get_language("python"))
        buf.connect("changed", self.changed_handler)
        view.set_buffer(buf)
        
        scroll = Gtk.ScrolledWindow()
        scroll.add(view)
        
        self.tabs.append(Tab(view, buf, path))
        
        display_path = self._to_display_path(path)
        self.append_page(scroll, Gtk.Label(display_path))
        self.show_all()
        self.set_current_page(len(self.tabs) - 1)
        
    def new_file_handler(self, widget):
        self.open_file()
        
    def changed_handler(self, widget):
        tab = self.tabs[self.get_current_page()]
        self.set_tab_label_text(
            tab.src_view.get_parent(), "* "+self._to_display_path(tab.path))

    def save_handler(self, widget):
        tab = self.tabs[self.get_current_page()]
        
        if not tab.path:
            dialog = Gtk.FileChooserDialog(
                "Save File", 
                self.root_window,
                Gtk.FileChooserAction.SAVE,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT))
            dialog.set_current_folder(self.workspace.root_dir)
            res = dialog.run()
            if res == Gtk.ResponseType.ACCEPT:
                tab = Tab(tab.src_view, tab.buffer, 
                    Path(dialog.get_filename(), self.workspace.root_dir))
                self.tabs[self.get_current_page()] = tab
                self._update_open_files()
                dialog.destroy()
            else:
                dialog.destroy()
                return
   
        with open(tab.path.abs, "w") as f:
            f.write(tab.buffer.get_text(
                tab.buffer.get_start_iter(),
                tab.buffer.get_end_iter(),
                False))     
                           
        self.set_tab_label_text(
            tab.src_view.get_parent(), self._to_display_path(tab.path))
            
    def close_tab_handler(self, widget):
        if not self.tabs:
            return
        
        current = self.get_current_page()
        self.remove_page(current)
        del self.tabs[current]
        self._update_open_files()
        
    def change_page_handler(self, _widget, _page, index):
        if self.tabs[index].path is not None:
            self.emit('switch-file', UIPath(self.tabs[index].path))

def sandbox():
    import unittest.mock as mock
    ws = mock.MagicMock()
    ws.open_files = []
    ws.root_dir = '.'
    graph = mock.MagicMock()
    graph.find_file.return_value = None
    
    win = Gtk.Window()
    pane = EditPane(win, ws, graph)
    pane.connect('switch-file', lambda _w, p: print('select '+p))
    pane.open_file(Path("edit.py", "."))
    pane.open_file(Path("ui/edit_pane.py", "."))
    win.add(pane)
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == '__main__':  
    sandbox()
   