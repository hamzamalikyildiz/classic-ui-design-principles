"""Tests that documented CLI commands, referenced files, and SKILL.md size stay valid."""
import pathlib
import re
import shlex
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _extract_bash_commands(md_path):
    """Return non-comment command lines inside ```bash fenced blocks."""
    text = md_path.read_text(encoding='utf-8')
    cmds = []
    for block in re.findall(r'```bash\r?\n(.*?)```', text, re.DOTALL):
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line or line.startswith('#'):
                continue
            cmds.append(line)
    return cmds


def _is_local_runnable_uitools(tokens):
    """Return True if a tokenized command is a self-contained uitools.py invocation."""
    if len(tokens) < 3 or 'scripts/uitools.py' not in tokens[1]:
        return False
    sub = tokens[2]
    if sub in ('--help', '-h'):
        return True
    if sub == 'audit':
        return '--help' in tokens or '-h' in tokens
    return sub in ('contrast', 'scale', 'radius', 'snap')


def _is_local_runnable_render_help(tokens):
    """Return True if a tokenized command is `render.py --help`."""
    return (
        len(tokens) >= 3
        and 'scripts/render.py' in tokens[1]
        and ('--help' in tokens or '-h' in tokens)
    )


def _run_doc_cmd(tokens):
    cmd = [sys.executable] + tokens[1:]
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=15)


class DocsCommandsTests(unittest.TestCase):
    def test_skill_md_size_under_11kb(self):
        size = (ROOT / 'SKILL.md').stat().st_size
        self.assertLessEqual(size, 11264, f'SKILL.md exceeds 11 KB ({size} bytes)')
        self.assertLessEqual(size, 11000, f'SKILL.md exceeds 11000 B CRLF budget ({size} bytes)')

    def test_skill_md_referenced_files_exist(self):
        text = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
        refs = sorted(set(re.findall(r'(?:reference|moods)/[a-z0-9_-]+\.md', text)))
        self.assertGreaterEqual(len(refs), 10)
        for rel in refs:
            p = ROOT / rel
            self.assertTrue(p.is_file(), f'Missing file referenced in SKILL.md: {rel}')
            self.assertGreater(p.stat().st_size, 0, f'Referenced file is empty: {rel}')

    def test_readme_uitools_commands_run(self):
        cmds = _extract_bash_commands(ROOT / 'README.md')
        ran = 0
        for line in cmds:
            tokens = shlex.split(line)
            if not _is_local_runnable_uitools(tokens):
                continue
            res = _run_doc_cmd(tokens)
            self.assertEqual(res.returncode, 0, f'Command failed: {line}\n{res.stderr}')
            ran += 1
        self.assertGreaterEqual(ran, 4, 'Expected >=4 runnable uitools.py commands in README.md')

    def test_tooling_md_uitools_commands_run(self):
        cmds = _extract_bash_commands(ROOT / 'reference' / 'tooling.md')
        ran = 0
        for line in cmds:
            tokens = shlex.split(line)
            if not _is_local_runnable_uitools(tokens):
                continue
            res = _run_doc_cmd(tokens)
            self.assertEqual(res.returncode, 0, f'Command failed: {line}\n{res.stderr}')
            ran += 1
        self.assertGreaterEqual(ran, 5, 'Expected >=5 runnable uitools.py commands in reference/tooling.md')

    def test_docs_render_help_commands_run(self):
        ran = 0
        for md in (ROOT / 'README.md', ROOT / 'reference' / 'tooling.md'):
            for line in _extract_bash_commands(md):
                tokens = shlex.split(line)
                if not _is_local_runnable_render_help(tokens):
                    continue
                res = _run_doc_cmd(tokens)
                self.assertEqual(res.returncode, 0, f'Command failed: {line}\n{res.stderr}')
                ran += 1
        self.assertGreaterEqual(ran, 1, 'Expected at least 1 `render.py --help` command in docs')

    def test_documented_scripts_and_demo_exist(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        for mod in ('uitools.py', 'render.py', 'uicolor.py', 'uiparse.py', 'uiroute.py', 'uiignore.py'):
            self.assertIn(mod, readme)
            self.assertTrue((ROOT / 'scripts' / mod).is_file(), f'Missing scripts/{mod}')
        self.assertTrue((ROOT / 'examples' / 'app-demo' / 'routes.json').is_file())


if __name__ == '__main__':
    unittest.main()
