#!/usr/bin/python

import json
import os.path

class Workspace(object):
    def __init__(self, workspace_dir='.workspace'):
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.files = set()
        self.file_listeners = []
        self.config = {}
        
        self.reload_file_list()
        self._load_config()
        
    def reload_file_list(self):
        root = os.path.dirname(self.workspace_dir)
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
        if not os.path.exists(self.workspace_dir):
            os.mkdir(self.workspace_dir)
        with open(os.path.join(self.workspace_dir, 'config'), 'w') as f:
            f.write(json.dumps(self.config, indent=4))
    
    @property
    def open_files(self):
        return self.config.get('open_files', [])
        
    @open_files.setter
    def open_files(self, files):
        self.config['open_files'] = files
        self._write_config()
            
import tempfile
import unittest
import mock
import shutil

class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.ws = os.path.join(self.temp_dir, '.workspace')
        open(os.path.join(self.temp_dir, 'foo'), 'w').close()
        os.mkdir(os.path.join(self.temp_dir, 'dir1'))
        open(os.path.join(self.temp_dir, 'dir1', 'file1'), 'w').close()
        os.mkdir(os.path.join(self.temp_dir, 'dir2'))
        open(os.path.join(self.temp_dir, 'dir2', 'file1'), 'w').close()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        
    def assert_default_files(self, workspace):
        self.assertEqual(workspace.files, set([
            os.path.join(self.temp_dir, n) for n in [
                'foo', 'dir1', 'dir1/file1', 'dir2', 'dir2/file1'
            ]]))
        
    def test_init(self):
        w = Workspace(self.ws)
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
        
    def test_write_open_files(self):
        w = Workspace(self.ws)
        w.open_files = ['foo', 'bar']
        with open(os.path.join(self.ws, 'config')) as f:
            self.assertEqual(f.read(), 
               '{\n    "open_files": [\n        "foo", \n        "bar"\n    ]\n}')
               
    def test_read_open_files(self):
        os.mkdir(os.path.join(self.ws))
        with open(os.path.join(self.ws, 'config'), 'w') as f:
            f.write('{"open_files": ["foo", "bar"]}')
        w = Workspace(self.ws)
        self.assertEqual(w.open_files, ["foo", "bar"])
        
if __name__ == '__main__':
    unittest.main()