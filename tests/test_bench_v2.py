"""Unit tests for v2 app-mode benchmark harness (make_tasks, build_pairs, make_judge_sets, JUDGE_PROMPT, score)."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'bench'))
sys.path.insert(0, str(ROOT / 'scripts'))

import build_pairs
import make_judge_sets
import make_tasks
import render as R
import score


def _write_png(path, size=(1200, 800), color=(240, 244, 248)):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new('RGB', size, color).save(path, format='PNG')


class MakeTasksV2Tests(unittest.TestCase):
    def test_make_tasks_page_mode_backward_compatible(self):
        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            make_tasks.main([
                str(work),
                '--skill', str(ROOT),
                '--python', sys.executable,
                '--briefs', 'r',
                '--moods', 'trust',
                '--reps', '1',
            ])
            index = json.loads((work / 'tasks' / 'index.json').read_text(encoding='utf-8'))
            self.assertEqual({e['arm'] for e in index}, {'skill', 'noskill'})
            self.assertEqual(len(index), 2)
            skill_txt = (work / 'tasks' / 'skill-trust-r-1.txt').read_text(encoding='utf-8')
            noskill_txt = (work / 'tasks' / 'noskill-trust-r-1.txt').read_text(encoding='utf-8')
            self.assertIn('Build one web page.', skill_txt)
            self.assertIn('uitools.py', skill_txt)
            self.assertNotIn('app-flow.md', skill_txt)
            self.assertIn('(no --check; use it only to render a screenshot)', noskill_txt)
            self.assertNotIn('uitools.py', noskill_txt)

    def test_make_tasks_app_mode_and_ablation_no_leakage(self):
        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            make_tasks.main([
                str(work),
                '--skill', str(ROOT),
                '--python', sys.executable,
                '--mode', 'app',
                '--ablation',
                '--briefs', 'cv-opt',
                '--moods', 'trust',
                '--reps', '1',
            ])
            index = json.loads((work / 'tasks' / 'index.json').read_text(encoding='utf-8'))
            self.assertEqual(len(index), 3)
            self.assertEqual({e['arm'] for e in index}, {'skill', 'noskill', 'noskill_check'})
            self.assertTrue(all(e.get('mode') == 'app' for e in index))

            skill_txt = (work / 'tasks' / 'skill-trust-cv-opt-1.txt').read_text(encoding='utf-8')
            noskill_txt = (work / 'tasks' / 'noskill-trust-cv-opt-1.txt').read_text(encoding='utf-8')
            ablation_txt = (work / 'tasks' / 'noskill_check-trust-cv-opt-1.txt').read_text(encoding='utf-8')

            # Shared technical contract present in all 3 arms (including no-debug-switcher & repeatable trigger)
            for txt in (skill_txt, noskill_txt, ablation_txt):
                self.assertIn('CVPulse', txt)
                self.assertIn('#/login', txt)
                self.assertIn('#/list', txt)
                self.assertIn('#/detail/1', txt)
                self.assertIn('#/settings', txt)
                self.assertIn('?state=', txt)
                self.assertIn('window.__RENDER_STATE__', txt)
                self.assertIn('data-motion-trigger', txt)
                self.assertIn('do NOT render a visible debug state-switcher bar/pills in the product UI', txt)
                self.assertIn('repeatable/toggleable', txt)

            # Skill arm reads SKILL.md + App references + runs audit and render --routes --motion
            for ref in (
                'SKILL.md',
                'app-flow.md',
                'states.md',
                'motion.md',
                'typography-locale.md',
                'sample-data.md',
                'uitools.py',
                '--routes',
                '--motion',
            ):
                self.assertIn(ref, skill_txt)

            # Noskill arm: no skill docs, no uitools, no --check, no --routes
            self.assertIn('Do NOT read anything under', noskill_txt)
            self.assertIn('(no --check; use it only to render a screenshot)', noskill_txt)
            for forbidden in ('SKILL.md', 'app-flow.md', 'states.md', 'motion.md', 'typography-locale.md', 'sample-data.md', 'uitools.py', '--routes', '--motion'):
                self.assertNotIn(forbidden, noskill_txt)

            # noskill_check ablation arm: no skill docs, no uitools, ONLY render.py --check --routes
            self.assertIn('Do NOT read anything under', ablation_txt)
            self.assertIn('render.py', ablation_txt)
            self.assertIn('--check', ablation_txt)
            self.assertIn('--routes', ablation_txt)
            for forbidden in ('SKILL.md', 'app-flow.md', 'states.md', 'motion.md', 'typography-locale.md', 'sample-data.md', 'uitools.py'):
                self.assertNotIn(forbidden, ablation_txt)

            # Bound routes JSON created for skill and noskill_check with file:/// URI and no pre-click state_overrides
            for arm in ('skill', 'noskill_check'):
                rf = work / 'routes' / f'{arm}-trust-cv-opt-1.json'
                self.assertTrue(rf.is_file())
                cfg = json.loads(rf.read_text(encoding='utf-8'))
                self.assertTrue(cfg['base_url'].startswith('file:///'))
                R.validate_routes_config(cfg)
                detail_route = next(r for r in cfg['routes'] if r['name'] == 'detail')
                self.assertEqual(detail_route.get('motion_trigger'), '[data-motion-trigger]')
                self.assertNotIn('state_overrides', detail_route)


class BuildPairsAppTests(unittest.TestCase):
    def test_all_routes_app_templates_have_motion_trigger_and_no_preclick_overrides(self):
        expected_files = {
            'cicd-board.json',
            'clinic-appt.json',
            'cv-opt.json',
            'invoice-quote.json',
            'meal-planner.json',
            'support-inbox.json',
        }
        routes_dir = ROOT / 'bench' / 'routes_app'
        actual_files = {p.name for p in routes_dir.glob('*.json')}
        self.assertEqual(actual_files, expected_files)
        for fname in sorted(expected_files):
            cfg = json.loads((routes_dir / fname).read_text(encoding='utf-8'))
            validated = R.validate_routes_config(cfg)
            detail_route = next(r for r in validated['routes'] if r['name'] == 'detail')
            self.assertEqual(detail_route.get('motion_trigger'), '[data-motion-trigger]', fname)
            self.assertNotIn('state_overrides', detail_route, f'{fname} should not pre-click [data-motion-trigger]')

    def test_prepare_routes_config_all_app_briefs_valid(self):
        briefs = json.loads((ROOT / 'bench' / 'briefs_app.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as td:
            html_file = pathlib.Path(td) / 'app.html'
            html_file.write_text('<html><body></body></html>', encoding='utf-8')
            expected_uri = html_file.resolve().as_uri()
            for mood, items in briefs.items():
                for brief_id in items:
                    cfg = build_pairs.prepare_routes_config(brief_id, html_file)
                    self.assertEqual(cfg['base_url'], expected_uri)
                    validated = R.validate_routes_config(cfg)
                    names = [r['name'] for r in validated['routes']]
                    self.assertEqual(names, ['login', 'list', 'detail', 'settings'], f'{mood}/{brief_id}')

    def test_parse_page_stem_and_extract_route_metrics(self):
        self.assertEqual(build_pairs.parse_page_stem('trust-cv-opt-1'), ('trust', 'cv-opt', '1'))
        self.assertEqual(build_pairs.parse_page_stem('editorial-support-inbox-2'), ('editorial', 'support-inbox', '2'))
        self.assertEqual(build_pairs.parse_page_stem('bold-a-1'), ('bold', 'a', '1'))

        report = {
            'summary': {'FAIL': 1, 'WARN': 3, 'INFO': 1},
            'captures': [{'route': 'login'}, {'route': 'detail'}],
            'findings': [
                {'severity': 'FAIL', 'rule': 'axe-color-contrast', 'message': 'contrast fail'},
                {'severity': 'WARN', 'rule': 'overflow-x', 'message': 'overflow'},
                {'severity': 'WARN', 'rule': 'slow-feedback', 'message': 'delayed'},
                {'severity': 'WARN', 'rule': 'reduced-motion-ignored', 'message': 'ignored'},
                {'severity': 'INFO', 'rule': 'info-only', 'message': 'ok'},
            ],
        }
        m = build_pairs.extract_route_metrics(report)
        self.assertEqual(m['axe_serious'], 1)
        self.assertEqual(m['layout_warns'], 3)
        self.assertEqual(m['motion_warns'], 2)
        self.assertEqual(m['capture_count'], 2)

    def test_build_pairs_app_mode_schema_and_ablation(self):
        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            for arm, warn_cnt in (('skill', 0), ('noskill', 2), ('noskill_check', 1)):
                raw_dir = work / 'raw' / arm
                raw_dir.mkdir(parents=True, exist_ok=True)
                (raw_dir / 'trust-cv-opt-1.html').write_text(
                    f'<!-- {arm} comment --><html><body><h1>{arm}</h1></body></html>',
                    encoding='utf-8',
                )

            def fake_render(cmd, **kwargs):
                out_dir = pathlib.Path(cmd[cmd.index('--out-dir') + 1])
                routes_file = pathlib.Path(cmd[cmd.index('--routes') + 1])
                cfg = json.loads(routes_file.read_text(encoding='utf-8'))
                self.assertTrue(cfg['base_url'].startswith('file:///'))
                self.assertIn('--motion', cmd)
                _write_png(out_dir / 'contact-sheet.png', size=(1360, 500), color=(220, 230, 240))
                _write_png(out_dir / 'detail' / 'filmstrip.png', size=(1500, 220), color=(30, 30, 35))
                html_txt = pathlib.Path(R.urllib.request.url2pathname(R.urllib.parse.urlsplit(cfg['base_url']).path)).read_text(encoding='utf-8')
                warns = 0 if 'skill' in html_txt and 'noskill' not in html_txt else (1 if 'noskill_check' in html_txt else 2)
                findings = [{'severity': 'WARN', 'rule': 'overflow-x', 'message': 'w'}] * warns
                report = {
                    'summary': {'FAIL': 0, 'WARN': warns, 'INFO': 0},
                    'captures': [{'route': 'detail'}],
                    'findings': findings,
                }
                (out_dir / 'report.json').write_text(json.dumps(report), encoding='utf-8')
                return subprocess.CompletedProcess(cmd, 0, json.dumps(report), '')

            with mock.patch.object(build_pairs.subprocess, 'run', side_effect=fake_render):
                build_pairs.main([str(work), '--app', '--seed', '3', '--width', '1000'])

            # 3 pairwise comparisons: skill vs noskill, skill vs noskill_check, noskill_check vs noskill
            pm = json.loads((work / 'PAIR_MAP_DO_NOT_OPEN.json').read_text(encoding='utf-8'))
            self.assertEqual(len(pm), 3)
            comps = {v['comparison'] for v in pm.values()}
            self.assertEqual(comps, {'skill_vs_noskill', 'skill_vs_noskill_check', 'noskill_check_vs_noskill'})

            pairs_json = json.loads((work / 'pairs.json').read_text(encoding='utf-8'))
            key_json = json.loads((work / 'key.json').read_text(encoding='utf-8'))
            self.assertEqual(pairs_json['mode'], 'app')
            self.assertEqual(len(pairs_json['pairs']), 3)
            self.assertIn('pairs', key_json)
            self.assertIn('pages', key_json)

            # Blind pairs.json must NOT leak skill or arm identity
            blind_dump = json.dumps(pairs_json)
            self.assertNotIn('noskill', blind_dump)
            self.assertNotIn('"skill"', blind_dump)

            for entry in pairs_json['pairs']:
                pid = entry['id']
                for side in ('A', 'B'):
                    cs_rel = entry[side]['contact_sheet']
                    fs_rel = entry[side]['filmstrip']
                    self.assertTrue((work / cs_rel).is_file())
                    self.assertTrue((work / fs_rel).is_file())
                    self.assertTrue((work / 'judge' / f'{pid}-{side}-contact-sheet.png').is_file())
                    self.assertTrue((work / 'judge' / f'{pid}-{side}-filmstrip.png').is_file())
                    # Verify HTML comments were stripped during anonymization
                    anon_html = (work / entry[side]['html']).read_text(encoding='utf-8')
                    self.assertNotIn('<!--', anon_html)


class JudgePromptAndSetsTests(unittest.TestCase):
    def test_judge_prompt_and_make_judge_sets_page_vs_app_modes(self):
        page_prompt = make_judge_sets.load_judge_prompt(app_mode=False)
        app_prompt = make_judge_sets.load_judge_prompt(app_mode=True)
        self.assertIn('1. Görsel çekicilik', page_prompt)
        self.assertNotIn('5. Durumlar ve geri bildirim', page_prompt)
        self.assertIn('A 8/8/7/9 B 7/6/8/7', page_prompt)

        self.assertIn('5. Durumlar ve geri bildirim', app_prompt)
        self.assertIn('6. Hareket ve akıcılık', app_prompt)
        self.assertIn('A 8/8/7/9/8/7 B 7/6/8/7/5/6', app_prompt)

        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            (work / 'judge').mkdir()
            pm = {
                'cift1': {
                    'A': 'p1001',
                    'B': 'p1002',
                    'arm_a': 'skill',
                    'arm_b': 'noskill',
                    'skill': 'A',
                    'focal': 'A',
                    'comparison': 'skill_vs_noskill',
                    'mood': 'trust',
                    'brief': 'cv-opt',
                    'rep': '1',
                },
            }
            (work / 'PAIR_MAP_DO_NOT_OPEN.json').write_text(json.dumps(pm), encoding='utf-8')
            for side in ('A', 'B'):
                _write_png(work / 'judge' / f'cift1-{side}-contact-sheet.png', size=(600, 400))
                _write_png(work / 'judge' / f'cift1-{side}-filmstrip.png', size=(600, 180))

            make_judge_sets.main([str(work), '--app', '--seed', '11'])
            for side in ('A', 'B'):
                self.assertTrue((work / 'judge_ece' / f'cift1-{side}-contact-sheet.png').is_file())
                self.assertTrue((work / 'judge_ece' / f'cift1-{side}-filmstrip.png').is_file())

            task_ece = (work / 'judge_tasks' / 'ece.txt').read_text(encoding='utf-8')
            self.assertIn('contact-sheet.png', task_ece)
            self.assertIn('filmstrip.png', task_ece)
            self.assertIn('8/8/7/9/8/7', task_ece)


class ScoreV2Tests(unittest.TestCase):
    def test_score_backward_compatible_with_real_run8(self):
        report = score.score_run(ROOT / 'bench' / 'runs' / 'run8')
        self.assertIn('Pairs: 6, judges: 5, votes: 30.', report)
        self.assertIn('**Skill win rate (all votes): 25/30 = 83%**', report)
        self.assertIn('Per-pair majority: skill wins 6, no-skill wins 0, ties 0; exact sign test p = 0.0312.', report)
        self.assertIn('| visual appeal | +0.73 |', report)
        self.assertIn('| professional look | +1.13 |', report)
        self.assertIn('| hierarchy and readability | +0.93 |', report)
        self.assertIn('| content richness | +0.47 |', report)
        self.assertNotIn('states and feedback', report)
        self.assertNotIn('noskill_check', report)

    def test_score_6_criteria_and_deltas(self):
        judges = json.loads((ROOT / 'bench' / 'judges.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            (work / 'maps').mkdir()
            (work / 'verdicts').mkdir()
            for j in judges:
                jid = j['id']
                mp = {
                    'cift1': {'orig': 'cift1', 'skill': 'A', 'arm_a': 'skill', 'arm_b': 'noskill', 'comparison': 'skill_vs_noskill', 'mood': 'trust', 'brief': 'cv-opt', 'rep': '1'},
                    'cift2': {'orig': 'cift2', 'skill': 'B', 'arm_a': 'noskill', 'arm_b': 'skill', 'comparison': 'skill_vs_noskill', 'mood': 'technical', 'brief': 'cicd-board', 'rep': '1'},
                }
                (work / 'maps' / f'MAP_{jid}.json').write_text(json.dumps(mp), encoding='utf-8')
                # cift1: skill=A wins (+1/+2/+1/+1/+3/+4)
                # cift2: skill=B wins (+1/+0/+1/+1/+3/+2) -> mean diffs: +1.00, +1.00, +1.00, +1.00, +3.00, +3.00
                lines = [
                    'cift1: A | 5 | Durumlar ve mikro anlar belirgin. | A 8/9/8/8/9/9 B 7/7/7/7/6/5',
                    'cift2: B | 4 | Akis ve hareket cok akici. | A 7/8/7/7/6/6 B 8/8/8/8/9/8',
                ]
                (work / 'verdicts' / f'judge_{jid}.txt').write_text('\n'.join(lines), encoding='utf-8')

            report = score.score_run(work)
            self.assertIn('**Skill win rate (all votes): 10/10 = 100%**', report)
            self.assertIn('| states and feedback | +3.00 |', report)
            self.assertIn('| motion and fluidity | +3.00 |', report)
            self.assertIn('Δ states = +3.00, Δ motion = +3.00', report)

    def test_score_ablation_noskill_check(self):
        judges = json.loads((ROOT / 'bench' / 'judges.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td)
            (work / 'maps').mkdir()
            (work / 'verdicts').mkdir()
            for j in judges:
                jid = j['id']
                mp = {
                    'cift1': {'orig': 'cift1', 'skill': 'A', 'arm_a': 'skill', 'arm_b': 'noskill', 'comparison': 'skill_vs_noskill', 'mood': 'trust', 'brief': 'cv-opt', 'rep': '1'},
                    'cift2': {'orig': 'cift2', 'skill': 'A', 'arm_a': 'skill', 'arm_b': 'noskill_check', 'comparison': 'skill_vs_noskill_check', 'mood': 'trust', 'brief': 'cv-opt', 'rep': '1'},
                    'cift3': {'orig': 'cift3', 'skill': None, 'arm_a': 'noskill_check', 'arm_b': 'noskill', 'focal': 'A', 'comparison': 'noskill_check_vs_noskill', 'mood': 'trust', 'brief': 'cv-opt', 'rep': '1'},
                }
                (work / 'maps' / f'MAP_{jid}.json').write_text(json.dumps(mp), encoding='utf-8')
                lines = [
                    'cift1: A | 5 | Skill daha iyi. | A 9/9/9/9/9/9 B 6/6/6/6/5/5',
                    'cift2: A | 4 | Kurallar arac kontrolunden fazlasini katiyor. | A 9/9/9/9/9/9 B 7/7/8/7/7/6',
                    'cift3: A | 4 | Arac kontrolu tek basina hata sayisini dusurmus. | A 7/7/8/7/7/6 B 6/6/6/6/5/5',
                ]
                (work / 'verdicts' / f'judge_{jid}.txt').write_text('\n'.join(lines), encoding='utf-8')

            key_obj = {
                'mode': 'app',
                'pages': {
                    'p1': {'arm': 'skill', 'mood': 'trust', 'brief': 'cv-opt', 'rep': '1'},
                    'p2': {'arm': 'noskill_check', 'mood': 'trust', 'brief': 'cv-opt', 'rep': '1'},
                    'p3': {'arm': 'noskill', 'mood': 'trust', 'brief': 'cv-opt', 'rep': '1'},
                },
            }
            metrics_obj = {
                'p1': {'axe_serious': 0, 'layout_warns': 0},
                'p2': {'axe_serious': 0, 'layout_warns': 1},
                'p3': {'axe_serious': 2, 'layout_warns': 3},
            }
            (work / 'key.json').write_text(json.dumps(key_obj), encoding='utf-8')
            (work / 'metrics.json').write_text(json.dumps(metrics_obj), encoding='utf-8')

            report = score.score_run(work)
            self.assertIn('**Skill win rate (all votes): 5/5 = 100%**', report)
            self.assertIn('## Ablation (noskill_check)', report)
            self.assertIn('### skill vs noskill_check: 5/5 = 100%', report)
            self.assertIn('### noskill_check vs noskill: 5/5 = 100%', report)
            self.assertIn('| skill | 1 | 0 | 0.0 |', report)
            self.assertIn('| noskill_check | 1 | 0 | 1.0 |', report)
            self.assertIn('| noskill | 1 | 1 | 3.0 |', report)


if __name__ == '__main__':
    unittest.main()
