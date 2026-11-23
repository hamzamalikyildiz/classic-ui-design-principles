#!/usr/bin/env python3
"""Score blind human A/B evaluation CSVs and compare with optional LLM judge results.

Usage:
    python bench/human/score_human.py --csv-dir <dir> --key <run_dir/key.json> \
        [--llm-summary <llm_results.json|verdicts_dir>] [--out-md <report.md>]
"""

import argparse
import csv
import json
import math
import pathlib
import re
import sys
from typing import Any

CRITERIA_NAMES = [
    "1. İlk izlenim",
    "2. Hiyerarşi & okunabilirlik",
    "3. Marka/mood uyumu",
    "4. İçerik & işlevsellik",
    "5. Durumlar & geri bildirim",
    "6. Hareket & akıcılık",
]

TXT_VERDICT_RE = re.compile(r"^\s*([A-Za-z0-9_-]+)\s*:\s*([AB])\b", re.I)


def wilson_ci(wins: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Compute the Wilson score 95% confidence interval for a binomial proportion."""
    if total <= 0:
        return (0.0, 0.0)
    p_hat = wins / total
    z2 = z * z
    denom = 1.0 + z2 / total
    center = (p_hat + z2 / (2.0 * total)) / denom
    half = (z * math.sqrt((p_hat * (1.0 - p_hat) / total) + (z2 / (4.0 * total * total)))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def cohens_kappa(labels_a: list[str], labels_b: list[str]) -> tuple[float, float, float]:
    """Compute Cohen's kappa, observed agreement (p_o), and chance agreement (p_e).

    Both lists must have the same length and contain comparable categorical labels.
    """
    if len(labels_a) != len(labels_b):
        raise ValueError("Label lists must have equal length")
    n = len(labels_a)
    if n == 0:
        return (0.0, 0.0, 0.0)

    classes = sorted(set(labels_a) | set(labels_b))
    agree = sum(1 for x, y in zip(labels_a, labels_b) if x == y)
    p_o = agree / n

    counts_a = {c: 0 for c in classes}
    counts_b = {c: 0 for c in classes}
    for x, y in zip(labels_a, labels_b):
        counts_a[x] += 1
        counts_b[y] += 1

    p_e = sum((counts_a[c] / n) * (counts_b[c] / n) for c in classes)
    if math.isclose(1.0 - p_e, 0.0, abs_tol=1e-12):
        kappa = 1.0 if math.isclose(p_o, 1.0, abs_tol=1e-12) else 0.0
    else:
        kappa = (p_o - p_e) / (1.0 - p_e)
    return (kappa, p_o, p_e)


def _kappa_interpretation(kappa: float) -> str:
    """Return a concise Landis & Koch interpretation label for Cohen's kappa."""
    if kappa < 0:
        return "Uyum yok / ters (poor)"
    if kappa < 0.20:
        return "Çok zayıf (slight)"
    if kappa < 0.40:
        return "Zayıf (fair)"
    if kappa < 0.60:
        return "Orta (moderate)"
    if kappa < 0.80:
        return "Önemli (substantial)"
    return "Neredeyse tam (almost perfect)"


def _resolve_skill_side(entry: Any) -> str | None:
    """Extract 'A' or 'B' indicating which side is the skill arm."""
    if isinstance(entry, str):
        val = entry.strip().upper()
        return val if val in {"A", "B"} else None
    if not isinstance(entry, dict):
        return None
    for k in ("skill", "skill_side", "skill_arm"):
        val = entry.get(k)
        if isinstance(val, str) and val.strip().upper() in {"A", "B"}:
            return val.strip().upper()
    for side in ("A", "B"):
        val = entry.get(side)
        if isinstance(val, str) and val.strip().lower() == "skill":
            return side
    return None


def load_key(key_path: pathlib.Path) -> dict[str, dict[str, Any]]:
    """Load key.json and normalize into {pair_id: {'skill': 'A'|'B', ...}}."""
    raw = json.loads(key_path.read_text(encoding="utf-8"))
    entries: list[tuple[str, Any]] = []
    if isinstance(raw, dict):
        if "pairs" in raw and isinstance(raw["pairs"], list):
            for item in raw["pairs"]:
                if isinstance(item, dict) and ("pair_id" in item or "id" in item):
                    pid = str(item.get("pair_id") or item.get("id"))
                    entries.append((pid, item))
        else:
            for k, v in raw.items():
                entries.append((str(k), v))
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and ("pair_id" in item or "id" in item):
                pid = str(item.get("pair_id") or item.get("id"))
                entries.append((pid, item))
    else:
        raise ValueError("Unsupported key.json structure")

    out: dict[str, dict[str, Any]] = {}
    for pid, obj in entries:
        side = _resolve_skill_side(obj)
        if side is None:
            continue
        meta = dict(obj) if isinstance(obj, dict) else {}
        meta["skill"] = side
        out[pid] = meta
    if not out:
        raise ValueError(f"No valid pair mappings found in {key_path}")
    return out


def _parse_score(val: str | None) -> float | None:
    """Parse a 1..5 score string to float, or None if missing/invalid."""
    if val is None:
        return None
    s = val.strip()
    if not s:
        return None
    try:
        num = float(s)
        return num if 1.0 <= num <= 5.0 else None
    except ValueError:
        return None


def load_human_votes(csv_dir: pathlib.Path, key: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Read all human rater CSV files in csv_dir and map winners to skill/noskill."""
    if not csv_dir.is_dir():
        raise FileNotFoundError(f"CSV directory not found: {csv_dir}")

    csv_files = sorted(csv_dir.rglob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No .csv files found in {csv_dir}")

    dedup: dict[tuple[str, str], dict[str, Any]] = {}
    for idx, csv_path in enumerate(csv_files):
        with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                pid = (row.get("pair_id") or "").strip()
                winner = (row.get("winner") or "").strip().upper()
                if pid not in key or winner not in {"A", "B"}:
                    continue
                rater = (row.get("rater_id_anon") or "").strip() or f"anon_{csv_path.stem}_{idx}"
                role = (row.get("role") or "").strip() or "Belirtilmedi"
                vision_note = (row.get("vision_note") or "").strip()
                skill_side = key[pid]["skill"]
                win = winner == skill_side

                diffs: list[float | None] = []
                for c in range(1, 7):
                    sa = _parse_score(row.get(f"a_c{c}"))
                    sb = _parse_score(row.get(f"b_c{c}"))
                    if sa is not None and sb is not None:
                        diff = (sa - sb) if skill_side == "A" else (sb - sa)
                        diffs.append(diff)
                    else:
                        diffs.append(None)

                dedup[(rater, pid)] = {
                    "rater_id_anon": rater,
                    "role": role,
                    "vision_note": vision_note,
                    "pair_id": pid,
                    "winner_side": winner,
                    "winner_arm": "skill" if win else "noskill",
                    "win": win,
                    "diffs": diffs,
                    "reason": (row.get("reason") or "").strip(),
                }

    votes = list(dedup.values())
    if not votes:
        raise ValueError(f"No valid human votes matched key.json in {csv_dir}")
    return votes


def _arm_from_label(val: str, skill_side: str) -> str | None:
    """Normalize a verdict label ('skill', 'noskill', 'A', 'B') to 'skill' or 'noskill'."""
    s = val.strip()
    low = s.lower()
    if low in {"skill", "noskill"}:
        return low
    up = s.upper()
    if up in {"A", "B"}:
        return "skill" if up == skill_side else "noskill"
    return None


def _extract_verdicts_from_obj(obj: Any, key: dict[str, dict[str, Any]], counts: dict[str, list[str]]) -> None:
    """Extract pair_id -> skill/noskill verdicts from a parsed JSON object."""
    if isinstance(obj, dict):
        for container_key in ("pairs", "verdicts", "results", "pair_results"):
            if container_key in obj:
                _extract_verdicts_from_obj(obj[container_key], key, counts)
                return
        for k, v in obj.items():
            pid = str(k)
            if pid not in key:
                continue
            skill_side = key[pid]["skill"]
            if isinstance(v, str):
                arm = _arm_from_label(v, skill_side)
                if arm:
                    counts.setdefault(pid, []).append(arm)
            elif isinstance(v, dict):
                for field in ("winner_arm", "majority", "winner", "arm", "verdict"):
                    val = v.get(field)
                    if isinstance(val, str):
                        arm = _arm_from_label(val, skill_side)
                        if arm:
                            counts.setdefault(pid, []).append(arm)
                            break
    elif isinstance(obj, list):
        for item in obj:
            if not isinstance(item, dict):
                continue
            pid = str(item.get("pair_id") or item.get("id") or "")
            if pid not in key:
                continue
            skill_side = key[pid]["skill"]
            for field in ("winner_arm", "majority", "winner", "arm", "verdict"):
                val = item.get(field)
                if isinstance(val, str):
                    arm = _arm_from_label(val, skill_side)
                    if arm:
                        counts.setdefault(pid, []).append(arm)
                        break


def load_llm_verdicts(llm_path: pathlib.Path, key: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Load LLM judge verdicts from a JSON file or a verdicts directory."""
    if not llm_path.exists():
        raise FileNotFoundError(f"LLM summary path not found: {llm_path}")

    counts: dict[str, list[str]] = {}
    if llm_path.is_file():
        obj = json.loads(llm_path.read_text(encoding="utf-8"))
        _extract_verdicts_from_obj(obj, key, counts)
    else:
        for f in sorted(llm_path.rglob("*")):
            if not f.is_file():
                continue
            if f.suffix.lower() == ".json":
                obj = json.loads(f.read_text(encoding="utf-8"))
                _extract_verdicts_from_obj(obj, key, counts)
            elif f.suffix.lower() == ".txt":
                for line in f.read_text(encoding="utf-8-sig").splitlines():
                    m = TXT_VERDICT_RE.match(line)
                    if not m:
                        continue
                    pid, side = m.group(1), m.group(2).upper()
                    if pid in key:
                        arm = "skill" if side == key[pid]["skill"] else "noskill"
                        counts.setdefault(pid, []).append(arm)

    verdicts: dict[str, str] = {}
    for pid, arms in counts.items():
        skill_n = sum(1 for a in arms if a == "skill")
        noskill_n = sum(1 for a in arms if a == "noskill")
        if skill_n > noskill_n:
            verdicts[pid] = "skill"
        elif noskill_n > skill_n:
            verdicts[pid] = "noskill"
    return verdicts


def _majority_by_pair(votes: list[dict[str, Any]]) -> dict[str, str]:
    """Compute per-pair human majority ('skill' or 'noskill'), excluding exact ties."""
    grouped: dict[str, list[bool]] = {}
    for v in votes:
        grouped.setdefault(v["pair_id"], []).append(v["win"])
    out: dict[str, str] = {}
    for pid, wins in grouped.items():
        w = sum(1 for x in wins if x)
        l = len(wins) - w
        if w > l:
            out[pid] = "skill"
        elif l > w:
            out[pid] = "noskill"
    return out


def build_report(
    votes: list[dict[str, Any]],
    key: dict[str, dict[str, Any]],
    llm_verdicts: dict[str, str] | None = None,
) -> str:
    """Build the Markdown evaluation report from human votes and optional LLM verdicts."""
    total = len(votes)
    wins = sum(1 for v in votes if v["win"])
    lo, hi = wilson_ci(wins, total)
    raters = sorted({v["rater_id_anon"] for v in votes})
    pairs_seen = sorted({v["pair_id"] for v in votes})
    human_maj = _majority_by_pair(votes)

    lines: list[str] = [
        "# İnsan Değerlendirme Sonuçları (Kör A/B)",
        "",
        f"- **Oylayıcı sayısı:** {len(raters)}",
        f"- **Değerlendirilen çift sayısı:** {len(pairs_seen)} / {len(key)}",
        f"- **Toplam oy:** {total}",
        f"- **Skill kazanma oranı:** {wins}/{total} = **{100.0 * wins / total:.1f}%** "
        f"(Wilson %95 GA: {100.0 * lo:.1f}% – {100.0 * hi:.1f}%)",
        "",
        "## 6 Kriter Ortalama Farkları (Skill − No-Skill, 1–5 ölçeği)",
        "",
        "| Kriter | Geçerli Oy | Ortalama Fark |",
        "|---|---:|---:|",
    ]

    for idx, cname in enumerate(CRITERIA_NAMES):
        vals = [v["diffs"][idx] for v in votes if v["diffs"][idx] is not None]
        if vals:
            mean_d = sum(vals) / len(vals)
            lines.append(f"| {cname} | {len(vals)} | {mean_d:+.2f} |")
        else:
            lines.append(f"| {cname} | 0 | n/a |")

    lines += [
        "",
        "## Rol Bazlı Kırılım",
        "",
        "| Rol | Oylayıcı | Skill Kazanma | Oran | Wilson %95 GA |",
        "|---|---:|---:|---:|---|",
    ]
    by_role: dict[str, list[dict[str, Any]]] = {}
    for v in votes:
        by_role.setdefault(v["role"], []).append(v)
    for role in sorted(by_role):
        rv = by_role[role]
        rw = sum(1 for x in rv if x["win"])
        rn = len(rv)
        r_raters = len({x["rater_id_anon"] for x in rv})
        rlo, rhi = wilson_ci(rw, rn)
        lines.append(
            f"| {role} | {r_raters} | {rw}/{rn} | {100.0 * rw / rn:.1f}% | "
            f"{100.0 * rlo:.1f}% – {100.0 * rhi:.1f}% |"
        )

    if llm_verdicts is not None:
        overlap = sorted(pid for pid in human_maj if pid in llm_verdicts)
        h_labels = [human_maj[pid] for pid in overlap]
        l_labels = [llm_verdicts[pid] for pid in overlap]
        h_skill = sum(1 for x in h_labels if x == "skill")
        l_skill = sum(1 for x in l_labels if x == "skill")
        kappa, p_o, p_e = cohens_kappa(h_labels, l_labels)

        lines += [
            "",
            "## İnsan vs LLM Jüri Karşılaştırması",
            "",
            "| Metrik | İnsan (Çoğunluk) | LLM Jüri |",
            "|---|---:|---:|",
            f"| Ortak çift sayısı | {len(overlap)} | {len(overlap)} |",
            f"| Skill kazanma | {h_skill}/{len(overlap)} ({(100.0 * h_skill / len(overlap)) if overlap else 0.0:.1f}%) | "
            f"{l_skill}/{len(overlap)} ({(100.0 * l_skill / len(overlap)) if overlap else 0.0:.1f}%) |",
            "",
            f"- **Ham uyum ($p_o$):** {100.0 * p_o:.1f}%",
            f"- **Şans uyumu ($p_e$):** {100.0 * p_e:.1f}%",
            f"- **Cohen's κ (kappa):** **{kappa:.4f}** ({_kappa_interpretation(kappa)})",
        ]

    return "\n".join(lines)


def score_human(
    csv_dir: pathlib.Path,
    key_path: pathlib.Path,
    llm_summary_path: pathlib.Path | None = None,
    out_md: pathlib.Path | None = None,
) -> str:
    """Run full human scoring pipeline and optionally write Markdown report."""
    key = load_key(key_path)
    votes = load_human_votes(csv_dir, key)
    llm_verdicts = load_llm_verdicts(llm_summary_path, key) if llm_summary_path else None
    report = build_report(votes, key, llm_verdicts)
    if out_md is not None:
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text(report + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for score_human."""
    parser = argparse.ArgumentParser(description="Score blind human A/B CSVs and compare with LLM verdicts.")
    parser.add_argument("--csv-dir", required=True, help="Directory containing human rater .csv files")
    parser.add_argument("--key", required=True, help="Path to key.json mapping pair_id -> skill side")
    parser.add_argument("--llm-summary", help="Optional LLM results JSON or verdicts directory")
    parser.add_argument("--out-md", help="Optional output path for Markdown report")
    args = parser.parse_args(argv)

    report = score_human(
        csv_dir=pathlib.Path(args.csv_dir),
        key_path=pathlib.Path(args.key),
        llm_summary_path=pathlib.Path(args.llm_summary) if args.llm_summary else None,
        out_md=pathlib.Path(args.out_md) if args.out_md else None,
    )
    try:  # Turkish report text must not crash on Windows consoles that default to cp1252/cp1254
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
