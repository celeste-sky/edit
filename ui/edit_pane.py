#!/usr/bin/env python3
# Copyright 2015 Iain Peet
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import collections
from gi.repository import Gtk, GtkSource
import logging
import os.path

Tab = collections.namedtuple('Tab', ['src_view', 'buffer', 'path'])

class EditPane(Gtk.Notebook):
    def __init__(self, root_window, workspace, src_graph, *args, **kwargs):
        super(EditPane, self).__init__(*args, **kwargs)
        self.root_window = root_window
        self.workspace = workspace
        self.src_graph = src_graph
        self.language_manager = GtkSource.LanguageManager()
        self.tabs = []
        
        for path in self.workspace.open_files:
            self._open_file(path)
        if not self.workspace.open_files:
            self._open_file(None)
    
    def _to_display_path(self, abs_path):
        if not abs_path:
            return "Unnamed"
        elif abs_path.startswith(os.path.abspath(self.workspace.root_dir)):
            return os.path.relpath(abs_path, self.workspace.root_dir)
        else:
            return abs_path
            
    def open_file(self, path=None):
        self._open_file(path)
        self._update_open_files()
    
    def _update_open_files(self):
        self.workspace.open_files = [i.path for i in self.tabs if i.path]
             
    def _open_file(self, path):
        if path:
            path = os.path.abspath(path)
            try:
                with open(path) as f:
                    content = f.read()
            except IOError as e:
                content = ''
                logging.info("Couldn't open {}: {}".format(path, e))
            
        view = GtkSource.View(
            auto_indent=True, 
            insert_spaces_instead_of_tabs=True, 
            tab_width=4, 
            show_line_numbers=True)
        
        node = self.src_graph.find_file(path)
        if node:
            print('{} outgoing: '.format(path))
            for e in node.outgoing:
                print('  ' + e.dest.path)
            print('{} incoming: '.format(path))
            for e in node.incoming:
                print('  ' + e.source.path)
        
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
                tab = Tab(tab.src_view, tab.buffer, dialog.get_filename())
                self.tabs[self.get_current_page()] = tab
                self._update_open_files()
                dialog.destroy()
            else:
                dialog.destroy()
                return
   
        with open(tab.path, "w") as f:
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
        
if __name__ == '__main__':  
    win = Gtk.Window()
    pane = EditPane()
    pane.open_file("edit.py")
    pane.open_file("edit_pane.py")
    win.add(pane)
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()
   