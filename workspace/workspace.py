#!/usr/bin/python

import json
import logging
import os.path

class Workspace(object):
    def __init__(self, workspace_dir):
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.files = set()
        self.file_listeners = []
        self.config = {}
        
        self._load_config()
        self.reload_file_list()
        
    def reload_file_list(self):
        logging.info("Loading workspace file list")
        root = self.root_dir
        new_files = set()
        
        def file_visitor(arg, dirname, names):
            for name in list(names):
                if name.startswith("."):
                    # skip hidden files.  don't walk down hidden dirs.
                    names.remove(name)
                    continue
                path = os.path.abspath(os.path.join(dirname, name))
                new_files.add(path)
                
        os.path.walk(root, file_visitor, None)
        removed = self.files.difference(new_files)
        added = new_files.difference(self.files)
        self.files = new_files
        for listener in self.file_listeners:
            listener(removed, added)
            
    def _load_config(self):
        try:
            with open(os.path.join(self.workspace_dir, 'config')) as f:
                self.config = json.loads(f.read())
        except IOError:
            # it's valid for no config to exist
            pass
            
    def _write_config(self):
        if not os.path.isdir(self.workspace_dir):
            # no workspace dir -> no saving
            return
        with open(os.path.join(self.workspace_dir, 'config'), 'w') as f:
            f.write(json.dumps(self.config, indent=4))
    
    @property
    def open_files(self):
        return self.config.get('open_files', [])
        
    @open_files.setter
    def open_files(self, files):
        self.config['open_files'] = files
        self._write_config()
        
    @property
    def root_dir(self):
        return self.config.get(
            'root_dir', os.path.dirname(self.workspace_dir))
            
    @property
    def python_path(self):
        return self.config.get('python_path', [])
            
import tempfile
import unittest
import mock
import shutil

class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.ws = os.path.join(self.temp_dir, '.workspace')
        self.alt_ws = None
        open(os.path.join(self.temp_dir, 'foo'), 'w').close()
        os.mkdir(os.path.join(self.temp_dir, 'dir1'))
        open(os.path.join(self.temp_dir, 'dir1', 'file1'), 'w').close()
        os.mkdir(os.path.join(self.temp_dir, 'dir2'))
        open(os.path.join(self.temp_dir, 'dir2', 'file1'), 'w').close()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        if self.alt_ws:
            shutil.rmtree(self.alt_ws)
        
    def assert_default_files(self, workspace):
        self.assertEqual(workspace.files, set([
            os.path.join(self.temp_dir, n) for n in [
                'foo', 'dir1', 'dir1/file1', 'dir2', 'dir2/file1'
            ]]))
        
    def test_init(self):
        w = Workspace(self.ws)
        self.assert_default_files(w)
        
    def test_init_remote_workspace(self):
        self.alt_ws = tempfile.mkdtemp()
        with open(os.path.join(self.alt_ws, 'config'), 'w') as f:
            f.write('{"root_dir": "'+self.temp_dir+'"}')
        w = Workspace(self.alt_ws)
        self.assert_default_files(w)
     
    def test_update(self):
        w = Workspace(self.ws)
        open(os.path.join(self.temp_dir, 'dir1', 'file2'), 'w').close()
        os.unlink(os.path.join(self.temp_dir, 'dir2', 'file1'))
        cb = mock.MagicMock()
        w.file_listeners.append(cb)
        w.reload_file_list()
        cb.assert_called_once_with(
            set([os.path.join(self.temp_dir, 'dir2', 'file1')]),
            set([os.path.join(self.temp_dir, 'dir1', 'file2')]))
            
    def test_hidden_file(self):
        open(os.path.join(self.temp_dir, '.hidden'), 'w').close()
        w = Workspace(self.ws)
        self.assert_default_files(w)
            
    def test_hidden_dirs(self):
        os.mkdir(os.path.join(self.temp_dir, '.hidden'))
        open(os.path.join(self.temp_dir, '.hidden', 'not_hidden'), 'w').close()
        w = Workspace(self.ws)
        self.assert_default_files(w)
        
    def test_update_doesnt_create_workspace(self):
        w = Workspace(self.ws)
        w.open_files = ['foo', 'bar']
        self.assertFalse(os.path.exists(self.ws))
        
    def test_update_open_files_written(self):
        os.mkdir(self.ws)
        w = Workspace(self.ws)
        w.open_files = ['foo', 'bar']        
        with open(os.path.join(self.ws, 'config')) as f:
            self.assertEqual(f.read(), 
               '{\n    "open_files": [\n        "foo", \n        "bar"\n    ]\n}')
               
    def test_open_files_read(self):
        os.mkdir(os.path.join(self.ws))
        with open(os.path.join(self.ws, 'config'), 'w') as f:
            f.write('{"open_files": ["foo", "bar"]}')
        w = Workspace(self.ws)
        self.assertEqual(w.open_files, ["foo", "bar"])
        
if __name__ == '__main__':
    unittest.main()