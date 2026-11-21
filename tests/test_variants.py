"""Unit tests for İP-A3 conditional class variant model and JSX conditional regions.

Run: python -m unittest tests/test_variants.py -v
"""
import ast
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import uiparse as up  # noqa: E402


FIXTURES = ROOT / 'tests' / 'fixtures' / 'real_app'


class ClassVariantModelTests(unittest.TestCase):
    def test_plain_string_literals_and_missing(self):
        self.assertEqual(up.classset(' id="x"').base, [])
        self.assertEqual(up.classset(' class="px-4 py-2 bg-white"').base, ['px-4', 'py-2', 'bg-white'])
        self.assertEqual(up.classset(" className='text-sm text-slate-900'").base, ['text-sm', 'text-slate-900'])
        cs = up.classset(' className={"rounded-lg p-4"}')
        self.assertEqual(cs.base, ['rounded-lg', 'p-4'])
        self.assertEqual(cs.branches, [])
        self.assertFalse(cs.exploded)
        combos = up.expand_combinations(cs)
        self.assertEqual(len(combos), 1)
        self.assertEqual(combos[0].classes, ['rounded-lg', 'p-4'])
        self.assertEqual(combos[0].label, '')

    def test_template_literal_with_ternary_and_logical_and(self):
        attrs = ' className={`px-4 ${isActive ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-900"} ${extra && "font-bold"}`}'
        cs = up.classset(attrs)
        self.assertEqual(cs.base, ['px-4'])
        self.assertEqual(len(cs.branches), 2)
        self.assertFalse(cs.exploded)
        combos = up.expand_combinations(cs)
        self.assertEqual(len(combos), 4)
        self.assertEqual(combos[0].classes, ['px-4', 'bg-blue-600', 'text-white', 'font-bold'])
        self.assertEqual(combos[0].label, 'isActive=true, extra=true')
        self.assertEqual(combos[3].classes, ['px-4', 'bg-slate-100', 'text-slate-900'])
        self.assertEqual(combos[3].label, 'isActive=false, extra=false')

    def test_template_literal_partial_interpolation_avoids_broken_fragments(self):
        attrs = ' className={`px-4 bg-${tone}-500 text-white`}'
        cs = up.classset(attrs)
        self.assertEqual(cs.base, ['px-4', 'text-white'])

    def test_logical_and_expression(self):
        cs = up.classset(' className={isOpen && "bg-slate-900 text-white"}')
        self.assertEqual(cs.base, [])
        self.assertEqual(len(cs.branches), 1)
        gid, alts = cs.branches[0]
        self.assertEqual(alts, [['bg-slate-900', 'text-white'], []])
        self.assertEqual(cs.groups[gid]['labels'], ['isOpen=true', 'isOpen=false'])

        cs2 = up.classset(' className={user?.isAdmin && !loading && "ring-2 ring-blue-500"}')
        self.assertEqual(len(cs2.branches), 1)
        self.assertEqual(cs2.branches[0][1], [['ring-2', 'ring-blue-500'], []])

    def test_fallback_or_and_nullish_coalescing(self):
        cs_or = up.classset(' className={maybeCls || "bg-white text-slate-900"}')
        self.assertEqual(len(cs_or.branches), 1)
        self.assertEqual(cs_or.branches[0][1], [['bg-white', 'text-slate-900'], []])

        cs_nullish = up.classset(' className={cn("p-4", customText ?? "text-slate-700")}')
        self.assertEqual(cs_nullish.base, ['p-4'])
        self.assertEqual(cs_nullish.branches[0][1], [['text-slate-700'], []])

        cs_and_or = up.classset(' className={(cond && "bg-emerald-600") || "bg-slate-200"}')
        self.assertEqual(cs_and_or.branches[0][1], [['bg-emerald-600'], ['bg-slate-200']])

    def test_single_level_ternary_and_comparison_condition(self):
        cs = up.classset(' className={status === "active" ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-900"}')
        self.assertEqual(cs.base, [])
        self.assertEqual(len(cs.branches), 1)
        gid, alts = cs.branches[0]
        self.assertEqual(alts, [['bg-emerald-600', 'text-white'], ['bg-slate-100', 'text-slate-900']])
        combos = up.expand_combinations(cs)
        self.assertNotIn('active', combos[0].classes)
        self.assertIn('status === "active"=true', combos[0].label)

    def test_nested_ternary_two_levels(self):
        cs_right = up.classset(' className={c1 ? "bg-red-600" : c2 ? "bg-amber-500" : "bg-emerald-600"}')
        self.assertEqual(len(cs_right.branches), 1)
        gid, alts = cs_right.branches[0]
        self.assertEqual(alts, [['bg-red-600'], ['bg-amber-500'], ['bg-emerald-600']])
        self.assertEqual(cs_right.groups[gid]['labels'], ['c1=true', 'c1=false,c2=true', 'c1=false,c2=false'])

        cs_left = up.classset(' className={c1 ? (c2 ? "p-2" : "p-4") : "p-6"}')
        self.assertEqual(len(cs_left.branches), 1)
        self.assertEqual(cs_left.branches[0][1], [['p-2'], ['p-4'], ['p-6']])
        self.assertEqual(cs_left.groups[cs_left.branches[0][0]]['labels'], ['c1=true,c2=true', 'c1=true,c2=false', 'c1=false'])

        cs_both = up.classset(' className={c1 ? (c2 ? "a" : "b") : (c3 ? "c" : "d")}')
        self.assertEqual(len(cs_both.branches), 1)
        self.assertEqual(cs_both.branches[0][1], [['a'], ['b'], ['c'], ['d']])

    def test_helper_calls_cn_clsx_twmerge_cx_and_arrays(self):
        for fn in ('cn', 'clsx', 'twMerge', 'cx'):
            cs = up.classset(f' className={{{fn}("px-3 py-1", active && "bg-slate-900")}}')
            self.assertEqual(cs.base, ['px-3', 'py-1'])
            self.assertEqual(cs.branches[0][1], [['bg-slate-900'], []])

        nested = up.classset(' className={twMerge(clsx(["flex", isRow ? "flex-row" : "flex-col"]), "gap-2")}')
        self.assertEqual(nested.base, ['flex', 'gap-2'])
        self.assertEqual(nested.branches[0][1], [['flex-row'], ['flex-col']])

    def test_object_literal_syntax(self):
        attrs = " className={cn('base', { 'a b': cond, c: flag, active, 'font-bold': true, 'hidden': false })}"
        cs = up.classset(attrs)
        self.assertEqual(cs.base, ['base', 'font-bold'])
        self.assertEqual(len(cs.branches), 3)
        self.assertEqual(cs.branches[0][1], [['a', 'b'], []])
        self.assertEqual(cs.branches[1][1], [['c'], []])
        self.assertEqual(cs.branches[2][1], [['active'], []])
        self.assertEqual(cs.groups[cs.branches[0][0]]['labels'], ['cond=true', 'cond=false'])
        self.assertEqual(cs.groups[cs.branches[1][0]]['labels'], ['flag=true', 'flag=false'])
        self.assertEqual(cs.groups[cs.branches[2][0]]['labels'], ['active=true', 'active=false'])

    def test_multiple_independent_groups_and_exact_limit_8(self):
        cs = up.classset(' className={cn(c1 ? "a" : "b", c2 && "c", c3 && "d")}')
        self.assertEqual(len(cs.branches), 3)
        self.assertEqual(len({gid for gid, _ in cs.branches}), 3)
        self.assertFalse(cs.exploded)
        combos = up.expand_combinations(cs, limit=8)
        self.assertEqual(len(combos), 8)
        self.assertFalse(cs.exploded)

    def test_correlated_identical_condition_does_not_cross_match(self):
        attrs = ' className={`${isDark ? "bg-slate-900" : "bg-white"} ${isDark ? "text-white" : "text-slate-900"}`}'
        cs = up.classset(attrs)
        self.assertEqual(len(cs.branches), 1)
        combos = up.expand_combinations(cs)
        self.assertEqual(len(combos), 2)
        self.assertEqual(combos[0].classes, ['bg-slate-900', 'text-white'])
        self.assertEqual(combos[1].classes, ['bg-white', 'text-slate-900'])

    def test_branch_explosion_marks_exploded_and_caps_at_8(self):
        attrs = ' className={cn(c1 && "a", c2 && "b", c3 && "c", c4 && "d")}'
        cs = up.classset(attrs)
        self.assertTrue(cs.exploded)
        combos = up.expand_combinations(cs, limit=8)
        self.assertEqual(len(combos), 8)
        self.assertTrue(cs.exploded)

    def test_chip_fixture_branches_never_cross_match(self):
        src = (FIXTURES / 'Chip.tsx').read_text(encoding='utf-8')
        nodes = [n for n in up.walk(src) if n[0] == 'button']
        self.assertEqual(len(nodes), 1)
        cs = nodes[0].classset
        self.assertEqual(cs.base, ['px-3', 'py-1', 'rounded-full', 'text-sm', 'font-medium', 'text-slate-900'])
        combos = cs.expand()
        self.assertEqual(len(combos), 2)
        self.assertEqual(up.pick(combos[0].classes, 'bg'), 'slate-900')
        self.assertEqual(up.pick(combos[0].classes, 'text'), 'white')
        self.assertEqual(combos[0].label, 'selected=true')
        self.assertEqual(up.pick(combos[1].classes, 'bg'), 'slate-100')
        self.assertEqual(up.pick(combos[1].classes, 'text'), 'slate-900')
        self.assertEqual(combos[1].label, 'selected=false')
        for combo in combos:
            self.assertFalse('text-white' in combo.classes and 'bg-slate-100' in combo.classes)

    def test_bad_contrast_fixture_preserves_failing_branch(self):
        src = (FIXTURES / 'BadContrast.tsx').read_text(encoding='utf-8')
        btns = [n for n in up.walk(src) if n[0] == 'button']
        self.assertEqual(len(btns), 1)
        combos = btns[0].classset.expand()
        self.assertEqual(len(combos), 2)
        self.assertEqual(up.pick(combos[1].classes, 'bg'), 'slate-200')
        self.assertEqual(up.pick(combos[1].classes, 'text'), 'slate-400')

    def test_actions_fixture_jsx_conditional_regions(self):
        src = (FIXTURES / 'Actions.tsx').read_text(encoding='utf-8')
        regions = up.jsx_regions(src)
        self.assertEqual(len(regions), 1)
        self.assertEqual(regions[0].kind, 'ternary')
        self.assertEqual([b.label for b in regions[0].branches], ['isEditing=true', 'isEditing=false'])

        buttons = [n for n in up.walk(src) if n[0] == 'Button']
        self.assertEqual(len(buttons), 2)
        self.assertEqual(buttons[0].branch_region, (regions[0].region_id, 0))
        self.assertEqual(buttons[1].branch_region, (regions[0].region_id, 1))
        self.assertEqual(buttons[0].branch_label, 'isEditing=true')
        self.assertEqual(buttons[1].branch_label, 'isEditing=false')

    def test_jsx_regions_complementary_and_blocks_and_intervening_tag(self):
        paired = (
            '<div>\n'
            '  {c && <Button className="bg-slate-900 text-white">A</Button>}\n'
            '  {!c && <Button className="bg-blue-600 text-white">B</Button>}\n'
            '</div>'
        )
        regs = up.jsx_regions(paired)
        self.assertEqual(len(regs), 1)
        self.assertEqual(regs[0].kind, 'and-pair')
        btns = [n for n in up.walk(paired) if n[0] == 'Button']
        self.assertEqual(btns[0].branch_region[0], btns[1].branch_region[0])
        self.assertNotEqual(btns[0].branch_region[1], btns[1].branch_region[1])

        eq_paired = (
            '<div>\n'
            '  {tab === "edit" && <Button>Edit</Button>}\n'
            '  {tab === "view" && <Button>View</Button>}\n'
            '</div>'
        )
        eq_btns = [n for n in up.walk(eq_paired) if n[0] == 'Button']
        self.assertEqual(eq_btns[0].branch_region[0], eq_btns[1].branch_region[0])
        self.assertNotEqual(eq_btns[0].branch_region[1], eq_btns[1].branch_region[1])

        separated = (
            '<div>\n'
            '  {c && <Button>A</Button>}\n'
            '  <span>sep</span>\n'
            '  {!c && <Button>B</Button>}\n'
            '</div>'
        )
        sep_btns = [n for n in up.walk(separated) if n[0] == 'Button']
        self.assertNotEqual(sep_btns[0].branch_region[0], sep_btns[1].branch_region[0])

    def test_jsx_regions_lookup_and_nested_branches(self):
        lookup_src = (
            '<div>\n'
            '  {{ a: <Button>Alpha</Button>, b: <Button>Beta</Button> }[k]}\n'
            '</div>'
        )
        regs = up.jsx_regions(lookup_src)
        self.assertEqual(len(regs), 1)
        self.assertEqual(regs[0].kind, 'lookup')
        btns = [n for n in up.walk(lookup_src) if n[0] == 'Button']
        self.assertEqual(len(btns), 2)
        self.assertEqual(btns[0].branch_region[0], btns[1].branch_region[0])
        self.assertEqual(btns[0].branch_label, 'a')
        self.assertEqual(btns[1].branch_label, 'b')

        nested_src = (
            '<div>\n'
            '  {c1 ? (<><Button>One</Button>{c2 && <Button>Two</Button>}</>) : <Button>Three</Button>}\n'
            '</div>'
        )
        nb = [n for n in up.walk(nested_src) if n[0] == 'Button']
        self.assertEqual(len(nb), 3)
        self.assertEqual(len(nb[0].branch_regions), 1)
        self.assertEqual(len(nb[1].branch_regions), 2)
        self.assertEqual(nb[0].branch_regions[0], nb[1].branch_regions[0])
        self.assertNotEqual(nb[0].branch_regions[0], nb[2].branch_regions[0])

    def test_walk_backwards_compatible_6_tuple_and_ancestors(self):
        src = '<div className="bg-slate-900"><button className={active ? "text-white" : "text-slate-200"}>Go</button></div>'
        nodes = list(up.walk(src))
        self.assertEqual(len(nodes), 2)
        for node in nodes:
            self.assertIsInstance(node, tuple)
            self.assertEqual(len(node), 6)
            tag, attrs, cls, anc, s, e = node
            self.assertIsInstance(tag, str)
            self.assertIsInstance(attrs, str)
            self.assertIsInstance(cls, list)
            self.assertIsInstance(anc, list)
            self.assertIsInstance(s, int)
            self.assertIsInstance(e, int)
            self.assertIsInstance(node.classset, up.ClassSet)
        btn_anc = nodes[1][3]
        self.assertEqual(len(btn_anc), 1)
        self.assertIsInstance(btn_anc[0], tuple)
        self.assertEqual(len(btn_anc[0]), 4)
        self.assertEqual(btn_anc[0].classset.base, ['bg-slate-900'])

    def test_uiparse_uses_stdlib_only(self):
        tree = ast.parse((SCRIPTS / 'uiparse.py').read_text(encoding='utf-8'))
        stdlib = sys.stdlib_module_names
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(alias.name.split('.')[0], stdlib)
            elif isinstance(node, ast.ImportFrom) and node.module:
                self.assertIn(node.module.split('.')[0], stdlib)


if __name__ == '__main__':
    unittest.main()
