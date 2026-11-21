#!/usr/bin/env python3
"""Make one independent blind judge set per persona from the pairs built by build_pairs.py.

    python3 bench/make_judge_sets.py <workdir> [--seed 7] [--app]

For each persona in judges.json: shuffles pair order, randomly swaps A/B for every pair, and writes
<workdir>/judge_<id>/ciftN-{A,B}-*.png, <workdir>/maps/MAP_<id>.json (never shown to judges) and
<workdir>/judge_tasks/<id>.txt (the full judge prompt). Each judge sees the same pairs in a different
order and with different A/B placement, so position and order effects average out.
"""
import argparse, json, pathlib, random, re, shutil

HERE = pathlib.Path(__file__).resolve().parent


def load_judge_prompt(app_mode=False):
    """Load JUDGE_PROMPT.md formatted for either 4-criterion page mode or 6-criterion app mode."""
    raw = (HERE / 'JUDGE_PROMPT.md').read_text(encoding='utf-8')
    if app_mode:
        return raw.replace('<!-- APP_MODE -->\n', '').strip()
    # Keep 4-criterion page instructions cleanly without app-only criteria 5-6
    lines = []
    skip_app = False
    for ln in raw.splitlines():
        if ln.strip() == '<!-- APP_MODE -->':
            skip_app = True
            continue
        if skip_app and ln.startswith('Çıktı formatı'):
            skip_app = False
        if skip_app:
            continue
        if ln.startswith('- Uygulama modu (`--app`'):
            continue
        if ln.startswith('- Tek sayfa modu (4 kriter):'):
            ln = ln.replace('- Tek sayfa modu (4 kriter): ', '')
        if ln.startswith('- `A x/... B y/...`:'):
            ln = '- `A x/x/x/x B y/y/y/y`: yukarıdaki 4 kriter için 1-10 puanlar'
        lines.append(ln)
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('work')
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--app', action='store_true',
                    help='use 6-criterion app prompt and reference contact-sheet.png + filmstrip.png')
    a = ap.parse_args(argv)

    W = pathlib.Path(a.work)
    with open(W / 'PAIR_MAP_DO_NOT_OPEN.json', encoding='utf-8') as fh:
        pm = json.load(fh)
    with open(HERE / 'judges.json', encoding='utf-8') as fh:
        judges = json.load(fh)

    base = load_judge_prompt(app_mode=a.app)
    (W / 'maps').mkdir(exist_ok=True)
    (W / 'judge_tasks').mkdir(exist_ok=True)

    for idx, j in enumerate(judges):
        rnd = random.Random(f'{a.seed}-{j["id"]}')
        ids = list(pm)
        rnd.shuffle(ids)
        pair_pattern = [True, False] if idx % 2 == 0 else [False, True]
        flags = (pair_pattern * ((len(ids) + 1) // 2))[:len(ids)]
        rnd.shuffle(flags)

        d = W / f'judge_{j["id"]}'
        if d.exists():
            shutil.rmtree(d)
        d.mkdir()
        mp = {}

        for n, (orig, focal_is_a) in enumerate(zip(ids, flags), 1):
            v = pm[orig]
            focal_orig = v.get('focal') or v.get('skill') or 'A'
            swap = (focal_orig == 'A') != focal_is_a
            src = {'A': 'B', 'B': 'A'} if swap else {'A': 'A', 'B': 'B'}  # new side -> original side
            for side in 'AB':
                prefix = f'{orig}-{src[side]}-'
                for f in sorted((W / 'judge').glob(f'{prefix}*.png')):
                    suffix = f.name[len(prefix):]
                    shutil.copy(f, d / f'cift{n}-{side}-{suffix}')

            if 'arm_a' in v and 'arm_b' in v:
                new_arm_a = v['arm_b'] if swap else v['arm_a']
                new_arm_b = v['arm_a'] if swap else v['arm_b']
                skill_side = 'A' if new_arm_a == 'skill' else ('B' if new_arm_b == 'skill' else None)
                mp[f'cift{n}'] = {
                    'orig': orig,
                    'skill': skill_side,
                    'arm_a': new_arm_a,
                    'arm_b': new_arm_b,
                    'focal': 'A' if focal_is_a else 'B',
                    'comparison': v.get('comparison', f'{new_arm_a}_vs_{new_arm_b}'),
                    'mood': v['mood'],
                    'brief': v['brief'],
                    'rep': v['rep'],
                }
            else:
                mp[f'cift{n}'] = {
                    'orig': orig,
                    'skill': ('A' if focal_is_a else 'B'),
                    'mood': v['mood'],
                    'brief': v['brief'],
                    'rep': v['rep'],
                }

        with open(W / 'maps' / f'MAP_{j["id"]}.json', 'w', encoding='utf-8') as fh:
            json.dump(mp, fh, indent=1, ensure_ascii=False)

        out = W / f'judge_{j["id"]}.txt'
        out.unlink(missing_ok=True)
        if a.app:
            files_desc = (
                f'Dosyalar: {d} klasöründe. Çift N için A tarafı = ciftN-A-contact-sheet.png (ekran × durum × viewport ızgarası) '
                f've varsa ciftN-A-filmstrip.png (hareket/sonuç mikro anı kareleri); B tarafı = ciftN-B-contact-sheet.png ve '
                f'varsa ciftN-B-filmstrip.png. Çift sayısı: {len(ids)}. Her PNG\'yi Read aracıyla aç.'
            )
            format_desc = (
                'Satır formatı aynen: `cift3: A | 4 | tek cümle Türkçe gerekçe | A 8/8/7/9/8/7 B 7/6/8/7/5/6` '
                '(tercih, güven 1-5, gerekçe, sonra altı kriter için A ve B puanları).'
            )
        else:
            files_desc = (
                f'Dosyalar: {d} klasöründe. Çift N için A = ciftN-A-1.png, ciftN-A-2.png (varsa -3.png), B = ciftN-B-*.png '
                f'(aynı uzun sayfanın üstten alta parçaları). Çift sayısı: {len(ids)}. Her PNG\'yi Read aracıyla aç.'
            )
            format_desc = (
                'Satır formatı aynen: `cift3: A | 4 | tek cümle Türkçe gerekçe | A 8/8/7/9 B 7/6/8/7` '
                '(tercih, güven 1-5, gerekçe, sonra dört kriter için A ve B puanları).'
            )

        prompt = (
            f'Sen {j["name"]}, {j["age"]} yaşındasın. {j["persona"]}\n\n'
            f'Sayfaları BU kişinin gözüyle, kendi zevkinle değerlendir.\n\n{base}\n\n'
            f'{files_desc} '
            f'{W} klasöründeki başka hiçbir dosyayı (özellikle MAP, KEY, raw, anon, pairs, metrics, maps, key, pairs.json adlı olanları) ve '
            f'skill klasörünü okuma.\n\n'
            f'Sonuçları {out} dosyasına, HER ÇİFTTEN SONRA o satırı ekleyerek yaz (bağlam kaybolursa iş kaybolmasın). '
            f'{format_desc} '
            f'Gerekçeyi mutlaka tek cümle ve Türkçe yaz. Beraberlik yok. '
            f'En sonda sadece dosya yolunu yaz.'
        )
        (W / 'judge_tasks' / f'{j["id"]}.txt').write_text(prompt, encoding='utf-8')
    print(f'{len(judges)} judge sets, {len(pm)} pairs each; prompts in {W / "judge_tasks"}')


if __name__ == '__main__':
    main()
