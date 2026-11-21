#!/usr/bin/env python3
"""Generate an offline blind A/B human evaluation kit from a benchmark run.

Usage:
    python bench/human/make_human_kit.py --run-dir <bench/runs/runX> --out-dir <kit_dir> [--seed 42]

Reads <run_dir>/pairs.json and copies A/B media from <run_dir>/pairs/ into <out_dir>/media/.
Never copies key.json (or any answer key) into <out_dir>, preserving blind evaluation.
"""

import argparse
import json
import pathlib
import random
import shutil
from typing import Any

CRITERIA = [
    ("c1", "1. İlk izlenim", "Görsel çekicilik, ilk bakışta kalite ve güven hissi"),
    ("c2", "2. Hiyerarşi & okunabilirlik", "Tipografi, kontrast, odak noktası ve taranabilirlik"),
    ("c3", "3. Marka/mood uyumu", "Renk, üslup ve brief atmosferiyle tutarlılık"),
    ("c4", "4. İçerik & işlevsellik", "Bileşenlerin amacı karşılaması, gerçekçi ve faydalı içerik"),
    ("c5", "5. Durumlar & geri bildirim", "Boş/hata/yükleme/etkileşim durumları ve netlik"),
    ("c6", "6. Hareket & akıcılık", "Geçişler, filmstrip/animasyon kalitesi ve görsel ritim"),
]

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
MOTION_EXTS = {".gif", ".mp4", ".webm"}
KEY_NAMES = {"key.json", "key_do_not_open.json", "pair_map_do_not_open.json", "page_key.json"}
SENSITIVE_FIELDS = {"skill", "noskill", "arm", "truth", "key", "winner_arm", "expected"}


