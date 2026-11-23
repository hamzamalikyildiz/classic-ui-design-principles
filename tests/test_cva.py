"""Unit and integration tests for İP-A5 cva / shadcn variant resolution.

Run: python -m unittest tests/test_cva.py -v
"""
import importlib.util
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import uiparse as up  # noqa: E402

spec = importlib.util.spec_from_file_location('uitools', SCRIPTS / 'uitools.py')
ut = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ut)


SHADCN_BUTTON_CVA = """
import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground shadow hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90",
        outline: "border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8",
        icon: "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)
"""


class CvaResolutionTests(unittest.TestCase):
    def test_parse_cva_definitions_standard_shadcn_button(self):
        defs = up.parse_cva_definitions(SHADCN_BUTTON_CVA)
        self.assertIn('Button', defs)
        self.assertIn('buttonVariants', defs)
        btn = defs['Button']
        self.assertEqual(btn.var_name, 'buttonVariants')
        self.assertEqual(btn.component, 'Button')
        self.assertIn('inline-flex', btn.base)
        self.assertIn('rounded-md', btn.base)
        self.assertEqual(btn.default_variants, {'variant': 'default', 'size': 'default'})
        self.assertIn('bg-primary', btn.variants['variant']['default'])
        self.assertIn('border', btn.variants['variant']['outline'])
        self.assertEqual(btn.variants['size']['sm'], ['h-8', 'rounded-md', 'px-3', 'text-xs'])
        self.assertEqual(btn.variants['size']['lg'], ['h-10', 'rounded-md', 'px-8'])
        self.assertEqual(btn.variants['size']['icon'], ['size-9'])

    def test_default_variants_applied_on_bare_button(self):
        src = SHADCN_BUTTON_CVA + '\nexport function View() {\n  return <Button>Kaydet</Button>;\n}\n'
        nodes = [n for n in up.walk(src) if n[0] == 'Button']
        self.assertEqual(len(nodes), 1)
        tag, attrs, cls, anc, s, e = nodes[0]
        self.assertIn('inline-flex', cls)
        self.assertIn('bg-primary', cls)
        self.assertIn('text-primary-foreground', cls)
        self.assertIn('h-9', cls)
        self.assertIn('px-4', cls)
        self.assertEqual(up.height_px(cls), 36.0)
        self.assertEqual(up.pick(cls, 'bg'), 'primary')
        self.assertEqual(up.pick(cls, 'text'), 'primary-foreground')

    def test_explicit_outline_and_lg_variant_not_solid_primary_cta(self):
        src = (
            SHADCN_BUTTON_CVA
            + '\nexport function View() {\n'
            + '  return <Button variant="outline" size="lg">İptal</Button>;\n'
            + '}\n'
        )
        nodes = [n for n in up.walk(src) if n[0] == 'Button']
        self.assertEqual(len(nodes), 1)
        tag, attrs, cls, anc, s, e = nodes[0]
        self.assertIn('border', cls)
        self.assertIn('border-input', cls)
        self.assertIn('bg-background', cls)
        self.assertIn('h-10', cls)
        self.assertIn('px-8', cls)
        self.assertNotIn('bg-primary', cls)
        self.assertNotIn('h-9', cls)
        self.assertEqual(up.height_px(cls), 40.0)
        self.assertFalse(ut.is_solid_cta(tag, attrs, cls))

    def test_fitts_primary_audit_flags_sm_h8_but_not_lg_h10_or_h11(self):
        sm_src = (
            SHADCN_BUTTON_CVA
            + '\nexport function SmallCtaPage() {\n'
            + '  return <main><Button size="sm">Küçük</Button></main>;\n'
            + '}\n'
        )
        sm_issues = ut.audit('SmallCtaPage.tsx', 8, {}, txt=sm_src, strict=True)
        sm_fitts = [i for i in sm_issues if i[1] == 'fitts-primary']
        self.assertEqual(len(sm_fitts), 1, f'Expected fitts-primary on size="sm", got: {sm_issues}')
        self.assertEqual(sm_fitts[0][0], 'WARN')
        self.assertIn('32px', sm_fitts[0][2])

        lg_src = (
            SHADCN_BUTTON_CVA
            + '\nexport function LargeCtaPage() {\n'
            + '  return <main><Button size="lg">Kaydet</Button></main>;\n'
            + '}\n'
        )
        lg_issues = ut.audit('LargeCtaPage.tsx', 8, {}, txt=lg_src, strict=True)
        lg_fitts = [i for i in lg_issues if i[1] == 'fitts-primary']
        self.assertEqual(lg_fitts, [], f'Unexpected fitts-primary on size="lg": {lg_fitts}')

        h11_src = (
            SHADCN_BUTTON_CVA
            + '\nexport function HeroCtaPage() {\n'
            + '  return <main><Button size="lg" className="h-11">Başla</Button></main>;\n'
            + '}\n'
        )
        h11_issues = ut.audit('HeroCtaPage.tsx', 8, {}, txt=h11_src, strict=True)
        h11_fitts = [i for i in h11_issues if i[1] == 'fitts-primary']
        self.assertEqual(h11_fitts, [])

    def test_conditional_variant_prop_produces_two_classset_branches(self):
        src = (
            SHADCN_BUTTON_CVA
            + '\nexport function ToggleAction({ isPrimary }: { isPrimary: boolean }) {\n'
            + '  return <Button variant={isPrimary ? "default" : "ghost"}>Eylem</Button>;\n'
            + '}\n'
        )
        nodes = [n for n in up.walk(src) if n[0] == 'Button']
        self.assertEqual(len(nodes), 1)
        cs = nodes[0].classset
        self.assertIn('inline-flex', cs.base)
        self.assertIn('h-9', cs.base)
        self.assertEqual(len(cs.branches), 1)
        combos = cs.expand()
        self.assertEqual(len(combos), 2)
        self.assertEqual(combos[0].label, 'isPrimary=true')
        self.assertIn('bg-primary', combos[0].classes)
        self.assertIn('text-primary-foreground', combos[0].classes)
        self.assertEqual(combos[1].label, 'isPrimary=false')
        self.assertNotIn('bg-primary', combos[1].classes)
        self.assertIn('hover:bg-accent', combos[1].classes)

    def test_correlated_conditional_variant_and_size_props(self):
        defs = up.parse_cva_definitions(SHADCN_BUTTON_CVA)
        cs = up.resolve_cva_classes(
            'Button',
            ' variant={compact ? "ghost" : "default"} size={compact ? "sm" : "lg"}',
            defs,
        )
        self.assertEqual(len(cs.branches), 1)
        combos = cs.expand()
        self.assertEqual(len(combos), 2)
        self.assertEqual(combos[0].label, 'compact=true')
        self.assertIn('h-8', combos[0].classes)
        self.assertNotIn('bg-primary', combos[0].classes)
        self.assertEqual(combos[1].label, 'compact=false')
        self.assertIn('h-10', combos[1].classes)
        self.assertIn('bg-primary', combos[1].classes)

    def test_discover_cva_definitions_across_components_ui_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            ui_dir = root / 'components' / 'ui'
            app_dir = root / 'app' / 'dashboard'
            ui_dir.mkdir(parents=True)
            app_dir.mkdir(parents=True)

            button_tsx = ui_dir / 'button.tsx'
            button_tsx.write_text(
                SHADCN_BUTTON_CVA
                + '\nexport function Button({ className, variant, size, ...props }: any) {\n'
                + '  return <button className={buttonVariants({ variant, size, className })} {...props} />;\n'
                + '}\n',
                encoding='utf-8',
            )

            badge_tsx = ui_dir / 'badge.tsx'
            badge_tsx.write_text(
                'import { cva } from "class-variance-authority";\n'
                'export const badgeVariants = cva(\n'
                '  ["inline-flex", "items-center", "rounded-full", "px-2.5", "py-0.5", "text-[10px]"],\n'
                '  {\n'
                '    variants: {\n'
                '      variant: {\n'
                '        default: "bg-primary text-primary-foreground",\n'
                '        secondary: "bg-secondary text-secondary-foreground",\n'
                '        outline: "text-foreground border",\n'
                '      },\n'
                '    },\n'
                '    defaultVariants: { variant: "default" },\n'
                '  }\n'
                ');\n',
                encoding='utf-8',
            )

            page_path = app_dir / 'page.tsx'
            page_txt = (
                'import { Button } from "@/components/ui/button";\n'
                'import { Badge } from "@/components/ui/badge";\n'
                'export default function DashboardPage() {\n'
                '  return (\n'
                '    <main className="p-6">\n'
                '      <Badge variant="secondary">Yeni</Badge>\n'
                '      <Button variant="outline" size="lg">İptal</Button>\n'
                '      <Button size="sm">Kaydet</Button>\n'
                '    </main>\n'
                '  );\n'
                '}\n'
            )
            page_path.write_text(page_txt, encoding='utf-8')

            discovered = up.discover_cva_definitions(page_path)
            self.assertIn('Button', discovered)
            self.assertIn('Badge', discovered)

            nodes = list(up.walk(page_txt, source_path=page_path))
            by_tag = {}
            for n in nodes:
                by_tag.setdefault(n[0], []).append(n)

            self.assertEqual(len(by_tag['Badge']), 1)
            badge_cls = by_tag['Badge'][0][2]
            self.assertIn('rounded-full', badge_cls)
            self.assertIn('text-[10px]', badge_cls)
            self.assertIn('bg-secondary', badge_cls)

            self.assertEqual(len(by_tag['Button']), 2)
            outline_btn_cls = by_tag['Button'][0][2]
            self.assertIn('border', outline_btn_cls)
            self.assertIn('h-10', outline_btn_cls)
            self.assertNotIn('bg-primary', outline_btn_cls)

            sm_btn_cls = by_tag['Button'][1][2]
            self.assertIn('bg-primary', sm_btn_cls)
            self.assertIn('h-8', sm_btn_cls)
            self.assertEqual(up.height_px(sm_btn_cls), 32.0)

    def test_classname_overrides_appear_after_cva_classes(self):
        src = (
            SHADCN_BUTTON_CVA
            + '\nexport function Custom() {\n'
            + '  return <Button size="sm" className="h-12 bg-emerald-600 px-6">Özel</Button>;\n'
            + '}\n'
        )
        nodes = [n for n in up.walk(src) if n[0] == 'Button']
        self.assertEqual(len(nodes), 1)
        cls = nodes[0][2]
        self.assertLess(cls.index('h-8'), cls.index('h-12'))
        self.assertLess(cls.index('bg-primary'), cls.index('bg-emerald-600'))
        self.assertEqual(up.height_px(cls), 48.0)
        self.assertEqual(up.pick(cls, 'bg'), 'emerald-600')

    def test_array_base_compound_variants_and_component_function_mapping(self):
        src = """
        const chipStyles = cva(
          ["inline-flex", "items-center", "rounded-full"],
          {
            variants: {
              intent: {
                primary: ["bg-blue-600", "text-white"],
                neutral: ["bg-slate-100", "text-slate-800"],
              },
              size: {
                sm: "h-7 px-2 text-xs",
                md: "h-9 px-3 text-sm",
              },
            },
            compoundVariants: [
              { intent: "primary", size: "md", className: "shadow-md ring-2" },
            ],
            defaultVariants: {
              intent: "primary" as const,
              size: "md" as const,
            },
          } as const
        );

        function StatusPill(props: any) {
          return <span className={chipStyles(props)} />;
        }

        export function Header() {
          return <StatusPill />;
        }
        """
        defs = up.parse_cva_definitions(src)
        self.assertIn('Chip', defs)
        self.assertIn('StatusPill', defs)
        nodes = [n for n in up.walk(src) if n[0] == 'StatusPill']
        self.assertEqual(len(nodes), 1)
        cls = nodes[0][2]
        self.assertIn('rounded-full', cls)
        self.assertIn('bg-blue-600', cls)
        self.assertIn('h-9', cls)
        self.assertIn('shadow-md', cls)
        self.assertIn('ring-2', cls)

    def test_extract_cva_metadata_detects_small_heights_and_micro_text(self):
        src = (
            SHADCN_BUTTON_CVA
            + '\nconst badgeVariants = cva("inline-flex text-[10px] px-2", {\n'
            + '  variants: { variant: { default: "bg-primary", compact: "h-7 text-[11px]" } },\n'
            + '  defaultVariants: { variant: "default" },\n'
            + '});\n'
        )
        meta = up.extract_cva_metadata(src)
        self.assertTrue(bool(meta))
        self.assertIn('Button', meta.components)
        self.assertIn('Badge', meta.components)
        self.assertIn('Button', meta)
        self.assertIn('h-9', meta.default_classes['Button'])
        self.assertIn('bg-primary', meta.default_classes['Button'])

        small_tokens = {item[3] for item in meta.small_heights}
        self.assertIn('h-8', small_tokens)
        self.assertIn('h-9', small_tokens)
        self.assertIn('size-9', small_tokens)
        self.assertIn('h-7', small_tokens)

        micro_tokens = {item[3] for item in meta.micro_texts}
        self.assertIn('text-[10px]', micro_tokens)
        self.assertIn('text-[11px]', micro_tokens)


if __name__ == '__main__':
    unittest.main()
