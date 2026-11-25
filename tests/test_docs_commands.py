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


def _normalize_tokens(tokens):
    """Resolve `<skill_dir>/scripts/...` doc placeholders relative to repo ROOT."""
    out = []
    for tok in tokens:
        if tok.startswith('<skill_dir>/'):
            out.append(tok[len('<skill_dir>/'):])
        else:
            out.append(tok)
    return out


def _is_local_runnable_uitools(tokens):
    """Return True if a tokenized command is a self-contained uitools.py invocation."""
    tokens = _normalize_tokens(tokens)
    if len(tokens) < 3 or tokens[1] != 'scripts/uitools.py':
        return False
    sub = tokens[2]
    if sub in ('--help', '-h'):
        return True
    if sub == 'audit':
        return '--help' in tokens or '-h' in tokens
    return sub in ('contrast', 'scale', 'radius', 'snap')


def _is_local_runnable_render_help(tokens):
    """Return True if a tokenized command is `render.py --help`."""
    tokens = _normalize_tokens(tokens)
    return (
        len(tokens) >= 3
        and tokens[1] == 'scripts/render.py'
        and ('--help' in tokens or '-h' in tokens)
    )


def _is_local_runnable_verify_help(tokens):
    """Return True if a tokenized command is `verify.py --help`."""
    tokens = _normalize_tokens(tokens)
    return (
        len(tokens) >= 3
        and tokens[1] == 'scripts/verify.py'
        and ('--help' in tokens or '-h' in tokens)
    )


def _run_doc_cmd(tokens):
    norm = _normalize_tokens(tokens)
    cmd = [sys.executable] + norm[1:]
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

    def test_skill_dir_placeholder_normalization_and_skill_md_commands(self):
        self.assertEqual(
            _normalize_tokens(['python', '<skill_dir>/scripts/uitools.py', 'radius', '24', '8']),
            ['python', 'scripts/uitools.py', 'radius', '24', '8'],
        )
        skill_text = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('<skill_dir>/scripts/', skill_text)
        self.assertIn('verify.py', skill_text)
        self.assertIn('reference/app-flow.md` §6', skill_text)

        ran = 0
        for line in _extract_bash_commands(ROOT / 'SKILL.md'):
            tokens = shlex.split(line, comments=True)
            self.assertTrue(
                tokens[1].startswith('<skill_dir>/scripts/'),
                f'Expected <skill_dir>/scripts/ prefix in SKILL.md command: {line}',
            )
            if not _is_local_runnable_uitools(tokens):
                continue
            res = _run_doc_cmd(tokens)
            self.assertEqual(res.returncode, 0, f'Command failed: {line}\n{res.stderr}')
            ran += 1
        self.assertGreaterEqual(ran, 3, 'Expected >=3 runnable uitools.py commands in SKILL.md')

    def test_readme_uitools_commands_run(self):
        cmds = _extract_bash_commands(ROOT / 'README.md')
        ran = 0
        for line in cmds:
            tokens = shlex.split(line, comments=True)
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
            tokens = shlex.split(line, comments=True)
            if not _is_local_runnable_uitools(tokens):
                continue
            res = _run_doc_cmd(tokens)
            self.assertEqual(res.returncode, 0, f'Command failed: {line}\n{res.stderr}')
            ran += 1
        self.assertGreaterEqual(ran, 5, 'Expected >=5 runnable uitools.py commands in reference/tooling.md')

    def test_docs_render_and_verify_help_commands(self):
        render_ran = 0
        verify_documented = 0
        for md in (ROOT / 'README.md', ROOT / 'reference' / 'tooling.md'):
            for line in _extract_bash_commands(md):
                tokens = shlex.split(line, comments=True)
                if _is_local_runnable_render_help(tokens):
                    res = _run_doc_cmd(tokens)
                    self.assertEqual(res.returncode, 0, f'Command failed: {line}\n{res.stderr}')
                    render_ran += 1
                elif _is_local_runnable_verify_help(tokens):
                    verify_documented += 1
                    if (ROOT / 'scripts' / 'verify.py').is_file():
                        res = _run_doc_cmd(tokens)
                        self.assertEqual(res.returncode, 0, f'Command failed: {line}\n{res.stderr}')
        self.assertGreaterEqual(render_ran, 1, 'Expected at least 1 `render.py --help` command in docs')
        self.assertGreaterEqual(verify_documented, 1, 'Expected at least 1 `verify.py --help` command in docs')

    def test_documented_scripts_and_demo_exist(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        for mod in ('uitools.py', 'render.py', 'uicolor.py', 'uiparse.py', 'uiroute.py', 'uiignore.py'):
            self.assertIn(mod, readme)
            self.assertTrue((ROOT / 'scripts' / mod).is_file(), f'Missing scripts/{mod}')
        self.assertIn('verify.py', readme)
        self.assertTrue((ROOT / 'examples' / 'app-demo' / 'routes.json').is_file())

    def test_brownfield_workflow_and_v21_docs_consistency(self):
        app_flow = (ROOT / 'reference' / 'app-flow.md').read_text(encoding='utf-8')
        self.assertIn('## 6. Brownfield Refactor', app_flow)
        for expected in ('--write-baseline', 'data-testid', 'ThemeToggle', 'Redesigned', 'Styled to match', 'Untouched'):
            self.assertIn(expected, app_flow)

        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertNotIn('`transform`/`opacity`-only', readme)
        self.assertIn('`transform`/`opacity`-led micro-moments', readme)
        self.assertIn('package_skill.py --flat', readme)

        tooling = (ROOT / 'reference' / 'tooling.md').read_text(encoding='utf-8')
        self.assertIn('package_skill.py --flat', tooling)
        self.assertIn('--format text|json', tooling)
        self.assertIn('--fail-on none|fail|warn', tooling)

        changelog = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
        self.assertIn('verify.py', changelog)
        self.assertIn('package_skill.py --flat', changelog)


if __name__ == '__main__':
    unittest.main()
