#!/usr/bin/env python3
"""Unit tests for bench/human/make_human_kit.py and bench/human/score_human.py."""

import csv
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bench" / "human"))

import make_human_kit as kit_mod  # noqa: E402
import score_human as score_mod  # noqa: E402


def _write_fake_png(path: pathlib.Path, label: bytes = b"png") -> None:
    """Write minimal bytes representing a placeholder image file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + label)


def _create_fake_run(run_dir: pathlib.Path, num_pairs: int = 4) -> tuple[dict, dict]:
    """Create a synthetic run directory with pairs.json, key.json, and A/B media."""
    pairs_list = []
    key_map = {}
    for i in range(1, num_pairs + 1):
        pid = f"pair_{i:02d}"
        skill_side = "A" if i % 2 == 1 else "B"
        for side in ("A", "B"):
            _write_fake_png(run_dir / "pairs" / pid / side / "contact-sheet.png", f"{pid}-{side}".encode())
            _write_fake_png(run_dir / "pairs" / pid / side / "filmstrip.png", f"{pid}-{side}-fs".encode())
        pairs_list.append(
            {
                "pair_id": pid,
                "brief": f"Brief {i}",
                "A": {"contact_sheet": f"pairs/{pid}/A/contact-sheet.png", "filmstrip": f"pairs/{pid}/A/filmstrip.png"},
                "B": {"contact_sheet": f"pairs/{pid}/B/contact-sheet.png", "filmstrip": f"pairs/{pid}/B/filmstrip.png"},
            }
        )
        key_map[pid] = {"skill": skill_side, "mood": "editorial", "brief": f"Brief {i}"}

    (run_dir / "pairs.json").write_text(json.dumps({"pairs": pairs_list}), encoding="utf-8")
    (run_dir / "key.json").write_text(json.dumps(key_map), encoding="utf-8")
    return {"pairs": pairs_list}, key_map


def _write_human_csv(path: pathlib.Path, rows: list[dict]) -> None:
    """Write synthetic human rater CSV with deterministic column order."""
    headers = [
        "rater_id_anon",
        "role",
        "vision_note",
        "pair_id",
        "winner",
        "a_c1",
        "a_c2",
        "a_c3",
        "a_c4",
        "a_c5",
        "a_c6",
        "b_c1",
        "b_c2",
        "b_c3",
        "b_c4",
        "b_c5",
        "b_c6",
        "reason",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


class TestHumanKit(unittest.TestCase):
    """Tests for offline blind kit generation and human/LLM scoring."""

    def test_make_human_kit_creates_blind_gallery_without_key_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            run_dir = tmp_path / "run1"
            out_dir = tmp_path / "kit"
            _create_fake_run(run_dir, num_pairs=4)

            rc = kit_mod.main(["--run-dir", str(run_dir), "--out-dir", str(out_dir), "--seed", "7"])
            self.assertEqual(rc, 0)

            index_file = out_dir / "index.html"
            self.assertTrue(index_file.is_file())
            self.assertFalse((out_dir / "key.json").exists())
            self.assertEqual(list(out_dir.rglob("*key*")), [])

            html_text = index_file.read_text(encoding="utf-8")
            self.assertNotIn("noskill", html_text.lower())
            self.assertIn("localStorage", html_text)
            self.assertIn("CSV İndir", html_text)
            for col in (
                "rater_id_anon",
                "role",
                "vision_note",
                "pair_id",
                "winner",
                "a_c1",
                "b_c6",
                "reason",
            ):
                self.assertIn(col, html_text)

            # Media copied for all pairs
            self.assertTrue((out_dir / "media" / "pair_01" / "A" / "contact-sheet.png").is_file())
            self.assertTrue((out_dir / "media" / "pair_01" / "B" / "filmstrip.png").is_file())

    def test_make_human_kit_is_offline_and_shuffles_deterministically(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            run_dir = tmp_path / "run2"
            _create_fake_run(run_dir, num_pairs=5)

            kit_a = tmp_path / "kit_a"
            kit_b = tmp_path / "kit_b"
            kit_c = tmp_path / "kit_c"
            kit_mod.build_human_kit(run_dir, kit_a, seed=123)
            kit_mod.build_human_kit(run_dir, kit_b, seed=123)
            kit_mod.build_human_kit(run_dir, kit_c, seed=999)

            html_a = (kit_a / "index.html").read_text(encoding="utf-8")
            html_b = (kit_b / "index.html").read_text(encoding="utf-8")
            html_c = (kit_c / "index.html").read_text(encoding="utf-8")

            self.assertEqual(html_a, html_b)
            self.assertNotEqual(html_a, html_c)
            self.assertNotIn("https://", html_a)
            self.assertNotIn("http://", html_a)

    def test_cohens_kappa_exact_values(self):
        # Perfect agreement
        k_perf, po_perf, _ = score_mod.cohens_kappa(
            ["skill", "skill", "noskill", "noskill"],
            ["skill", "skill", "noskill", "noskill"],
        )
        self.assertAlmostEqual(po_perf, 1.0, places=6)
        self.assertAlmostEqual(k_perf, 1.0, places=6)

        # Exact chance agreement (50/50 balanced independent)
        k_chance, po_chance, pe_chance = score_mod.cohens_kappa(
            ["skill", "skill", "noskill", "noskill"],
            ["skill", "noskill", "skill", "noskill"],
        )
        self.assertAlmostEqual(po_chance, 0.5, places=6)
        self.assertAlmostEqual(pe_chance, 0.5, places=6)
        self.assertAlmostEqual(k_chance, 0.0, places=6)

        # Complete disagreement (< 0)
        k_opp, po_opp, _ = score_mod.cohens_kappa(
            ["skill", "skill", "noskill", "noskill"],
            ["noskill", "noskill", "skill", "skill"],
        )
        self.assertAlmostEqual(po_opp, 0.0, places=6)
        self.assertLess(k_opp, 0.0)
        self.assertAlmostEqual(k_opp, -1.0, places=6)

    def test_score_human_win_rate_wilson_ci_criteria_and_roles(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            run_dir = tmp_path / "run"
            _, key_map = _create_fake_run(run_dir, num_pairs=4)

            # Rater 1 (Tasarımcı): picks skill on all 4 pairs, skill scores 5, noskill scores 3 -> diff +2
            r1_rows = []
            # Rater 2 (Geliştirici): picks skill on 3/4 pairs, noskill on pair_04
            r2_rows = []
            for i in range(1, 5):
                pid = f"pair_{i:02d}"
                sk = key_map[pid]["skill"]
                ns = "B" if sk == "A" else "A"
                scores_sk = {f"{sk.lower()}_c{c}": 5 for c in range(1, 7)}
                scores_ns = {f"{ns.lower()}_c{c}": 3 for c in range(1, 7)}
                r1_rows.append(
                    {
                        "rater_id_anon": "r_001",
                        "role": "Tasarımcı",
                        "vision_note": "",
                        "pair_id": pid,
                        "winner": sk,
                        **scores_sk,
                        **scores_ns,
                        "reason": "Net hiyerarşi",
                    }
                )
                w2 = sk if i <= 3 else ns
                r2_rows.append(
                    {
                        "rater_id_anon": "r_002",
                        "role": "Geliştirici",
                        "vision_note": "Gözlük",
                        "pair_id": pid,
                        "winner": w2,
                        **scores_sk,
                        **scores_ns,
                        "reason": "İyi",
                    }
                )

            csv_dir = tmp_path / "csvs"
            _write_human_csv(csv_dir / "rater1.csv", r1_rows)
            _write_human_csv(csv_dir / "rater2.csv", r2_rows)

            report = score_mod.score_human(csv_dir, run_dir / "key.json")
            # 7/8 = 87.5%
            self.assertIn("7/8 = **87.5%**", report)
            lo, hi = score_mod.wilson_ci(7, 8)
            self.assertIn(f"{100.0 * lo:.1f}% – {100.0 * hi:.1f}%", report)
            self.assertIn("| Tasarımcı | 1 | 4/4 | 100.0% |", report)
            self.assertIn("| Geliştirici | 1 | 3/4 | 75.0% |", report)
            self.assertIn("| 1. İlk izlenim | 8 | +2.00 |", report)

    def test_score_human_with_llm_summary_and_out_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            run_dir = tmp_path / "run"
            _, key_map = _create_fake_run(run_dir, num_pairs=4)

            csv_dir = tmp_path / "csvs"
            rows = []
            # Human majority: pair_01=skill, pair_02=skill, pair_03=noskill, pair_04=noskill
            human_arms = {"pair_01": "skill", "pair_02": "skill", "pair_03": "noskill", "pair_04": "noskill"}
            for pid, arm in human_arms.items():
                sk = key_map[pid]["skill"]
                ns = "B" if sk == "A" else "A"
                winner = sk if arm == "skill" else ns
                rows.append(
                    {
                        "rater_id_anon": "r_100",
                        "role": "Son kullanıcı",
                        "vision_note": "",
                        "pair_id": pid,
                        "winner": winner,
                        **{f"a_c{c}": 4 for c in range(1, 7)},
                        **{f"b_c{c}": 4 for c in range(1, 7)},
                        "reason": "",
                    }
                )
            _write_human_csv(csv_dir / "r100.csv", rows)

            # LLM agrees on all 4 -> kappa should be 1.0000
            llm_json = tmp_path / "llm_results.json"
            llm_json.write_text(json.dumps(human_arms), encoding="utf-8")

            out_md = tmp_path / "reports" / "human_report.md"
            rc = score_mod.main(
                [
                    "--csv-dir",
                    str(csv_dir),
                    "--key",
                    str(run_dir / "key.json"),
                    "--llm-summary",
                    str(llm_json),
                    "--out-md",
                    str(out_md),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(out_md.is_file())
            md_text = out_md.read_text(encoding="utf-8")
            self.assertIn("Cohen's κ (kappa):** **1.0000**", md_text)

            # Also test verdicts directory with .txt files showing opposite verdicts -> kappa = -1.0000
            verdicts_dir = tmp_path / "verdicts"
            verdicts_dir.mkdir()
            txt_lines = []
            for pid, arm in human_arms.items():
                sk = key_map[pid]["skill"]
                ns = "B" if sk == "A" else "A"
                opp_side = ns if arm == "skill" else sk
                txt_lines.append(f"{pid}: {opp_side} | 4 | test | A 4/4/4/4 B 4/4/4/4")
            (verdicts_dir / "judge_1.txt").write_text("\n".join(txt_lines), encoding="utf-8")

            report_opp = score_mod.score_human(csv_dir, run_dir / "key.json", verdicts_dir)
            self.assertIn("Cohen's κ (kappa):** **-1.0000**", report_opp)


if __name__ == "__main__":
    unittest.main()
