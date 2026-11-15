"""Upload-path regressions; run with calibre-debug -e this_file.py."""

import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from calibre.ebooks.metadata.book.base import Metadata
except ImportError:
    Metadata = None


@unittest.skipIf(Metadata is None, 'Requires the Calibre Python runtime (calibre-debug)')
class UploadPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Import the actual driver without running the plugin's GUI entry point.
        plugin = types.ModuleType('test_crosspoint_upload_paths')
        plugin.__path__ = [str(Path(__file__).resolve().parents[1] / 'crosspoint_reader')]
        sys.modules[plugin.__name__] = plugin
        cls.driver = importlib.import_module(plugin.__name__ + '.driver')

    def format_path(self, title, authors, template):
        mi = Metadata(title, authors)
        mi.id = 42
        mi.author_sort = ' & '.join(authors)
        errors = []
        device = types.SimpleNamespace(save_template=lambda: template, _log=errors.append)
        with patch.object(self.driver, 'PREFS', {'upload_template': template}):
            result = self.driver.CrossPointDevice._format_upload_path(device, mi, 'source.epub')
        self.assertEqual(errors, [])
        return result

    def test_chinese_author_folder_and_title(self):
        self.assertEqual(self.format_path('红楼梦', ['曹雪芹'], '{author_sort}/{title} - {authors}'),
                         (['曹雪芹'], '红楼梦 - 曹雪芹.epub'))

    def test_nested_unicode_folders(self):
        self.assertEqual(self.format_path('吾輩は猫である', ['夏目漱石'], '日本語/{authors}/{title}'),
                         (['日本語', '夏目漱石'], '吾輩は猫である.epub'))

    def test_flat_accented_title(self):
        self.assertEqual(self.format_path('Les Misérables', ['Victor Hugo'], '{title}'),
                         ([], 'Les Misérables.epub'))

    def test_unsafe_filename_characters_are_still_removed(self):
        folders, name = self.format_path('红楼梦:甲?乙*丙|丁<戊>"己', ['曹雪芹'], '{authors}/{title}')
        self.assertEqual(folders, ['曹雪芹'])
        self.assertIn('红楼梦', name)
        self.assertTrue(name.endswith('.epub'))
        self.assertFalse(set(name) & set('<>:"/\\|?*'))

    def test_english_paths_are_unchanged(self):
        self.assertEqual(self.format_path('Pride and Prejudice', ['Jane Austen'], '{authors}/{title}'),
                         (['Jane Austen'], 'Pride and Prejudice.epub'))


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(UploadPathTests))
    sys.exit(not result.wasSuccessful())
