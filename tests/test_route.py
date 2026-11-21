"""Unit and integration tests for İP-A6: route/screen composition, component inlining, and screen-level rules.

Run: python -m unittest tests/test_route.py -v
"""
import contextlib
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import uiroute as ur  # noqa: E402

spec = importlib.util.spec_from_file_location('uitools', SCRIPTS / 'uitools.py')
ut = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ut)


def _rules(issues, rule):
    return [i for i in issues if i[1] == rule]


class ComponentInliningAndRouteTests(unittest.TestCase):
    def test_01_same_file_inner_component_inherits_dark_ancestor(self):
        """1) Same-file inner function component inherits bg-slate-900 from caller; no false wcag-aa FAIL."""
        src = (
            'import React from "react";\n'
            'function ScoreBars() {\n'
            '  return (\n'
            '    <div className="mt-4 space-y-2">\n'
            '      <div className="flex items-center justify-between text-sm text-white/80">\n'
            '        <span>Accessibility</span>\n'
            '        <span>92%</span>\n'
            '      </div>\n'
            '    </div>\n'
            '  );\n'
            '}\n'
            'export function ScoreCard() {\n'
            '  return (\n'
            '    <section className="rounded-xl bg-slate-900 p-6 text-white">\n'
            '      <ScoreBars />\n'
            '    </section>\n'
            '  );\n'
            '}\n'
        )
        iss = _rules(ut.audit('ScoreCard.tsx', 8, {}, txt=src), 'wcag-aa')
        self.assertEqual([i for i in iss if i[0] in ('FAIL', 'WARN')], [], iss)

    def test_02_same_file_inner_component_real_contrast_fail_caught_with_line(self):
        """2) Same-file inner component with real low-contrast text inside bg-slate-900 FAILS wcag-aa at original line."""
        src = (
            'import React from "react";\n'
            'const InnerBadge = () => (\n'
            '  <div className="mt-2">\n'
            '    <span className="text-sm text-slate-800">Hard to read</span>\n'
            '  </div>\n'
            ');\n'
            'export function DarkPanel() {\n'
            '  return (\n'
            '    <section className="rounded-xl bg-slate-900 p-6">\n'
            '      <InnerBadge />\n'
            '    </section>\n'
            '  );\n'
            '}\n'
        )
        iss = _rules(ut.audit('DarkPanel.tsx', 8, {}, txt=src), 'wcag-aa')
        self.assertEqual(len(iss), 1, iss)
        self.assertEqual(iss[0][0], 'FAIL')
        self.assertIn('text-slate-800 on bg-slate-900', iss[0][2])
        self.assertTrue(iss[0][2].startswith('L4 '), iss[0][2])

    def test_03_relative_import_inlining_in_route_mode(self):
        """3) Relative import (./ScoreBars) is resolved and inlined in route mode."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            app_dir = root / 'app' / 'score'
            app_dir.mkdir(parents=True)
            (app_dir / 'ScoreBars.tsx').write_text(
                'export function ScoreBars() {\n'
                '  return <p className="text-sm text-white/80">92%</p>;\n'
                '}\n',
                encoding='utf-8',
            )
            page = app_dir / 'page.tsx'
            page.write_text(
                'import { ScoreBars } from "./ScoreBars";\n'
                'export default function ScorePage() {\n'
                '  return <main className="bg-slate-900 p-8"><ScoreBars /></main>;\n'
                '}\n',
                encoding='utf-8',
            )
            composed = ur.compose_route(page, root_dir=root)
            self.assertEqual(composed.inlined_count, 1)
            self.assertEqual(len(composed.inlined_files), 1)
            iss = _rules(ut.audit(str(page), 8, {}, txt=composed, route_mode=True, root_dir=root), 'wcag-aa')
            self.assertEqual(iss, [], iss)

    def test_04_at_slash_alias_import_resolution(self):
        """4) Default @/ alias resolves against root/src and root."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            comp_dir = root / 'src' / 'components'
            app_dir = root / 'src' / 'app'
            comp_dir.mkdir(parents=True)
            app_dir.mkdir(parents=True)

            target = comp_dir / 'DarkBanner.tsx'
            target.write_text(
                'export default function DarkBanner() {\n'
                '  return <div className="bg-slate-900 p-6"><p className="text-white">Banner</p></div>;\n'
                '}\n',
                encoding='utf-8',
            )
            page = app_dir / 'page.tsx'
            page.write_text(
                'import DarkBanner from "@/components/DarkBanner";\n'
                'export default function Page() { return <main><DarkBanner /></main>; }\n',
                encoding='utf-8',
            )

            resolved = ur.resolve_import('@/components/DarkBanner', page, root_dir=root)
            self.assertEqual(resolved, target.resolve())
            composed = ur.compose_route(page, root_dir=root)
            self.assertEqual(composed.inlined_count, 1)
            self.assertIn('bg-slate-900', str(composed))

    def test_05_tsconfig_paths_alias_and_cva_resolution(self):
        """5) tsconfig.json compilerOptions.paths (@ui/* -> src/components/ui/*) resolves imports and CVA."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            ui_dir = root / 'src' / 'design-system' / 'ui'
            app_dir = root / 'src' / 'app'
            ui_dir.mkdir(parents=True)
            app_dir.mkdir(parents=True)

            tsconfig = root / 'tsconfig.json'
            tsconfig.write_text(
                '// JSONC comment in tsconfig\n'
                '{\n'
                '  "compilerOptions": {\n'
                '    "baseUrl": ".",\n'
                '    "paths": {\n'
                '      "@ui/*": ["src/design-system/ui/*"],\n'
                '    },\n'
                '  },\n'
                '}\n',
                encoding='utf-8',
            )
            btn_file = ui_dir / 'button.tsx'
            btn_file.write_text(
                'import { cva } from "class-variance-authority";\n'
                'export const buttonVariants = cva("inline-flex items-center", {\n'
                '  variants: {\n'
                '    variant: { default: "bg-indigo-600 text-white", outline: "border bg-white text-slate-900" },\n'
                '    size: { sm: "h-8 px-3", lg: "h-12 px-6" },\n'
                '  },\n'
                '  defaultVariants: { variant: "default", size: "sm" },\n'
                '});\n'
                'export function Button(props: any) {\n'
                '  return <button className={buttonVariants(props)} />;\n'
                '}\n',
                encoding='utf-8',
            )
            panel_file = ui_dir / 'panel.tsx'
            panel_file.write_text(
                'export function Panel({ children }: { children: any }) {\n'
                '  return <section className="bg-slate-900 p-6">{children}</section>;\n'
                '}\n',
                encoding='utf-8',
            )
            page = app_dir / 'page.tsx'
            page.write_text(
                'import { Button } from "@ui/button";\n'
                'import { Panel } from "@ui/panel";\n'
                'export default function Page() {\n'
                '  return (\n'
                '    <main>\n'
                '      <Panel>\n'
                '        <p className="text-white/80">Content</p>\n'
                '        <Button size="sm">Save</Button>\n'
                '      </Panel>\n'
                '    </main>\n'
                '  );\n'
                '}\n',
                encoding='utf-8',
            )

            ts_paths = ur.load_tsconfig_paths(tsconfig_path=tsconfig, root_dir=root)
            self.assertEqual(ur.resolve_import('@ui/button', page, root_dir=root, tsconfig_paths=ts_paths), btn_file.resolve())
            iss = ut.audit(str(page), 8, {}, route_mode=True, root_dir=root, tsconfig_path=str(tsconfig))
            self.assertEqual(_rules(iss, 'wcag-aa'), [], iss)
            # CVA from @ui/button should detect h-8 (32px) on solid default Button
            fitts = _rules(iss, 'fitts-primary')
            self.assertEqual(len(fitts), 1, iss)
            self.assertIn('32px', fitts[0][2])

    def test_06_index_tsx_directory_import_resolution(self):
        """6) Directory import (./Card) resolves to ./Card/index.tsx."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            card_dir = root / 'components' / 'Card'
            card_dir.mkdir(parents=True)
            idx = card_dir / 'index.tsx'
            idx.write_text(
                'export function Card({ children }: { children: any }) {\n'
                '  return <div className="rounded-xl bg-slate-900 p-6">{children}</div>;\n'
                '}\n',
                encoding='utf-8',
            )
            page = root / 'app' / 'page.tsx'
            page.parent.mkdir(parents=True)
            page.write_text(
                'import { Card } from "../components/Card";\n'
                'export default function Page() {\n'
                '  return <main><Card><span className="text-white/80">Inside index.tsx</span></Card></main>;\n'
                '}\n',
                encoding='utf-8',
            )
            self.assertEqual(ur.resolve_import('../components/Card', page, root_dir=root), idx.resolve())
            iss = ut.audit(str(page), 8, {}, route_mode=True, root_dir=root)
            self.assertEqual(_rules(iss, 'wcag-aa'), [], iss)

    def test_07_children_prop_substitution_across_components(self):
        """7) {children} and {props.children} are replaced with caller JSX children."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            comp = root / 'DarkCard.tsx'
            comp.write_text(
                'export function DarkCard({ children }: { children: React.ReactNode }) {\n'
                '  return (\n'
                '    <div className="rounded-xl bg-slate-900 p-6 text-white">\n'
                '      {children}\n'
                '    </div>\n'
                '  );\n'
                '}\n',
                encoding='utf-8',
            )
            page = root / 'page.tsx'
            page.write_text(
                'import { DarkCard } from "./DarkCard";\n'
                'export default function Page() {\n'
                '  return (\n'
                '    <main>\n'
                '      <DarkCard>\n'
                '        <p className="text-white/80">Metin</p>\n'
                '        <p className="text-slate-800">Bad child</p>\n'
                '      </DarkCard>\n'
                '    </main>\n'
                '  );\n'
                '}\n',
                encoding='utf-8',
            )
            iss = _rules(ut.audit(str(page), 8, {}, route_mode=True, root_dir=root), 'wcag-aa')
            self.assertEqual(len(iss), 1, iss)
            self.assertIn('text-slate-800 on bg-slate-900', iss[0][2])
            self.assertFalse(any('text-white/80' in i[2] for i in iss))

    def test_08_depth_limit_4_and_circular_import_guard(self):
        """8) Max depth <= 4 stops deep chains and A -> B -> A circular imports do not loop infinitely."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            # A -> B -> A cycle
            (root / 'A.tsx').write_text(
                'import { B } from "./B";\n'
                'export function A() { return <div className="bg-slate-900 p-4"><B /></div>; }\n',
                encoding='utf-8',
            )
            (root / 'B.tsx').write_text(
                'import { A } from "./A";\n'
                'export function B() { return <div className="p-2"><A /></div>; }\n',
                encoding='utf-8',
            )
            cycle_entry = root / 'CyclePage.tsx'
            cycle_entry.write_text(
                'import { A } from "./A";\n'
                'export default function CyclePage() { return <main><A /></main>; }\n',
                encoding='utf-8',
            )
            composed_cycle = ur.compose_route(cycle_entry, root_dir=root)
            self.assertEqual(composed_cycle.inlined_count, 2)  # A then B, then <A /> stopped by cycle guard

            # Depth chain: Page(0) -> L1(1) -> L2(2) -> L3(3) -> L4(4) -> L5(5, NOT expanded)
            for lvl in range(1, 6):
                nxt = f'import {{ L{lvl + 1} }} from "./L{lvl + 1}";\n' if lvl < 5 else ''
                body = f'<L{lvl + 1} />' if lvl < 5 else '<span>leaf-5</span>'
                (root / f'L{lvl}.tsx').write_text(
                    f'{nxt}export function L{lvl}() {{ return <div data-lvl="{lvl}">{body}</div>; }}\n',
                    encoding='utf-8',
                )
            deep_entry = root / 'DeepPage.tsx'
            deep_entry.write_text(
                'import { L1 } from "./L1";\n'
                'export default function DeepPage() { return <main><L1 /></main>; }\n',
                encoding='utf-8',
            )
            composed_deep = ur.compose_route(deep_entry, root_dir=root, max_depth=4)
            s_deep = str(composed_deep)
            self.assertIn('data-lvl="4"', s_deep)
            self.assertNotIn('data-lvl="5"', s_deep)
            self.assertNotIn('leaf-5', s_deep)

    def test_09_unresolved_third_party_wrapper_unknown_bg_no_false_contrast(self):
        """9) Unresolved 3rd-party package wrapper (import { FancyBox } from 'external-ui') avoids white-bg false FAIL."""
        src = (
            'import { FancyBox } from "external-ui";\n'
            'export function Widget() {\n'
            '  return (\n'
            '    <FancyBox>\n'
            '      <p className="text-white">Light text inside unknown 3rd-party surface</p>\n'
            '    </FancyBox>\n'
            '  );\n'
            '}\n'
        )
        iss = _rules(ut.audit('Widget.tsx', 8, {}, txt=src), 'wcag-aa')
        self.assertEqual(iss, [], iss)

    def test_10_component_file_downgrades_screen_rules_to_info_with_note(self):
        """10) Component file (components/Sidebar.tsx) downgrades screen rules to INFO with --route hint."""
        sidebar_path = ROOT / 'tests' / 'fixtures' / 'real_app' / 'components' / 'Sidebar.tsx'
        self.assertTrue(ur.is_component_file(sidebar_path, route_mode=False))
        self.assertFalse(ur.is_component_file(sidebar_path, route_mode=True))

        iss = ut.audit(str(sidebar_path), 8, {}, None, 'trust')
        hero = _rules(iss, 'no-hero-surface')
        self.assertEqual(len(hero), 1, iss)
        self.assertEqual(hero[0][0], 'INFO')
        self.assertIn('(bileşen dosyası; ekran kuralları için --route kullan)', hero[0][2])

        # Verify miller-7, skeleton-empty, landmark-main, and screen-level single-primary-cta also downgrade in component files,
        # while block-level single-primary-cta (inside <section>) remains WARN.
        comp_src = (
            '<html><body>\n'
            '<nav>' + '<a href="/x">Link</a>' * 8 + '</nav>\n'
            '<div>{items.map(i => <span key={i}>{i}</span>)}</div>\n'
            '<button className="bg-indigo-600 text-white h-12">ScreenA</button>\n'
            '<button className="bg-indigo-600 text-white h-12">ScreenB</button>\n'
            '<section><button className="bg-indigo-600 text-white h-12">BlockA</button>'
            '<button className="bg-indigo-600 text-white h-12">BlockB</button></section>\n'
            '</body></html>\n'
        )
        # Note: use a path without <html>? Wait: <html> makes is_page_file=True! So test without <html> for component file:
        comp_jsx = (
            '<nav>' + '<a href="/x">Link</a>' * 8 + '</nav>\n'
            '<div>{items.map(i => <span key={i}>{i}</span>)}</div>\n'
            '<button className="bg-indigo-600 text-white h-12">ScreenA</button>\n'
            '<button className="bg-indigo-600 text-white h-12">ScreenB</button>\n'
            '<section><button className="bg-indigo-600 text-white h-12">BlockA</button>'
            '<button className="bg-indigo-600 text-white h-12">BlockB</button></section>\n'
        )
        c_iss = ut.audit('src/components/NavBar.tsx', 8, {}, None, 'trust', txt=comp_jsx)
        for rule in ('no-hero-surface', 'miller-7', 'skeleton-empty'):
            r_list = _rules(c_iss, rule)
            self.assertTrue(r_list, f'expected {rule} in {c_iss}')
            self.assertEqual(r_list[0][0], 'INFO')
            self.assertIn('(bileşen dosyası; ekran kuralları için --route kullan)', r_list[0][2])
        cta_list = _rules(c_iss, 'single-primary-cta')
        self.assertEqual(sorted(i[0] for i in cta_list), ['INFO', 'WARN'], cta_list)

    def test_11_page_file_and_route_mode_keep_screen_rules_at_warn(self):
        """11) Page file (app/dashboard/page.tsx) and --route mode keep no-hero-surface at WARN."""
        page_path = ROOT / 'tests' / 'fixtures' / 'real_app' / 'app' / 'dashboard' / 'page.tsx'
        self.assertTrue(ur.is_page_file(page_path))
        self.assertFalse(ur.is_component_file(page_path))
        iss_file = _rules(ut.audit(str(page_path), 8, {}, None, 'trust'), 'no-hero-surface')
        self.assertEqual([i[0] for i in iss_file], ['WARN'])

        sidebar_path = ROOT / 'tests' / 'fixtures' / 'real_app' / 'components' / 'Sidebar.tsx'
        iss_route = _rules(ut.audit(str(sidebar_path), 8, {}, None, 'trust', route_mode=True), 'no-hero-surface')
        self.assertEqual([i[0] for i in iss_route], ['WARN'])

    def test_12_cli_route_and_routes_glob_with_summary_table(self):
        """12) CLI --route and --routes-glob scan multiple screens, show inlined counts and ROUTE SUMMARY."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            comp_dir = root / 'components'
            comp_dir.mkdir()
            (comp_dir / 'Header.tsx').write_text(
                'export function Header() {\n'
                '  return <header className="bg-slate-900 p-4"><span className="text-white">App</span></header>;\n'
                '}\n',
                encoding='utf-8',
            )
            (comp_dir / 'ScorePanel.tsx').write_text(
                'export function ScorePanel() {\n'
                '  return <div className="bg-slate-900 p-6"><p className="text-white/80">95%</p></div>;\n'
                '}\n',
                encoding='utf-8',
            )
            dash_page = root / 'app' / 'dashboard' / 'page.tsx'
            dash_page.parent.mkdir(parents=True)
            dash_page.write_text(
                'import { Header } from "@/components/Header";\n'
                'import { ScorePanel } from "@/components/ScorePanel";\n'
                'export default function Dashboard() {\n'
                '  return <main><Header /><ScorePanel /></main>;\n'
                '}\n',
                encoding='utf-8',
            )
            settings_page = root / 'app' / 'settings' / 'page.tsx'
            settings_page.parent.mkdir(parents=True)
            settings_page.write_text(
                'import { Header } from "@/components/Header";\n'
                'export default function Settings() {\n'
                '  return <main><Header /><p className="text-slate-900">Settings</p></main>;\n'
                '}\n',
                encoding='utf-8',
            )

            # Single --route test
            out_single = io.StringIO()
            with self.assertRaises(SystemExit) as cm1, contextlib.redirect_stdout(out_single):
                ut.main(['audit', '--route', str(dash_page), '--root', str(root)])
            self.assertEqual(cm1.exception.code, 0)
            s1 = out_single.getvalue()
            self.assertIn('[inlined 2 component(s)]', s1)
            self.assertIn('components/Header.tsx', s1)
            self.assertIn('components/ScorePanel.tsx', s1)
            self.assertIn('SUMMARY FAIL=0', s1)

            # Multi-route --routes-glob test
            out_glob = io.StringIO()
            with self.assertRaises(SystemExit) as cm2, contextlib.redirect_stdout(out_glob):
                ut.main(['audit', '--routes-glob', 'app/**/page.tsx', '--root', str(root)])
            self.assertEqual(cm2.exception.code, 0)
            s2 = out_glob.getvalue()
            self.assertIn('app/dashboard/page.tsx', s2)
            self.assertIn('app/settings/page.tsx', s2)
            self.assertIn('ROUTE SUMMARY:', s2)
            self.assertIn('inlined=2', s2)
            self.assertIn('inlined=1', s2)


if __name__ == '__main__':
    unittest.main()
