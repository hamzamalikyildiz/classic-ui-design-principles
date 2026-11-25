"""An audited page is untrusted: its inline `tailwind.config` must never run as code (SkillEvaluator finding)."""
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import render as rd  # noqa: E402


class InlineConfigTests(unittest.TestCase):
    def test_json_needs_no_node(self):
        self.assertEqual(rd.eval_inline_config('{"theme": {"extend": {}}}'), {'theme': {'extend': {}}})

    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_plain_object_literal_is_evaluated(self):
        cfg = rd.eval_inline_config("{ theme: { extend: { colors: { ink: '#123', brand: { 500: '#abc' } } } } }")
        self.assertEqual(cfg['theme']['extend']['colors']['ink'], '#123')
        self.assertEqual(cfg['theme']['extend']['colors']['brand']['500'], '#abc')

    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_strings_that_look_like_calls_are_fine(self):
        self.assertEqual(rd.eval_inline_config("{ a: 'rgb(1,2,3)', b: \"require(x)\" }"), {'a': 'rgb(1,2,3)', 'b': 'require(x)'})

    def test_code_is_refused_and_never_runs(self):
        canary = pathlib.Path(tempfile.mkdtemp()) / 'canary.txt'
        posix = canary.as_posix()
        hostile = [
            "{ x: require('fs').writeFileSync('%s', 'pwned') }" % posix,
            "{ x: (function(){ return this.constructor.constructor('return process')().mainModule"
            ".require('fs').writeFileSync('%s','pwned') })() }" % posix,
            "{ x: process.exit(1) }",
            "{ x: `${1+1}` }",
            "{ x: () => 1 }",
            "{ x: eval('1') }",
        ]
        for src in hostile:
            with self.subTest(src=src[:40]):
                self.assertIsNone(rd.eval_inline_config(src))
        self.assertFalse(canary.exists(), 'page code must not run on the host')

    def test_non_file_schemes_are_never_opened(self):
        for url in ('file:///C:/Windows/win.ini', 'ftp://example.com/x', 'gopher://x', ''):
            self.assertFalse(rd.reachable(url), url)


if __name__ == '__main__':
    unittest.main()
