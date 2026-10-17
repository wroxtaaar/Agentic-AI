import tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from tools.projects import structure, resolve_project_path

class ProjectTests(unittest.TestCase):
 def test_structure(self):
  with tempfile.TemporaryDirectory() as d:
   Path(d,'README.md').write_text('x')
   with patch('tools.projects.roots', return_value=[Path(d)]):
    self.assertEqual(structure(d)['file_count'],1)

 def test_default_path_resolves_only_when_one_repository_is_discovered(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   (root/'.git').mkdir()
   (root/'README.md').write_text('x')
   with patch('tools.projects.roots', return_value=[root.parent]):
    resolved, error = resolve_project_path('.')
   self.assertIsNone(error)
   self.assertEqual(resolved, root.resolve())

 def test_default_path_refuses_ambiguous_repositories(self):
  with tempfile.TemporaryDirectory() as d:
   parent=Path(d)
   for name in ('one','two'):
    (parent/name/'.git').mkdir(parents=True)
   with patch('tools.projects.roots', return_value=[parent]):
    resolved, error = resolve_project_path('.')
   self.assertIsNone(resolved)
   self.assertIn('Multiple projects', error)

if __name__=='__main__':unittest.main()
