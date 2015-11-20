#!/usr/bin/python
#

from gi.repository import Gdk, GObject, Gtk, GtkSource
import sys
from edit_pane import EditPane

class EditWindow(Gtk.Window):
    def __init__(self):
        super(EditWindow, self).__init__(title="Edit")
        
        self.edit_pane = EditPane()
        self.edit_pane.open_file(__file__)

        self.accelerators = Gtk.AccelGroup()
        self.add_accel_group(self.accelerators)
        self.menu_bar = Gtk.MenuBar()
        self._build_menus()

        self.vbox = Gtk.VBox()
        self.vbox.add(self.menu_bar)
        self.vbox.add(self.edit_pane)
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
        
        open_item = Gtk.MenuItem(label="Open")
        key, mod = Gtk.accelerator_parse("<Control>o")
        open_item.add_accelerator(
            "activate", self.accelerators, key, mod, Gtk.AccelFlags.VISIBLE)
        open_item.connect("activate", self.do_open)
        file_menu.add(open_item)
        
        quit = Gtk.MenuItem(label="Quit")
        key, mod = Gtk.accelerator_parse("<Control>q")
        quit.add_accelerator(
            "activate", self.accelerators, key, mod, Gtk.AccelFlags.VISIBLE)
        quit.connect("activate", Gtk.main_quit)
        file_menu.add(quit)
        
        self.menu_bar.add(file_menu_item)    

    def do_save(self, widget):
        print "save {}".format(__file__)
                
    def do_open(self, widget):
        dialog = Gtk.FileChooserDialog(
            "Open File", 
            self,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT))
        res = dialog.run()
        if res == Gtk.ResponseType.ACCEPT:
            self.edit_pane.open_file(dialog.get_filename())
        dialog.destroy()

if __name__ == '__main__':
    win = EditWindow()
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()

