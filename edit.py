#!/usr/bin/python

from edit_pane import EditPane
from gi.repository import Gdk, GObject, Gtk, GtkSource
from graph.source_graph import SourceGraph
import logging
import os.path
import signal
import sys
from workspace.workspace import Workspace

class EditWindow(Gtk.Window):
    def __init__(self, workspace, src_graph):
        super(EditWindow, self).__init__(
            title="Edit", default_width=600, default_height=800)
        self.workspace = workspace
        self.src_graph = src_graph
        self.edit_pane = EditPane(self, self.workspace, self.src_graph)

        self.accelerators = Gtk.AccelGroup()
        self.add_accel_group(self.accelerators)
        self.menu_bar = Gtk.MenuBar()
        self._build_menus()

        self.vbox = Gtk.VBox()
        self.vbox.pack_start(self.menu_bar, False, False, 0)
        self.vbox.pack_start(self.edit_pane, True, True, 0)
        self.add(self.vbox)
        
    def _build_menus(self):
        file_menu_item = Gtk.MenuItem(label="File")
        file_menu = Gtk.Menu()
        file_menu_item.set_submenu(file_menu)
        
        save = Gtk.MenuItem(label="Save")
        key, mod = Gtk.accelerator_parse("<Control>s")        
        save.add_accelerator(
            "activate", self.accelerators, key, mod, Gtk.AccelFlags.VISIBLE)
        save.connect("activate", self.edit_pane.save_handler)
        file_menu.add(save)
        
        open_item = Gtk.MenuItem(label="Open")
        key, mod = Gtk.accelerator_parse("<Control>o")
        open_item.add_accelerator(
            "activate", self.accelerators, key, mod, Gtk.AccelFlags.VISIBLE)
        open_item.connect("activate", self.open_handler)
        file_menu.add(open_item)
        
        new = Gtk.MenuItem(label="New")
        key, mod = Gtk.accelerator_parse("<Control>n")
        new.add_accelerator(
            "activate", self.accelerators, key, mod, Gtk.AccelFlags.VISIBLE)
        new.connect("activate", self.edit_pane.new_file_handler)
        file_menu.add(new)
        
        close_tab = Gtk.MenuItem(label="Close Tab")
        key, mod = Gtk.accelerator_parse("<Control>w")
        close_tab.add_accelerator(
            "activate", self.accelerators, key, mod, Gtk.AccelFlags.VISIBLE)
        close_tab.connect("activate", self.edit_pane.close_tab_handler)
        file_menu.add(close_tab)
        
        quit = Gtk.MenuItem(label="Quit")
        key, mod = Gtk.accelerator_parse("<Control>q")
        quit.add_accelerator(
            "activate", self.accelerators, key, mod, Gtk.AccelFlags.VISIBLE)
        quit.connect("activate", Gtk.main_quit)
        file_menu.add(quit)
        
        self.menu_bar.add(file_menu_item)    
                
    def open_handler(self, widget):
        dialog = Gtk.FileChooserDialog(
            "Open File", 
            self,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT))
        dialog.set_current_folder(self.workspace.root_dir)
        res = dialog.run()
        if res == Gtk.ResponseType.ACCEPT:
            self.edit_pane.open_file(dialog.get_filename())
        dialog.destroy()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    ws_dir = '.workspace'
    if len(sys.argv) == 2:
        ws_dir = sys.argv[1]
    if not os.path.isdir(ws_dir):
        logging.warn(
        'Workspace doesn\'t exist: {}'.format(ws_dir))
    workspace = Workspace(ws_dir)
    src_graph = SourceGraph(workspace)
        
    win = EditWindow(workspace, src_graph)
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()

