#!/usr/bin/python

import collections
from gi.repository import Gtk, GtkSource
import os.path

Tab = collections.namedtuple('Tab', ['src_view', 'buffer', 'path'])

class EditPane(Gtk.Notebook):
    def __init__(self, *args, **kwargs):
        super(EditPane, self).__init__(*args, **kwargs)
        self.language_manager = GtkSource.LanguageManager()
        self.tabs = []
        
    def open_file(self, path):
        if os.path.abspath(path).startswith(os.path.abspath(os.curdir)):
            path = os.path.relpath(path)
        with open(path) as f:
            content = f.read()
            
        view = GtkSource.View(
            auto_indent=True, 
            insert_spaces_instead_of_tabs=True, 
            tab_width=4, 
            show_line_numbers=True)
        
        buf = GtkSource.Buffer()
        buf.set_text(content)
        buf.set_language(self.language_manager.get_language("python"))
        view.set_buffer(buf)
        
        scroll = Gtk.ScrolledWindow(
            min_content_height=800, min_content_width=600)
        scroll.add(view)
        
        self.tabs.append(Tab(view, buf, path))
        
        self.append_page(scroll, Gtk.Label(path))
        self.show_all()
        self.set_current_page(len(self.tabs) - 1)

    def save(self, widget):
        tab = self.tabs[self.get_current_page()]
        with open(tab.path, "w") as f:
            f.write(tab.buffer.get_text(
                tab.buffer.get_start_iter(),
                tab.buffer.get_end_iter(),
                False))
        
if __name__ == '__main__':  
    print "hello"
    win = Gtk.Window()
    pane = EditPane()
    pane.open_file("edit.py")
    pane.open_file("edit_pane.py")
    win.add(pane)
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()
    
