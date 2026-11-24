"""Unit tests for package_skill.py (default nested claude.ai bundle and --flat marketplace bundle)."""
import contextlib
import io
import pathlib
import sys
import tempfile
import unittest
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import package_skill  # noqa: E402


class PackageSkillTests(unittest.TestCase):
    def _assert_no_excluded_paths(self, names):
        for name in names:
            parts = name.split('/')
            self.assertNotIn('bench', parts, f'Unexpected bench/ entry in archive: {name}')
            self.assertNotIn('tests', parts, f'Unexpected tests/ entry in archive: {name}')
            self.assertNotIn('examples', parts, f'Unexpected examples/ entry in archive: {name}')
            self.assertNotIn('__pycache__', parts, f'Unexpected __pycache__ entry in archive: {name}')
            self.assertFalse(name.endswith(('.pyc', '.pyo')), f'Unexpected bytecode file in archive: {name}')

    def _assert_valid_skill_frontmatter(self, skill_text):
        norm = skill_text.replace('\r\n', '\n')
        self.assertTrue(norm.startswith('---\n'), 'SKILL.md must begin with YAML frontmatter')
        end = norm.find('\n---\n', 4)
        self.assertGreater(end, 0, 'SKILL.md must close YAML frontmatter')
        frontmatter = norm[4:end]
        self.assertIn('name: classic-ui-design-principles', frontmatter)
        self.assertIn('description:', frontmatter)

    def test_default_nested_archive_for_claude_ai(self):
        with tempfile.TemporaryDirectory() as td:
            out = pathlib.Path(td) / 'nested.zip'
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                res = package_skill.main(['--out', str(out)])
            self.assertEqual(res, out)
            self.assertTrue(out.is_file())

            with zipfile.ZipFile(out, 'r') as z:
                self.assertIsNone(z.testzip())
                names = set(z.namelist())
                self.assertTrue(names)
                self.assertTrue(
                    all(n.startswith('classic-ui-design-principles/') for n in names),
                    'Default archive must nest all entries under classic-ui-design-principles/',
                )
                self._assert_no_excluded_paths(names)

                expected = {
                    'classic-ui-design-principles/SKILL.md',
                    'classic-ui-design-principles/README.md',
                    'classic-ui-design-principles/LICENSE',
                    'classic-ui-design-principles/moods/trust.md',
                    'classic-ui-design-principles/reference/rules.md',
                    'classic-ui-design-principles/scripts/uitools.py',
                    'classic-ui-design-principles/scripts/render.py',
                    'classic-ui-design-principles/scripts/verify.py',
                    'classic-ui-design-principles/scripts/e2e_gate.py',
                }
                self.assertTrue(expected.issubset(names), f'Missing expected entries: {expected - names}')
                skill_txt = z.read('classic-ui-design-principles/SKILL.md').decode('utf-8')
                self._assert_valid_skill_frontmatter(skill_txt)

    def test_flat_archive_for_marketplace_root_skill_md(self):
        with tempfile.TemporaryDirectory() as td:
            out = pathlib.Path(td) / 'flat.zip'
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                res = package_skill.main(['--out', str(out), '--flat'])
            self.assertEqual(res, out)
            self.assertTrue(out.is_file())

            with zipfile.ZipFile(out, 'r') as z:
                self.assertIsNone(z.testzip())
                names = set(z.namelist())
                self.assertTrue(names)
                self.assertFalse(
                    any(n.startswith('classic-ui-design-principles/') for n in names),
                    '--flat archive must not nest entries under classic-ui-design-principles/',
                )
                self._assert_no_excluded_paths(names)

                expected = {
                    'SKILL.md',
                    'README.md',
                    'LICENSE',
                    'moods/trust.md',
                    'reference/rules.md',
                    'scripts/uitools.py',
                    'scripts/render.py',
                    'scripts/verify.py',
                    'scripts/e2e_gate.py',
                }
                self.assertTrue(expected.issubset(names), f'Missing expected root entries: {expected - names}')
                skill_txt = z.read('SKILL.md').decode('utf-8')
                self._assert_valid_skill_frontmatter(skill_txt)


if __name__ == '__main__':
    unittest.main()
