#!/usr/bin/env python3
"""Make one independent blind judge set per persona from the pairs built by build_pairs.py.

    python3 bench/make_judge_sets.py <workdir> [--seed 7]

For each persona in judges.json: shuffles pair order, randomly swaps A/B for every pair, and writes
<workdir>/judge_<id>/ciftN-{A,B}-K.png, <workdir>/maps/MAP_<id>.json (never shown to judges) and
<workdir>/judge_tasks/<id>.txt (the full judge prompt). Each judge sees the same pairs in a different
order and with different A/B placement, so position and order effects average out.
"""
import argparse, json, pathlib, random, shutil

HERE = pathlib.Path(__file__).resolve().parent
ap = argparse.ArgumentParser(); ap.add_argument('work'); ap.add_argument('--seed', type=int, default=7); a = ap.parse_args()
W = pathlib.Path(a.work)
pm = json.load(open(W / 'PAIR_MAP_DO_NOT_OPEN.json')); judges = json.load(open(HERE / 'judges.json'))
base = (HERE / 'JUDGE_PROMPT.md').read_text(encoding='utf-8')
(W / 'maps').mkdir(exist_ok=True); (W / 'judge_tasks').mkdir(exist_ok=True)
for j in judges:
    rnd = random.Random(f'{a.seed}-{j["id"]}')
    ids = list(pm); rnd.shuffle(ids)
    d = W / f'judge_{j["id"]}'
    if d.exists(): shutil.rmtree(d)
    d.mkdir(); mp = {}
    for n, orig in enumerate(ids, 1):
        swap = rnd.random() < 0.5
        src = {'A': 'B', 'B': 'A'} if swap else {'A': 'A', 'B': 'B'}   # new side -> original side
        for side in 'AB':
            for f in sorted((W / 'judge').glob(f'{orig}-{src[side]}-*.png')):
                shutil.copy(f, d / f'cift{n}-{side}-{f.stem.rsplit("-", 1)[1]}.png')
        v = pm[orig]; sk = v['skill']
        mp[f'cift{n}'] = {'orig': orig, 'skill': ({'A': 'B', 'B': 'A'}[sk] if swap else sk),
                          'mood': v['mood'], 'brief': v['brief'], 'rep': v['rep']}
    json.dump(mp, open(W / 'maps' / f'MAP_{j["id"]}.json', 'w'), indent=1)
    out = W / f'judge_{j["id"]}.txt'
    prompt = (f'Sen {j["name"]}, {j["age"]} yaşındasın. {j["persona"]}\n\n'
              f'Sayfaları BU kişinin gözüyle, kendi zevkinle değerlendir.\n\n{base}\n\n'
              f'Dosyalar: {d}\\ klasöründe. Çift N için A = ciftN-A-1.png, ciftN-A-2.png (varsa -3.png), B = ciftN-B-*.png '
              f'(aynı uzun sayfanın üstten alta parçaları). Çift sayısı: {len(ids)}. Her PNG\'yi Read aracıyla aç. '
              f'{W}\\ klasöründeki başka hiçbir dosyayı (özellikle MAP, KEY, raw, anon, pairs, metrics, maps adlı olanları) ve '
              f'skill klasörünü okuma.\n\n'
              f'Sonuçları {out} dosyasına, HER ÇİFTTEN SONRA o satırı ekleyerek yaz (bağlam kaybolursa iş kaybolmasın). '
              f'Satır formatı aynen: `cift3: A | 4 | tek cümle gerekçe | A 8/8/7/9 B 7/6/8/7` '
              f'(tercih, güven 1-5, gerekçe, sonra dört kriter için A ve B puanları). Beraberlik yok. '
              f'En sonda sadece dosya yolunu yaz.')
    (W / 'judge_tasks' / f'{j["id"]}.txt').write_text(prompt, encoding='utf-8')
print(f'{len(judges)} judge sets, {len(pm)} pairs each; prompts in {W / "judge_tasks"}')
