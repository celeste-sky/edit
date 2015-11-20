#!/usr/bin/python

from gi.repository import Gtk, GtkSource

class EditPane(Gtk.Notebook):
    def __init__(self, *args, **kwargs):
        super(EditPane, self).__init__(*args, **kwargs)
        self.language_manager = GtkSource.LanguageManager()
        self.src_views = []
        self.buffers = []
        
    def open_file(self, path):
        with open(path) as f:
            content = f.read()
            
        view = GtkSource.View(
            auto_indent=True, 
            insert_spaces_instead_of_tabs=True, 
            tab_width=4, 
            show_line_numbers=True)
        self.src_views.append(view)
        
        buf = GtkSource.Buffer()
        buf.set_text(content)
        buf.set_language(self.language_manager.get_language("python"))
        view.set_buffer(buf)
        self.buffers.append(buf)
        
        scroll = Gtk.ScrolledWindow(
            min_content_height=800, min_content_width=600)
        scroll.add(view)
        
        self.append_page(scroll, Gtk.Label(path))
        self.show_all()
        
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
    
