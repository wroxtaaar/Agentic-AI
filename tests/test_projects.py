import tempfile, unittest
from pathlib import Path
from tools.projects import structure
class ProjectTests(unittest.TestCase):
 def test_structure(self):
  with tempfile.TemporaryDirectory() as d:
   Path(d,'README.md').write_text('x'); self.assertEqual(structure(d)['file_count'],1)
if __name__=='__main__':unittest.main()
