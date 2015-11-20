#!/usr/bin/python
#

from gi.repository import Gdk, GObject, Gtk, GtkSource
import sys

class EditWindow(Gtk.Window):
    def __init__(self):
        super(EditWindow, self).__init__(title="Edit")
        self.text = GtkSource.View(
            auto_indent=True, 
            insert_spaces_instead_of_tabs=True, 
            tab_width=4, 
            show_line_numbers=True)
        self.language_manager = GtkSource.LanguageManager()
        self.buf = GtkSource.Buffer()

        with open(__file__) as f:
            self.buf = GtkSource.Buffer()
            self.buf.set_text(f.read())
            self.buf.set_language(self.language_manager.get_language("python"))
            self.text.set_buffer(self.buf)

        self.scroll = Gtk.ScrolledWindow(
            min_content_height=800, min_content_width=800)
        self.scroll.add(self.text)

        self.accelerators = Gtk.AccelGroup()
        self.add_accel_group(self.accelerators)
        
        self.menu_bar = Gtk.MenuBar()
        self._build_menus()

        self.vbox = Gtk.VBox()
        self.vbox.add(self.menu_bar)
        self.vbox.add(self.scroll)
        self.add(self.vbox)
        
    def _build_menus(self):
        file_menu_item = Gtk.MenuItem(label="File")
        file_menu = Gtk.Menu()
        file_menu_item.set_submenu(file_menu)
        
        save = Gtk.MenuItem(label="Save")
        key, mod = Gtk.accelerator_parse("<Control>s")        
        save.add_accelerator(
            "activate", self.accelerators, key, mod, Gtk.AccelFlags.VISIBLE)
        save.connect("activate", self.do_save)
        file_menu.add(save)
        
        quit = Gtk.MenuItem(label="Quit")
        key, mod = Gtk.accelerator_parse("<Control>q")
        quit.add_accelerator(
            "activate", self.accelerators, key, mod, Gtk.AccelFlags.VISIBLE)
        quit.connect("activate", Gtk.main_quit)
        file_menu.add(quit)
        
        self.menu_bar.add(file_menu_item)    

    def do_save(self, widget):
        print "save {}".format(__file__)
        with open(__file__, "w") as f:
            f.write(self.buf.get_text(
                self.buf.get_start_iter(), self.buf.get_end_iter(), True))

if __name__ == '__main__':
    win = EditWindow()
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()

