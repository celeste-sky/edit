#!/usr/bin/env python3
# Copyright 2015 Iain Peet
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from gi.repository import Gdk, GObject, Gtk
from ui.edge_view import EdgeView
from ui.edit_pane import EditPane
from ui.quick_open import QuickOpen
from workspace.path import Path


class MainWindow(Gtk.Window):
    def __init__(self, workspace, src_graph):
        super(MainWindow, self).__init__(
            title="Edit", default_width=800, default_height=800)
        self.workspace = workspace
        self.src_graph = src_graph
        self.edit_pane = EditPane(self, self.workspace, self.src_graph)
        self.quick_open = QuickOpen(self.workspace)
        self.outgoing_edges = EdgeView(EdgeView.OUTGOING)
        self.incoming_edges = EdgeView(EdgeView.INCOMING)

        self.accelerators = Gtk.AccelGroup()
        self.add_accel_group(self.accelerators)
        self.menu_bar = Gtk.MenuBar()
        self._build_menus()
        self._build_layout()
        self._connect_widgets()

    def _build_layout(self):
        # right nav vbox
        self.left_nav = Gtk.VBox()
        self.left_nav.pack_start(
            self.quick_open, expand=True, fill=True, padding=0)
        self.left_nav.pack_start(
            self.outgoing_edges, expand=True, fill=True, padding=0)
        self.left_nav.pack_start(
            self.incoming_edges, expand=True, fill=True, padding=0)

        # hbox lays our edit pane with navigation panels on sides
        self.hbox = Gtk.HBox()
        self.hbox.pack_start(self.left_nav, False, False, 0)
        self.hbox.pack_start(self.edit_pane, True, True, 0)
        self.quick_open.register_accelerators(self.accelerators)

        # Top level vbox adds menubar
        self.vbox = Gtk.VBox()
        self.vbox.pack_start(self.menu_bar, False, False, 0)
        self.vbox.pack_start(self.hbox, True, True, 0)
        self.add(self.vbox)

    def _connect_widgets(self):
        self.quick_open.connect('path-selected',
            lambda _w, p: self.edit_pane.open_file(p.path))

        if self.edit_pane.get_current_path() is not None:
            self.outgoing_edges.set_current_node(
                self.src_graph.find_file(self.edit_pane.get_current_path()))
            self.incoming_edges.set_current_node(
                self.src_graph.find_file(self.edit_pane.get_current_path()))

        self.outgoing_edges.connect('location-selected',
            lambda _w, l: self.edit_pane.open_file(l.path))
        self.incoming_edges.connect('location_selected',
            lambda _w, l: self.edit_pane.open_file(l.path))
        self.edit_pane.connect('switch-file',
            lambda _w, p: self.outgoing_edges.set_current_node(
                self.src_graph.find_file(p.path)))
        self.edit_pane.connect('switch-file',
            lambda _w, p: self.incoming_edges.set_current_node(
                self.src_graph.find_file(p.path)))

    def _build_menus(self):
        self._build_file_menu()
        self._build_edit_menu()
        
    def _build_edit_menu(self):
        edit_menu_item = Gtk.MenuItem(label="Edit")
        edit_menu = Gtk.Menu()
        edit_menu_item.set_submenu(edit_menu)
        
        find = Gtk.MenuItem(label="Find")
        key, mod = Gtk.accelerator_parse("<Control>f")
        find.add_accelerator(
            "activate", self.accelerators, key, mod, Gtk.AccelFlags.VISIBLE)
        find.connect("activate", self.edit_pane.find_handler)
        edit_menu.add(find)
        
        self.menu_bar.add(edit_menu_item)
    
    def _build_file_menu(self):
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
            self.edit_pane.open_file(Path(
                dialog.get_filename(), self.workspace.root_dir))
        dialog.destroy()
