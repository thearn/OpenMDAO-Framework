import unittest
import tempfile
import os
import shutil

from openmdao.util.fileutil import find_files
from openmdao.main.component import Component
from openmdao.main.project import Project, project_from_archive, \
     _is_valid_project_dir, PROJ_FILE_EXT
from openmdao.lib.datatypes.api import Float

class Multiplier(Component):
    rval_in = Float(iotype='in')
    rval_out = Float(iotype='out')
    mult = Float(iotype='in')
    
    def __init__(self):
        super(Multiplier, self).__init__()
        self.rval_in = 4.
        self.rval_out = 6.
        self.mult = 1.5

    def execute(self):
        self.rval_out = self.rval_in * self.mult

class ProjectTestCase(unittest.TestCase):
    def setUp(self):
        self.tdir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.tdir)
        
    def _fill_project(self, top):
        comp1 = top.add('comp1', Multiplier())
        comp2 = top.add('comp2', Multiplier())
        
        top.driver.workflow.add(['comp1', 'comp2'])
        
        top.comp1.mult = 2.0
        top.comp2.mult = 4.0
        top.connect('comp1.rval_out', 'comp2.rval_in')
        top.comp1.rval_in = 5.0
        
    def test_new_project_is_valid(self):
        proj = Project(os.path.join(self.tdir, 'proj1'))
        self._fill_project(proj.top)
        
        self.assertEqual(proj.path, os.path.join(self.tdir, 'proj1'))
        self.assertTrue(_is_valid_project_dir(proj.path))

    def test_project_export_import(self):
        proj = Project(os.path.join(self.tdir, 'proj1'))
        self._fill_project(proj.top)
        
        proj.export(destdir=self.tdir)
        proj.deactivate()
        
        newproj = project_from_archive(os.path.join(self.tdir,
                                                    'proj1%s' % PROJ_FILE_EXT), 
                                       'proj2',
                                       self.tdir)

        self.assertEqual(newproj.path, os.path.join(self.tdir, 'proj2'))
        self.assertTrue(_is_valid_project_dir(proj.path))
    

if __name__ == "__main__":
    unittest.main()


