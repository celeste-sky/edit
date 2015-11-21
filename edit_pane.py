#!/usr/bin/python

import collections
from gi.repository import Gtk, GtkSource
import os.path

Tab = collections.namedtuple('Tab', ['src_view', 'buffer', 'path'])

class EditPane(Gtk.Notebook):
    def __init__(self, root_window, *args, **kwargs):
        super(EditPane, self).__init__(*args, **kwargs)
        self.root_window = root_window
        self.language_manager = GtkSource.LanguageManager()
        self.tabs = []
    
    def _to_display_path(self, abs_path):
        if not abs_path:
            return "Unnamed"
        elif abs_path.startswith(os.path.abspath(os.curdir)):
            return os.path.relpath(abs_path)
        else:
            return abs_path
         
    def open_file(self, path=None):
        if path:
            path = os.path.abspath(path)
            with open(path) as f:
                content = f.read()
            
        view = GtkSource.View(
            auto_indent=True, 
            insert_spaces_instead_of_tabs=True, 
            tab_width=4, 
            show_line_numbers=True)
        
        buf = GtkSource.Buffer()
        if path:
            buf.set_text(content)
        buf.set_language(self.language_manager.get_language("python"))
        view.set_buffer(buf)
        
        scroll = Gtk.ScrolledWindow(
            min_content_height=800, min_content_width=600)
        scroll.add(view)
        
        self.tabs.append(Tab(view, buf, path))
        
        display_path = self._to_display_path(path)
        self.append_page(scroll, Gtk.Label(display_path))
        self.show_all()
        self.set_current_page(len(self.tabs) - 1)
        
    def new_file_handler(self, widget):
        self.open_file()

    def save_handler(self, widget):
        tab = self.tabs[self.get_current_page()]
        
        if not tab.path:
            dialog = Gtk.FileChooserDialog(
                "Save File", 
                self.root_window,
                Gtk.FileChooserAction.SAVE,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT))
            res = dialog.run()
            if res == Gtk.ResponseType.ACCEPT:
                tab = Tab(tab.src_view, tab.buffer, dialog.get_filename())
                self.tabs[self.get_current_page()] = tab
                dialog.destroy()
            else:
                dialog.destroy()
                return
                
            self.set_tab_label_text(
                tab.src_view.get_parent(), self._to_display_path(tab.path))
            
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
    
