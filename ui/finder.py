#!/usr/bin/env python3
# Copyright 2015 Iain Peet
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from gi.repository import Gdk, Gtk, GObject

class Finder(Gtk.HBox):
    __gsignals__ = {
        'search-changed': (GObject.SignalFlags.ACTION, None, (str,)),
        'next': (GObject.SignalFlags.ACTION, None, (str,)),
        'prev': (GObject.SignalFlags.ACTION, None, (str,)),
        'dismiss': (GObject.SignalFlags.ACTION, None, tuple()),
    }
    
    def __init__(self)->None:
        super(Finder, self).__init__(spacing=5)
        
        self.entry = Gtk.Entry(placeholder_text="Find")
        self.entry.connect('changed', lambda _: 
            self.emit('search-changed', self.entry.get_text()))
        self.entry.connect('key-release-event', self.on_key_release)
        self.pack_start(self.entry, expand=True, fill=True, padding=0)
        
        self.next = Gtk.Button(label="Next")
        self.next.connect('clicked', lambda _:  self.emit('next', self.entry.get_text()))
        self.pack_start(self.next, expand=False, fill=False, padding=0)
        
        self.prev = Gtk.Button(label="Prev")
        self.prev.connect('clicked', lambda _: self.emit('prev', self.entry.get_text()))
        self.pack_start(self.prev, expand=False, fill=False, padding=0)
        
    def on_key_release(self, widget:Gtk.Widget, ev:Gdk.Event)->None:
        if ev.keyval == Gdk.KEY_Escape:
            self.emit('dismiss')
    
import unittest
from unittest.mock import MagicMock

class FinderTest(unittest.TestCase):
    def dispatch_events(self)->None:
        while Gtk.events_pending():
            Gtk.main_iteration_do(blocking=False)
    
    def test_create(self)->None:
        f = Finder()
        self.dispatch_events()
        
    def test_emits_on_change(self)->None:
        f = Finder()
        on_change = MagicMock()
        f.connect('search-changed', on_change)
        f.entry.set_text("foof")
        self.dispatch_events()
        on_change.assert_called_with(f, "foof")
        
    def test_click_next(self)->None:
        f = Finder()
        on_next = MagicMock()
        f.connect('next', on_next)
        f.entry.set_text("foof")
        f.next.clicked()
        self.dispatch_events()
        on_next.assert_called_with(f, "foof")
        
    def test_click_prev(self)->None:
        f = Finder()
        on_prev = MagicMock()
        f.connect('prev', on_prev)
        f.entry.set_text('foof')
        f.prev.clicked()
        self.dispatch_events()
        on_prev.assert_called_with(f, "foof")
        
import sys
        
def sandbox()->None:
    win = Gtk.Window()
    finder = Finder()
    finder.connect('search-changed', lambda w, f: print('search '+f))
    finder.connect('next', lambda w, f: print('next '+f))
    finder.connect('prev', lambda w, f: print('prev '+f))
    finder.connect('dismiss', Gtk.main_quit)
    
    win.add(finder)
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == '__main__':
    sandbox()
        