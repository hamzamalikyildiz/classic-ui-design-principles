# Kovan CV — Demo Uygulaması (`examples/app-demo`)

Multi-screen Vite + React + TypeScript + Tailwind v4 + shadcn (`oklch`) + MSW demo uygulaması.
`scripts/uitools.py` ve `scripts/render.py` için gerçek uygulama test yatağıdır: 6 bilinçli yerleştirilmiş hata (`// DELIBERATE DEFECT #1..#6`) ve 4 yanlış-alarm tuzağı içerir.

## Kurulum (3 Komut)

```bash
cd examples/app-demo
npm install
npm run dev
```

## Ekranlar & Akış

- `/login`: Oturum açma (cookie + `localStorage`)
- `/cv`: 4 kanonik başvuru (`seed.json`), filtre çipleri, durumlar (`default`, `empty`, `loading`, `long-loading`, `error`)
- `/cv/app_01`: `ScoreCard` + `<ScoreBars />`, AI önerileri, mülakat soruları, 30s AI analizi simülasyonu
- `/settings`: Profil ve tema tercihleri

## Denetim Örnekleri

```bash
python scripts/uitools.py audit --route examples/app-demo/src/pages/CvDetailPage.tsx --root examples/app-demo --css examples/app-demo/src/index.css --mood trust
python scripts/render.py --routes examples/app-demo/routes.json --out-dir shots
```
