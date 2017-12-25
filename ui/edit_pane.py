#!/usr/bin/env python3
# Copyright 2015 Iain Peet
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import collections
from graph.source_graph import SourceGraph
from gi.repository import Gtk, GObject, GtkSource
import logging
import os.path
from typing import Any, Dict, List, Tuple
from ui.wrappers import UIPath
from workspace.path import Path
from workspace.workspace import Workspace

log = logging.getLogger(__name__)

class Tab(object):
    def __init__(self,
            src_view:GtkSource.View, 
            buffer:GtkSource.Buffer,
            path:Path, 
            search_ctx:GtkSource.SearchContext=None,
            search_pos:Tuple[int, int]=None) -> None:
        self.src_view = src_view
        self.buffer = buffer
        self.path = path
        self.search_ctx = search_ctx
        self.search_pos = search_pos

class EditPane(Gtk.Notebook):
    __gsignals__ = {
        'switch-file': (GObject.SignalFlags.ACTION, None, (UIPath,))
    }

    def __init__(self, 
            root_window:Gtk.Window, 
            workspace:Workspace, 
            src_graph:SourceGraph, 
            *args:List, 
            **kwargs:Dict) -> None:
        super(EditPane, self).__init__(*args, **kwargs)
        self.root_window = root_window
        self.workspace = workspace
        self.src_graph = src_graph
        self.language_manager = GtkSource.LanguageManager()
        self.tabs:List[Tab] = []
        self.connect('switch-page', self.change_page_handler)

        style_manager = GtkSource.StyleSchemeManager.get_default()
        self.style_scheme = style_manager.get_scheme(
            workspace.editor_options.get('style', 'classic'))

        for path in self.workspace.open_files:
            self._open_file(path)
        if not self.workspace.open_files:
            self._open_file(None)

    def _to_display_path(self, path:Path)->str:
        if not path:
            return "Unnamed"
        return path.abbreviate(16)

    def open_file(self, path:Path=None)->None:
        assert (path is None) or isinstance(path, Path)
        for i, t in enumerate(self.tabs):
            if path == t.path:
                self.set_current_page(i)
                return
        self._open_file(path)
        self._update_open_files()

    @property
    def current_tab(self) -> Tab:
        return self.tabs[self.get_current_page()]
        
    def get_current_path(self)->Path:
        return self.current_tab.path

    def _update_open_files(self)->None:
        self.workspace.open_files = [i.path for i in self.tabs if i.path]

    def _open_file(self, path:Path)->None:
        if path:
            try:
                with open(path.abs) as f:
                    content = f.read()
            except IOError as e:
                content = ''
                log.info("Couldn't open {}: {}".format(path, e))
                
        # XXX make this less of a hack
        view_opts = self.workspace.editor_options
        view_opts.pop('style', None)
        view = GtkSource.View(**view_opts)

        buf = GtkSource.Buffer()
        if path:
            buf.set_text(content)
        buf.set_language(self.language_manager.get_language("python"))
        buf.set_style_scheme(self.style_scheme)
        buf.connect("changed", self.changed_handler)
        view.set_buffer(buf)

        scroll = Gtk.ScrolledWindow()
        scroll.add(view)

        self.tabs.append(Tab(view, buf, path))

        display_path = self._to_display_path(path)
        self.append_page(scroll, Gtk.Label(label=display_path))
        self.show_all()
        self.set_current_page(len(self.tabs) - 1)

    def new_file_handler(self, widget:Gtk.Widget)->None:
        self.open_file()

    def changed_handler(self, widget:Gtk.Widget)->None:
        self.set_tab_label_text(
            self.current_tab.src_view.get_parent(),
            "* "+self._to_display_path(self.current_tab.path))

    def save_handler(self, widget:Gtk.Widget)->None:
        tab = self.tabs[self.get_current_page()]

        if not tab.path:
            # XXX: deprecated use of positional args:
            dialog = Gtk.FileChooserDialog(
                "Save File",
                self.root_window,
                Gtk.FileChooserAction.SAVE,
                # XXX: deprecated button list:
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT))
            dialog.set_current_folder(self.workspace.root_dir)
            res = dialog.run()
            if res == Gtk.ResponseType.ACCEPT:
                tab.path = Path(dialog.get_filename(), self.workspace.root_dir)
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

    def close_tab_handler(self, widget:Gtk.Widget)->None:
        if not self.tabs:
            return

        current = self.get_current_page()
        self.remove_page(current)
        del self.tabs[current]
        self._update_open_files()

    def change_page_handler(
            self, _widget:Gtk.Widget, _page:Any, index:int)->None:
        if self.tabs[index].path is not None:
            self.emit('switch-file', UIPath(self.tabs[index].path))
            
    def find_handler(self, pattern:str, move:int=0)->None:
        '''
        Update the current buffer to highlight the given pattern.
        If move is nonzero, move that many matches forward (neg for back)
        '''
        if self.current_tab.search_ctx:
            # Already have a  search context; update it / move
            ctx = self.current_tab.search_ctx
            settings = ctx.get_settings()
            if settings.get_search_text() != pattern:
                ctx.get_settings().set_search_text(pattern)
            if move == 0:
                return
            # If a a move was requested, search for the next match
            found = False
            # Get an iterator, clamping to end of file / end of line if the buffer
            # has been modified.
            search_iter = self.current_tab.buffer.get_iter_at_line(min(
                self.current_tab.search_pos[0], 
                self.current_tab.buffer.get_line_count() - 1))
            search_iter.forward_chars(min(
                self.current_tab.search_pos[1], search_iter.get_chars_in_line()-1))
            if move > 0:
                (found, start, end) = ctx.forward(search_iter)
            elif move < 0:
                # Reverse start/end, mostly so that the logic choosing "end" as 
                # search_pos below is straightforward
                (found, end, start) = ctx.backward(search_iter)
            # If a match was found, scroll to it and select it.
            if found:
                # Use the end of the match, so that we will move past on the next
                # search.
                self.current_tab.search_pos = (end.get_line(), end.get_line_offset())
                self.current_tab.src_view.scroll_to_iter(end,
                    within_margin=0.0, use_align=True, xalign=0.0, yalign=0.5)
                self.current_tab.buffer.select_range(start, end)
                # XXX: jump focus + hotkeys?
        else:
            # First search in this buffer; create a context.
            settings = GtkSource.SearchSettings(
                search_text=pattern, wrap_around=True)
            self.current_tab.search_ctx = GtkSource.SearchContext(
                buffer=self.current_tab.buffer, 
                settings=settings)
            self.current_tab.search_pos = (0, 0)

def sandbox()->None:
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