def _load_pairs(run_dir: pathlib.Path) -> list[dict[str, Any]]:
    """Load and normalize pairs.json into a list of pair dicts."""
    pairs_path = run_dir / "pairs.json"
    if not pairs_path.is_file():
        raise FileNotFoundError(f"pairs.json not found in {run_dir}")
    raw = json.loads(pairs_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        if "pairs" in raw and isinstance(raw["pairs"], list):
            items = raw["pairs"]
        else:
            items = []
            for k, v in raw.items():
                if isinstance(v, dict):
                    entry = dict(v)
                    entry.setdefault("pair_id", str(k))
                    items.append(entry)
    elif isinstance(raw, list):
        items = [dict(x) for x in raw if isinstance(x, dict)]
    else:
        raise ValueError("Unsupported pairs.json structure")

    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(items, 1):
        pid = str(item.get("pair_id") or item.get("id") or f"pair_{idx:03d}")
        normalized.append({"pair_id": pid, "raw": item})
    return normalized


def _resolve_candidate_path(run_dir: pathlib.Path, rel_or_abs: str) -> pathlib.Path | None:
    """Resolve a media path relative to run_dir or run_dir/pairs."""
    p = pathlib.Path(rel_or_abs)
    if p.is_absolute() and p.is_file():
        return p
    for base in (run_dir, run_dir / "pairs"):
        cand = base / p
        if cand.is_file():
            return cand
    return None


def _discover_side_media(run_dir: pathlib.Path, pair_id: str, side: str, raw_entry: dict[str, Any]) -> list[pathlib.Path]:
    """Find media files for one side (A or B) of a pair."""
    found: list[pathlib.Path] = []
    seen: set[pathlib.Path] = set()

    def add_file(path: pathlib.Path | None) -> None:
        if path is not None and path.is_file():
            resolved = path.resolve()
            if resolved.name.lower() in KEY_NAMES:
                return
            if resolved not in seen and (resolved.suffix.lower() in IMAGE_EXTS | MOTION_EXTS):
                seen.add(resolved)
                found.append(path)

    side_val = raw_entry.get(side) or raw_entry.get(side.lower())
    if isinstance(side_val, str):
        add_file(_resolve_candidate_path(run_dir, side_val))
    elif isinstance(side_val, dict):
        for k in ("contact_sheet", "contact-sheet", "filmstrip", "video", "gif", "image", "screenshot", "path"):
            v = side_val.get(k)
            if isinstance(v, str):
                add_file(_resolve_candidate_path(run_dir, v))
        extra = side_val.get("media")
        if isinstance(extra, list):
            for v in extra:
                if isinstance(v, str):
                    add_file(_resolve_candidate_path(run_dir, v))

    pairs_dir = run_dir / "pairs"
    # Directory layouts: pairs/<pair_id>/<side>/*
    side_dir = pairs_dir / pair_id / side
    if side_dir.is_dir():
        for child in sorted(side_dir.iterdir()):
            add_file(child)

    # Flat layouts inside pairs/<pair_id>/ or pairs/
    pair_subdir = pairs_dir / pair_id
    if pair_subdir.is_dir():
        for pat in (
            f"{side}.*",
            f"{side}-*.*",
            f"{side}_*.*",
        ):
            for child in sorted(pair_subdir.glob(pat)):
                add_file(child)

    if pairs_dir.is_dir():
        for pat in (
            f"{pair_id}-{side}.*",
            f"{pair_id}_{side}.*",
            f"{pair_id}-{side}-*.*",
            f"{pair_id}_{side}_*.*",
        ):
            for child in sorted(pairs_dir.glob(pat)):
                add_file(child)

    return found


def _copy_side_media(
    files: list[pathlib.Path], out_dir: pathlib.Path, pair_id: str, side: str
) -> dict[str, Any]:
    """Copy discovered media files into out_dir/media/<pair_id>/<side>/ and classify them."""
    dest_dir = out_dir / "media" / pair_id / side
    dest_dir.mkdir(parents=True, exist_ok=True)

    contact_sheet: str | None = None
    filmstrip: str | None = None
    motion: str | None = None
    all_images: list[str] = []

    for src in files:
        dst = dest_dir / src.name
        shutil.copy2(src, dst)
        rel = f"media/{pair_id}/{side}/{src.name}"
        lname = src.name.lower()
        ext = src.suffix.lower()

        if ext in {".mp4", ".webm"} and motion is None:
            motion = rel
        elif ext == ".gif" and motion is None:
            motion = rel
        elif "filmstrip" in lname and filmstrip is None:
            filmstrip = rel
        elif "contact" in lname and contact_sheet is None:
            contact_sheet = rel

        if ext in IMAGE_EXTS:
            all_images.append(rel)

    if contact_sheet is None and all_images:
        contact_sheet = next((img for img in all_images if img != filmstrip), all_images[0])

    return {
        "contact_sheet": contact_sheet,
        "filmstrip": filmstrip,
        "motion": motion,
        "images": all_images,
    }


def _safe_pair_meta(raw_entry: dict[str, Any], pair_id: str) -> dict[str, str]:
    """Extract only non-identifying display metadata for a pair."""
    meta: dict[str, str] = {"pair_id": pair_id}
    for field in ("title", "brief", "prompt", "mood", "category"):
        val = raw_entry.get(field)
        if isinstance(val, str) and val.strip():
            # Guard against accidental arm leakage in metadata strings
            lowered = val.lower()
            if "noskill" not in lowered and field not in SENSITIVE_FIELDS:
                meta[field] = val.strip()
    return meta


def _render_html(pairs_payload: list[dict[str, Any]], seed: int) -> str:
    """Render the self-contained offline human rating web app."""
    kit_id = f"ui_human_kit_s{seed}_{len(pairs_payload)}"
    payload_json = json.dumps(pairs_payload, ensure_ascii=False).replace("</", "<\\/")
    criteria_json = json.dumps(CRITERIA, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Kör A/B İnsan Değerlendirme Kiti</title>
  <style>
    :root {{
      --bg: #0f172a;
      --panel: #1e293b;
      --panel-2: #0b1220;
      --border: #334155;
      --text: #f8fafc;
      --muted: #94a3b8;
      --accent: #38bdf8;
      --accent-2: #22c55e;
      --warn: #f59e0b;
      --radius: 10px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.45;
    }}
    header {{
      position: sticky;
      top: 0;
      z-index: 20;
      background: rgba(15, 23, 42, 0.95);
      border-bottom: 1px solid var(--border);
      padding: 12px 20px;
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
    }}
    .brand {{ font-weight: 700; font-size: 16px; }}
    .privacy-badge {{
      font-size: 12px;
      color: var(--accent-2);
      background: rgba(34, 197, 94, 0.12);
      border: 1px solid rgba(34, 197, 94, 0.35);
      padding: 3px 8px;
      border-radius: 999px;
    }}
    .container {{ max-width: 1440px; margin: 0 auto; padding: 16px 20px 60px; }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 16px;
      margin-bottom: 16px;
    }}
    .profile-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
    }}
    label {{ display: block; font-size: 13px; color: var(--muted); margin-bottom: 4px; }}
    select, input[type="text"], textarea {{
      width: 100%;
      background: var(--panel-2);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 14px;
    }}
    .pair-nav {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }}
    .pills {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .pill {{
      border: 1px solid var(--border);
      background: var(--panel-2);
      color: var(--muted);
      border-radius: 6px;
      padding: 4px 10px;
      font-size: 12px;
      cursor: pointer;
    }}
    .pill.active {{ border-color: var(--accent); color: var(--text); font-weight: 700; }}
    .pill.done {{ border-color: var(--accent-2); color: var(--accent-2); }}
    .btn {{
      background: var(--panel-2);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 14px;
      font-size: 14px;
      cursor: pointer;
    }}
    .btn:hover {{ border-color: var(--accent); }}
    .btn-primary {{
      background: var(--accent);
      color: #082f49;
      border-color: var(--accent);
      font-weight: 700;
    }}
    .btn-success {{
      background: var(--accent-2);
      color: #052e16;
      border-color: var(--accent-2);
      font-weight: 700;
    }}
    .tabs {{ display: flex; gap: 8px; margin-bottom: 12px; }}
    .tab-btn.active {{ background: var(--accent); color: #082f49; border-color: var(--accent); font-weight: 700; }}
    .ab-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }}
    @media (max-width: 900px) {{ .ab-grid {{ grid-template-columns: 1fr; }} }}
    .side-box {{
      background: var(--panel-2);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 12px;
    }}
    .side-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
      font-weight: 700;
    }}
    .media-frame {{
      width: 100%;
      max-height: 540px;
      overflow: auto;
      border-radius: 6px;
      border: 1px solid var(--border);
      background: #020617;
      text-align: center;
    }}
    .media-frame img, .media-frame video {{
      max-width: 100%;
      height: auto;
      display: block;
      margin: 0 auto;
      cursor: zoom-in;
    }}
    .crit-table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 8px;
    }}
    .crit-table th, .crit-table td {{
      border-bottom: 1px solid var(--border);
      padding: 10px 8px;
      text-align: left;
      vertical-align: middle;
    }}
    .crit-desc {{ font-size: 12px; color: var(--muted); }}
    .scale-group {{ display: inline-flex; gap: 4px; }}
    .scale-btn {{
      width: 30px;
      height: 30px;
      border-radius: 6px;
      border: 1px solid var(--border);
      background: var(--panel-2);
      color: var(--text);
      cursor: pointer;
      font-size: 13px;
    }}
    .scale-btn.selected {{
      background: var(--accent);
      color: #082f49;
      border-color: var(--accent);
      font-weight: 700;
    }}
    .winner-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      margin-top: 14px;
    }}
    .winner-btn {{
      padding: 10px 20px;
      font-weight: 700;
      border-radius: 8px;
      border: 2px solid var(--border);
      background: var(--panel-2);
      color: var(--text);
      cursor: pointer;
    }}
    .winner-btn.selected {{
      border-color: var(--accent-2);
      background: rgba(34, 197, 94, 0.2);
      color: #86efac;
    }}
    .modal {{
      display: none;
      position: fixed;
      inset: 0;
      z-index: 50;
      background: rgba(2, 6, 23, 0.92);
      padding: 20px;
      overflow: auto;
    }}
    .modal.open {{ display: flex; flex-direction: column; align-items: center; }}
    .modal-bar {{
      display: flex;
      gap: 10px;
      margin-bottom: 12px;
      align-items: center;
    }}
    .modal img, .modal video {{ max-width: 96vw; max-height: 86vh; border-radius: 8px; }}
  </style>
</head>
<body>
  <header>
    <div>
      <span class="brand">Kör A/B İnsan Değerlendirme Kiti</span>
      <span class="privacy-badge">Gizlilik: İsim / e-posta / kimlik toplanmaz</span>
    </div>
    <div style="display:flex; gap:10px; align-items:center;">
      <span id="progressText" style="font-size:13px; color:var(--muted);">0 / 0 tamamlandı</span>
      <button class="btn btn-success" id="downloadCsvBtn" type="button">CSV İndir</button>
    </div>
  </header>

  <main class="container">
    <section class="card">
      <div class="profile-grid">
        <div>
          <label for="roleSelect">Rolünüz (isteğe bağlı)</label>
          <select id="roleSelect">
            <option value="">Belirtmek istemiyorum</option>
            <option value="Tasarımcı">Tasarımcı</option>
            <option value="Geliştirici">Geliştirici</option>
            <option value="Son kullanıcı">Son kullanıcı</option>
          </select>
        </div>
        <div>
          <label for="visionSelect">Göz / okuma durumu (isteğe bağlı)</label>
          <select id="visionSelect">
            <option value="">Normal / belirtilmedi</option>
            <option value="Gözlük / lens">Gözlük / lens kullanıyorum</option>
            <option value="Büyük yazı tercihi">Büyük yazı / yüksek kontrast tercihi</option>
            <option value="Renk görme farklılığı">Renk görme farklılığı</option>
          </select>
        </div>
        <div>
          <label for="raterIdBox">Anonim oturum kodu (rastgele)</label>
          <input id="raterIdBox" type="text" readonly />
        </div>
      </div>
    </section>

    <section class="card pair-nav">
      <div style="display:flex; gap:8px; align-items:center;">
        <button class="btn" id="prevBtn" type="button">← Önceki</button>
        <button class="btn" id="nextBtn" type="button">Sonraki →</button>
        <strong id="pairHeading" style="margin-left:8px;"></strong>
      </div>
      <div class="pills" id="pairPills"></div>
    </section>

    <section class="card" id="pairMetaBox" style="display:none;"></section>

    <section class="card">
      <div class="tabs">
        <button class="btn tab-btn active" id="tabContact" type="button">Contact Sheet</button>
        <button class="btn tab-btn" id="tabFilmstrip" type="button">Filmstrip / Hareket</button>
      </div>
      <div class="ab-grid">
        <div class="side-box">
          <div class="side-header">
            <span>Seçenek A</span>
            <button class="btn" type="button" onclick="openZoom('A')">Büyüt</button>
          </div>
          <div class="media-frame" id="mediaA"></div>
        </div>
        <div class="side-box">
          <div class="side-header">
            <span>Seçenek B</span>
            <button class="btn" type="button" onclick="openZoom('B')">Büyüt</button>
          </div>
          <div class="media-frame" id="mediaB"></div>
        </div>
      </div>
    </section>

    <section class="card">
      <h3 style="margin-top:0;">6 Kriter Puanlaması (1 = Zayıf, 5 = Mükemmel)</h3>
      <table class="crit-table">
        <thead>
          <tr>
            <th>Kriter</th>
            <th>A Puanı (1–5)</th>
            <th>B Puanı (1–5)</th>
          </tr>
        </thead>
        <tbody id="criteriaBody"></tbody>
      </table>

      <div class="winner-row">
        <strong>Genel Tercih (Zorunlu):</strong>
        <button class="winner-btn" id="winABtn" type="button">A Daha İyi</button>
        <button class="winner-btn" id="winBBtn" type="button">B Daha İyi</button>
      </div>

      <div style="margin-top:12px;">
        <label for="reasonInput">Kısa gerekçe (isteğe bağlı, neden bu seçimi yaptınız?)</label>
        <input id="reasonInput" type="text" placeholder="Örn: A daha okunabilir ve hiyerarşisi net..." />
      </div>
    </section>
  </main>

  <div class="modal" id="zoomModal" role="dialog" aria-modal="true">
    <div class="modal-bar">
      <strong id="zoomLabel"></strong>
      <button class="btn" type="button" onclick="switchZoomSide()">A / B Değiştir</button>
      <button class="btn" type="button" onclick="closeZoom()">Kapat (Esc)</button>
    </div>
    <div id="zoomContent"></div>
  </div>

  <script>
    const KIT_ID = {json.dumps(kit_id)};
    const PAIRS = {payload_json};
    const CRITERIA = {criteria_json};
    const STORAGE_KEY = "human_kit_state_" + KIT_ID;

    function makeAnonId() {{
      if (window.crypto && crypto.getRandomValues) {{
        const arr = new Uint32Array(2);
        crypto.getRandomValues(arr);
        return "r_" + arr[0].toString(16) + arr[1].toString(16).slice(0, 4);
      }}
      return "r_" + Math.random().toString(16).slice(2, 10);
    }}

    function loadState() {{
      try {{
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) return JSON.parse(raw);
      }} catch (e) {{}}
      return {{
        rater_id_anon: makeAnonId(),
        role: "",
        vision_note: "",
        currentIndex: 0,
        activeTab: "contact",
        ratings: {{}}
      }};
    }}

    const state = loadState();
    if (!state.rater_id_anon) state.rater_id_anon = makeAnonId();
    if (!state.ratings) state.ratings = {{}};

    function saveState() {{
      try {{ localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }} catch (e) {{}}
    }}

    function getRating(pid) {{
      if (!state.ratings[pid]) {{
        state.ratings[pid] = {{ winner: "", a: {{}}, b: {{}}, reason: "" }};
      }}
      return state.ratings[pid];
    }}

    function isPairComplete(pid) {{
      const r = state.ratings[pid];
      if (!r || (r.winner !== "A" && r.winner !== "B")) return false;
      for (const [cid] of CRITERIA) {{
        if (!r.a[cid] || !r.b[cid]) return false;
      }}
      return true;
    }}

    function renderMediaSide(side, pair) {{
      const m = pair[side];
      const el = document.getElementById("media" + side);
      el.innerHTML = "";
      if (state.activeTab === "filmstrip") {{
        if (m.motion) {{
          if (m.motion.endsWith(".gif")) {{
            const img = document.createElement("img");
            img.src = m.motion;
            img.alt = pair.pair_id + " " + side + " motion";
            img.onclick = () => openZoom(side);
            el.appendChild(img);
          }} else {{
            const vid = document.createElement("video");
            vid.src = m.motion;
            vid.controls = true;
            vid.loop = true;
            vid.muted = true;
            el.appendChild(vid);
          }}
          return;
        }}
        if (m.filmstrip) {{
          const img = document.createElement("img");
          img.src = m.filmstrip;
          img.alt = pair.pair_id + " " + side + " filmstrip";
          img.onclick = () => openZoom(side);
          el.appendChild(img);
          return;
        }}
        el.innerHTML = '<div style="padding:24px; color:var(--muted);">Bu seçenek için filmstrip/hareket medyası yok.</div>';
        return;
      }}
      if (m.contact_sheet) {{
        const img = document.createElement("img");
        img.src = m.contact_sheet;
        img.alt = pair.pair_id + " " + side + " contact sheet";
        img.onclick = () => openZoom(side);
        el.appendChild(img);
      }} else {{
        el.innerHTML = '<div style="padding:24px; color:var(--muted);">Görsel bulunamadı.</div>';
      }}
    }}

    function render() {{
      if (!PAIRS.length) return;
      if (state.currentIndex < 0) state.currentIndex = 0;
      if (state.currentIndex >= PAIRS.length) state.currentIndex = PAIRS.length - 1;
      const pair = PAIRS[state.currentIndex];
      const rating = getRating(pair.pair_id);

      document.getElementById("roleSelect").value = state.role || "";
      document.getElementById("visionSelect").value = state.vision_note || "";
      document.getElementById("raterIdBox").value = state.rater_id_anon;
      document.getElementById("pairHeading").textContent = `Çift ${{state.currentIndex + 1}} / ${{PAIRS.length}} (${{pair.pair_id}})`;

      const doneCount = PAIRS.filter(p => isPairComplete(p.pair_id)).length;
      document.getElementById("progressText").textContent = `${{doneCount}} / ${{PAIRS.length}} tamamlandı`;

      const metaBox = document.getElementById("pairMetaBox");
      const metaParts = [];
      if (pair.title) metaParts.push("<strong>" + escapeHtml(pair.title) + "</strong>");
      if (pair.brief) metaParts.push(escapeHtml(pair.brief));
      if (pair.prompt) metaParts.push(escapeHtml(pair.prompt));
      if (metaParts.length) {{
        metaBox.style.display = "block";
        metaBox.innerHTML = metaParts.join(" — ");
      }} else {{
        metaBox.style.display = "none";
      }}

      const pills = document.getElementById("pairPills");
      pills.innerHTML = "";
      PAIRS.forEach((p, idx) => {{
        const b = document.createElement("button");
        b.type = "button";
        b.className = "pill" + (idx === state.currentIndex ? " active" : "") + (isPairComplete(p.pair_id) ? " done" : "");
        b.textContent = String(idx + 1);
        b.onclick = () => {{ state.currentIndex = idx; saveState(); render(); }};
        pills.appendChild(b);
      }});

      const hasFilmstrip = !!(pair.A.filmstrip || pair.B.filmstrip || pair.A.motion || pair.B.motion);
      document.getElementById("tabFilmstrip").disabled = !hasFilmstrip;
      if (!hasFilmstrip && state.activeTab === "filmstrip") state.activeTab = "contact";
      document.getElementById("tabContact").classList.toggle("active", state.activeTab === "contact");
      document.getElementById("tabFilmstrip").classList.toggle("active", state.activeTab === "filmstrip");

      renderMediaSide("A", pair);
      renderMediaSide("B", pair);

      const tbody = document.getElementById("criteriaBody");
      tbody.innerHTML = "";
      CRITERIA.forEach(([cid, title, desc]) => {{
        const tr = document.createElement("tr");
        const tdLabel = document.createElement("td");
        tdLabel.innerHTML = `<div><strong>${{escapeHtml(title)}}</strong></div><div class="crit-desc">${{escapeHtml(desc)}}</div>`;
        tr.appendChild(tdLabel);

        ["a", "b"].forEach(sideKey => {{
          const td = document.createElement("td");
          const grp = document.createElement("div");
          grp.className = "scale-group";
          for (let score = 1; score <= 5; score++) {{
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "scale-btn" + (rating[sideKey][cid] === score ? " selected" : "");
            btn.textContent = String(score);
            btn.onclick = () => {{
              rating[sideKey][cid] = score;
              saveState();
              render();
            }};
            grp.appendChild(btn);
          }}
          td.appendChild(grp);
          tr.appendChild(td);
        }});
        tbody.appendChild(tr);
      }});

      document.getElementById("winABtn").classList.toggle("selected", rating.winner === "A");
      document.getElementById("winBBtn").classList.toggle("selected", rating.winner === "B");
      document.getElementById("reasonInput").value = rating.reason || "";
    }}

    function escapeHtml(s) {{
      return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }}

    let zoomSide = "A";
    function openZoom(side) {{
      zoomSide = side;
      const pair = PAIRS[state.currentIndex];
      const m = pair[side];
      const src = (state.activeTab === "filmstrip" && (m.motion || m.filmstrip)) ? (m.motion || m.filmstrip) : m.contact_sheet;
      if (!src) return;
      document.getElementById("zoomLabel").textContent = `${{pair.pair_id}} — Seçenek ${{side}}`;
      const content = document.getElementById("zoomContent");
      content.innerHTML = "";
      if (src.endsWith(".mp4") || src.endsWith(".webm")) {{
        const vid = document.createElement("video");
        vid.src = src;
        vid.controls = true;
        vid.autoplay = true;
        vid.loop = true;
        content.appendChild(vid);
      }} else {{
        const img = document.createElement("img");
        img.src = src;
        content.appendChild(img);
      }}
      document.getElementById("zoomModal").classList.add("open");
    }}
    function switchZoomSide() {{ openZoom(zoomSide === "A" ? "B" : "A"); }}
    function closeZoom() {{ document.getElementById("zoomModal").classList.remove("open"); }}
    document.addEventListener("keydown", e => {{ if (e.key === "Escape") closeZoom(); }});

    function csvCell(v) {{
      const s = String(v ?? "");
      if (/[",\\r\\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
      return s;
    }}

    function buildCsv() {{
      const headers = [
        "rater_id_anon", "role", "vision_note", "pair_id", "winner",
        "a_c1", "a_c2", "a_c3", "a_c4", "a_c5", "a_c6",
        "b_c1", "b_c2", "b_c3", "b_c4", "b_c5", "b_c6", "reason"
      ];
      const rows = [headers.join(",")];
      PAIRS.forEach(p => {{
        const r = state.ratings[p.pair_id] || {{ winner: "", a: {{}}, b: {{}}, reason: "" }};
        const row = [
          state.rater_id_anon,
          state.role || "",
          state.vision_note || "",
          p.pair_id,
          r.winner || "",
          r.a.c1 || "", r.a.c2 || "", r.a.c3 || "", r.a.c4 || "", r.a.c5 || "", r.a.c6 || "",
          r.b.c1 || "", r.b.c2 || "", r.b.c3 || "", r.b.c4 || "", r.b.c5 || "", r.b.c6 || "",
          r.reason || ""
        ];
        rows.push(row.map(csvCell).join(","));
      }});
      return "\\ufeff" + rows.join("\\r\\n") + "\\r\\n";
    }}

    document.getElementById("roleSelect").onchange = e => {{ state.role = e.target.value; saveState(); }};
    document.getElementById("visionSelect").onchange = e => {{ state.vision_note = e.target.value; saveState(); }};
    document.getElementById("prevBtn").onclick = () => {{ if (state.currentIndex > 0) {{ state.currentIndex--; saveState(); render(); }} }};
    document.getElementById("nextBtn").onclick = () => {{ if (state.currentIndex < PAIRS.length - 1) {{ state.currentIndex++; saveState(); render(); }} }};
    document.getElementById("tabContact").onclick = () => {{ state.activeTab = "contact"; saveState(); render(); }};
    document.getElementById("tabFilmstrip").onclick = () => {{ state.activeTab = "filmstrip"; saveState(); render(); }};
    document.getElementById("winABtn").onclick = () => {{ getRating(PAIRS[state.currentIndex].pair_id).winner = "A"; saveState(); render(); }};
    document.getElementById("winBBtn").onclick = () => {{ getRating(PAIRS[state.currentIndex].pair_id).winner = "B"; saveState(); render(); }};
    document.getElementById("reasonInput").oninput = e => {{ getRating(PAIRS[state.currentIndex].pair_id).reason = e.target.value; saveState(); }};
    document.getElementById("downloadCsvBtn").onclick = () => {{
      const blob = new Blob([buildCsv()], {{ type: "text/csv;charset=utf-8;" }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `human_votes_${{state.rater_id_anon}}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }};

    render();
  </script>
</body>
</html>
"""


def build_human_kit(run_dir: pathlib.Path, out_dir: pathlib.Path, seed: int = 42) -> pathlib.Path:
    """Build the blind offline human evaluation kit in out_dir and return index.html path."""
    pairs = _load_pairs(run_dir)
    if not pairs:
        raise ValueError(f"No pairs found in {run_dir / 'pairs.json'}")

    out_dir.mkdir(parents=True, exist_ok=True)
    shuffled = list(pairs)
    random.Random(seed).shuffle(shuffled)

    payload: list[dict[str, Any]] = []
    for entry in shuffled:
        pid = entry["pair_id"]
        raw = entry["raw"]
        a_files = _discover_side_media(run_dir, pid, "A", raw)
        b_files = _discover_side_media(run_dir, pid, "B", raw)
        pair_obj = _safe_pair_meta(raw, pid)
        pair_obj["A"] = _copy_side_media(a_files, out_dir, pid, "A")
        pair_obj["B"] = _copy_side_media(b_files, out_dir, pid, "B")
        payload.append(pair_obj)

    index_path = out_dir / "index.html"
    index_path.write_text(_render_html(payload, seed), encoding="utf-8")
    return index_path


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for make_human_kit."""
    parser = argparse.ArgumentParser(description="Build an offline blind A/B human rating kit.")
    parser.add_argument("--run-dir", required=True, help="Benchmark run directory containing pairs.json and pairs/")
    parser.add_argument("--out-dir", required=True, help="Output directory for the static offline kit")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for shuffling pair order (default: 42)")
    args = parser.parse_args(argv)

    index_path = build_human_kit(pathlib.Path(args.run_dir), pathlib.Path(args.out_dir), seed=args.seed)
    print(f"Human evaluation kit created: {index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
