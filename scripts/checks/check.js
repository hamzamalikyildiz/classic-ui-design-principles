() => {
  const out = [], vw = innerWidth;
  const where = e => { const c = (e.className && e.className.baseVal === undefined ? String(e.className) : '').trim().split(/\s+/).slice(0, 3).join('.');
                       return e.tagName.toLowerCase() + (c ? '.' + c : ''); };
  const vis = e => { const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
                     return r.width > 0 && r.height > 0 && cs.display !== 'none' && cs.visibility !== 'hidden'; };
  const mediaTags = new Set(['svg', 'img', 'canvas', 'video', 'iframe', 'input', 'textarea', 'select']);
  const hasDirectText = c => [...c.childNodes].some(nd => nd.nodeType === 3 && nd.textContent.trim());
  const contentBottom = container => {
    let last = container.getBoundingClientRect().top, n = 0;
    if (hasDirectText(container)) {
      for (const nd of container.childNodes) {
        if (nd.nodeType === 3 && nd.textContent.trim()) {
          const rg = document.createRange();
          rg.selectNodeContents(nd);
          const rr = rg.getBoundingClientRect();
          if (rr.height > 0) { last = Math.max(last, rr.bottom); n++; }
        }
      }
    }
    for (const d of container.querySelectorAll('*')) {
      if (!vis(d)) continue;
      const t = (d.children.length === 0 && (d.innerText || '').trim()) || hasDirectText(d);
      if (t || mediaTags.has(d.tagName.toLowerCase())) { last = Math.max(last, d.getBoundingClientRect().bottom); n++; }
    }
    return { last, n };
  };
  if (document.documentElement.scrollWidth > vw + 2)
    out.push(['WARN', 'page-overflow-x', `page is ${document.documentElement.scrollWidth}px wide in a ${vw}px viewport (horizontal scrollbar)`]);
  const clipped = [], hidden = [], empty = [], edge = [], blank = [], hollow = [], tinyDesk = [], trUpper = [];
  const hasTrContext = /[ğüşıöçĞÜŞİÖÇ]/.test(document.body?.innerText || '');
  for (const e of document.querySelectorAll('body *')) {
    if (!vis(e)) continue;
    const cs = getComputedStyle(e), tag = e.tagName.toLowerCase(), r = e.getBoundingClientRect();
    if (['script', 'style', 'svg', 'path', 'circle', 'rect', 'g', 'defs', 'stop', 'line', 'polygon', 'polyline', 'ellipse', 'text', 'tspan'].includes(tag)) continue;
    const text = (e.innerText || '').trim();
    const srOnly = r.width <= 2 || r.height <= 2 || cs.clip === 'rect(0px, 0px, 0px, 0px)' || cs.clipPath === 'inset(50%)';
    if (!srOnly) {
      if ((cs.overflowX === 'hidden' && e.scrollWidth > e.clientWidth + 3) || (cs.overflowY === 'hidden' && e.scrollHeight > e.clientHeight + 3)) {
        if (text && e.clientHeight > 0 && !cs.textOverflow.includes('ellipsis') && (cs.webkitLineClamp === 'none' || !cs.webkitLineClamp)) clipped.push(where(e));
      }
      if ((tag === 'pre' || tag === 'code') && e.scrollWidth > e.clientWidth + 3 && cs.display !== 'inline' && cs.overflowX !== 'auto' && cs.overflowX !== 'scroll') clipped.push(where(e) + ' (text runs out of its box)');
      if (text && parseFloat(cs.webkitTextStrokeWidth) > 0 && (cs.webkitTextFillColor === 'transparent' || /rgba\([^)]+,\s*0(?:\.0+)?\)/.test(cs.webkitTextFillColor || ''))) hollow.push(where(e));
      if (parseFloat(cs.fontSize) < 12 && [...e.childNodes].some(nd => nd.nodeType === 3 && nd.textContent.trim().length > 12)) tinyDesk.push(where(e) + ` (${Math.round(parseFloat(cs.fontSize))}px)`);
      if (cs.textTransform === 'uppercase') {
        const directText = [...e.childNodes].filter(nd => nd.nodeType === 3).map(nd => nd.textContent).join('').trim();
        if (directText && (/[ğüşıöçĞÜŞİÖÇ]/.test(directText) || (/i/.test(directText) && hasTrContext))) {
          const lang = e.closest('[lang]')?.getAttribute('lang') || document.documentElement.lang || '';
          if (!/^tr\b/i.test(lang)) trUpper.push(where(e));
        }
      }
    }
    if (text && parseFloat(cs.opacity) === 0 && !e.closest('[aria-hidden=true]')) hidden.push(where(e));
    if ((tag === 'button' || tag === 'a') && !text && !e.querySelector('svg,img,canvas') && !e.getAttribute('aria-label') && !e.getAttribute('title')) empty.push(where(e));
    if (['img', 'canvas', 'figure'].includes(tag) && r.right > vw + 2 && r.left < vw - 8) edge.push(where(e));
  }
  for (const e of document.querySelectorAll('section, main > div, header, footer')) {
    if (!vis(e) || getComputedStyle(e).position === 'absolute') continue;
    const r = e.getBoundingClientRect();
    if (r.height > 320 && !(e.innerText || '').trim() && !e.querySelector('svg,img,canvas,video,iframe')) blank.push(where(e) + ` (${Math.round(r.height)}px)`);
  }
  const sparse = [];
  for (const e of document.querySelectorAll('div, section, article, aside, pre')) {
    if (!vis(e)) continue;
    const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    if (r.height < 260 || r.width < 240) continue;
    if (!(parseFloat(cs.borderTopWidth) > 0 || cs.backgroundColor !== 'rgba(0, 0, 0, 0)')) continue;
    if (e.matches('body > div, main, #app, #root') || r.width > innerWidth * 0.9) continue;
    const { last, n } = contentBottom(e);
    if (n && (last - r.top) / r.height < 0.5) sparse.push(where(e) + ` (${Math.round(100 * (last - r.top) / r.height)}% filled)`);
  }
  if (sparse.length) out.push(['WARN', 'empty-panel', `${sparse.length} panel(s) are more than half empty: ${[...new Set(sparse)].slice(0, 4).join(', ')}; fill them (more rows, content) or shrink the panel`]);
  const cols = [];
  for (const p of document.querySelectorAll('div, section, main, article')) {
    if (!vis(p)) continue;
    const pr = p.getBoundingClientRect(), pcs = getComputedStyle(p);
    if (pr.height < 700 || p.children.length < 2) continue;
    if (!(pcs.display === 'grid' || (pcs.display === 'flex' && pcs.flexDirection.startsWith('row')))) continue;
    const visCols = [...p.children].filter(c => vis(c) && getComputedStyle(c).position !== 'absolute').map(c => ({ c, r: c.getBoundingClientRect(), cs: getComputedStyle(c) }));
    for (const col of visCols) {
      if (col.cs.position === 'sticky' || col.cs.position === 'fixed') continue;
      if ([...col.c.children].some(ch => getComputedStyle(ch).position === 'sticky')) continue;
      if (col.c.matches('nav') || (col.c.matches('aside') && col.c.querySelector('nav'))) continue;
      const r = col.r;
      if (r.width < 200) continue;
      if (pcs.display === 'grid' && visCols.some(sib => sib.c !== col.c && sib.r.top >= r.bottom - 5 && sib.r.left < r.right - 5 && sib.r.right > r.left + 5)) continue;
      const rowSibs = visCols.filter(sib => sib.cs.position !== 'fixed' && Math.abs(r.top - sib.r.top) < 80 && Math.min(r.bottom, sib.r.bottom) > Math.max(r.top, sib.r.top));
      if (rowSibs.length < 2) continue;
      const rowTop = Math.min(...rowSibs.map(s => s.r.top));
      const rowBottom = Math.max(...rowSibs.map(s => s.r.bottom));
      const rowHeight = rowBottom - rowTop;
      const { last, n } = contentBottom(col.c);
      const blankH = rowBottom - last;
      if (n && rowHeight > 0 && blankH > 500 && blankH / rowHeight > 0.4) cols.push(where(col.c) + ` (${Math.round(blankH)}px empty below its content)`);
    }
  }
  if (cols.length) out.push(['WARN', 'empty-column', `${cols.length} column(s) end far above their row: ${[...new Set(cols)].slice(0, 3).join(', ')}; continue the column (stats, related reading, contents) or use a single column`]);
  const ovl = [];
  const isHiddenOrRotated = (el, svg) => {
    for (let cur = el; cur && cur !== svg.parentElement; cur = cur.parentElement) {
      const pcs = getComputedStyle(cur);
      if (parseFloat(pcs.opacity) === 0 || pcs.display === 'none' || pcs.visibility === 'hidden') return true;
      if ((cur.getAttribute('transform') || '').includes('rotate')) return true;
      const tm = (pcs.transform || '').match(/^matrix\(([^)]+)\)/);
      if (tm) {
        const pts = tm[1].split(',').map(Number);
        if (Math.abs(pts[1]) > 0.05 || Math.abs(pts[2]) > 0.05) return true;
      }
    }
    return false;
  };
  for (const svg of document.querySelectorAll('svg')) {
    const labs = [...svg.querySelectorAll('text')].filter(el => {
      if (!vis(el)) return false;
      const cs = getComputedStyle(el);
      if (cs.fill === 'none') return false;
      if (isHiddenOrRotated(el, svg)) return false;
      return true;
    }).slice(0, 200);
    for (let i = 0; i < labs.length; i++) for (let j = i + 1; j < labs.length; j++) {
      const a = labs[i].getBoundingClientRect(), b = labs[j].getBoundingClientRect();
      const w = Math.min(a.right, b.right) - Math.max(a.left, b.left), h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (w > 2 && h > 2 && w * h > 0.25 * Math.min(a.width * a.height, b.width * b.height))
        ovl.push(`"${(labs[i].textContent || '').trim().slice(0, 12)}" / "${(labs[j].textContent || '').trim().slice(0, 12)}"`);
    }
  }
  if (ovl.length) out.push(['WARN', 'overlapping-labels', `${ovl.length} SVG label pair(s) overlap: ${ovl.slice(0, 3).join(', ')}; move or shorten the labels`]);
  const darkSelRe = /\.dark\b|\[data-theme\s*=\s*["']?dark["']?\]/i;
  const hasDarkRule = rules => {
    for (const r of rules) {
      if (r.selectorText && darkSelRe.test(r.selectorText)) return true;
      if (r.cssRules && hasDarkRule(r.cssRules)) return true;
    }
    return false;
  };
  let hasDarkStyles = false;
  for (const ss of document.styleSheets) {
    try {
      if (ss.cssRules && hasDarkRule(ss.cssRules)) { hasDarkStyles = true; break; }
    } catch (_) {}
  }
  if (hasDarkStyles) {
    const themeRe = /theme|tema|dark|light|karanl[ıiİ]k|ayd[ıiİ]nl[ıiİ]k|gece|g[üuÜ]nd[üuÜ]z/i;
    const hasToggle = [...document.querySelectorAll('[data-theme-toggle], button, input, select, a, [role="switch"]')].some(el => {
      if (!vis(el)) return false;
      if (el.hasAttribute('data-theme-toggle')) return true;
      const meta = `${el.getAttribute('aria-label') || ''} ${el.getAttribute('title') || ''} ${el.id || ''} ${el.innerText || ''}`;
      return themeRe.test(meta);
    });
    if (!hasToggle) out.push(['WARN', 'theme-toggle-missing', 'dark theme styles (.dark or [data-theme="dark"]) are defined, but no visible theme toggle control was found']);
  }
  const numCellRe = /^(?=.*\d)[\d\s,.%₺$€+-]+$/;
  const numAlign = [];
  for (const tbl of document.querySelectorAll('table')) {
    if (!vis(tbl)) continue;
    const colsMap = new Map();
    for (const tr of tbl.querySelectorAll('tr')) {
      if (!vis(tr)) continue;
      let col = 0;
      for (const cell of tr.children) {
        const span = parseInt(cell.getAttribute('colspan') || '1', 10) || 1;
        if (cell.tagName === 'TD' && vis(cell)) {
          const txt = (cell.innerText || '').trim();
          if (numCellRe.test(txt)) {
            if (!colsMap.has(col)) colsMap.set(col, []);
            colsMap.get(col).push(cell);
          }
        }
        col += span;
      }
    }
    for (const [col, cells] of colsMap) {
      if (cells.length >= 2 && cells.some(td => !getComputedStyle(td).fontVariantNumeric.includes('tabular-nums'))) {
        numAlign.push(`${where(tbl)} col ${col + 1}`);
      }
    }
  }
  const isLongLoading = window.__RENDER_STATE__ === 'long-loading'
    || document.documentElement.getAttribute('data-render-state') === 'long-loading'
    || location.search.includes('state=long-loading');
  if (isLongLoading) {
    const hasExplain = [...document.querySelectorAll('progress, [role="progressbar"], [data-stage], [data-step], [aria-current="step"]')].some(vis)
      || [...document.querySelectorAll('button, a, [role="button"]')].some(b => vis(b) && /[iİı]ptal|cancel|arka plana al|notify/i.test(`${b.innerText || ''} ${b.getAttribute('aria-label') || ''} ${b.getAttribute('title') || ''}`));
    if (!hasExplain) {
      const bText = (document.body?.innerText || '').trim();
      const bLines = bText ? bText.split(/\r?\n/).map(s => s.trim()).filter(Boolean) : [];
      if (bLines.length <= 2 && bText.length <= 160) {
        out.push(['WARN', 'long-wait-unexplained', 'long-loading state shows only a bare spinner/short message without progress, stage/step, or cancel/notify control']);
      }
    }
  }
  const u = a => [...new Set(a)].slice(0, 5).join(', ');
  if (clipped.length) out.push(['WARN', 'clipped-content', `${clipped.length} element(s) cut off or overflowing: ${u(clipped)}`]);
  if (hollow.length) out.push(['WARN', 'hollow-text', `${hollow.length} stroked hollow/transparent text element(s) hurt low-vision legibility: ${u(hollow)}`]);
  if (tinyDesk.length) out.push(['WARN', 'desktop-tiny-text', `${tinyDesk.length} text run(s) under 12px on desktop: ${u(tinyDesk)}`]);
  if (trUpper.length) out.push(['WARN', 'tr-uppercase-render', `${trUpper.length} uppercase Turkish text element(s) missing lang="tr": ${u(trUpper)}`]);
  if (hidden.length) out.push(['WARN', 'invisible-content', `${hidden.length} element(s) with text but opacity 0 after load and scroll: ${u(hidden)}`]);
  if (blank.length) out.push(['WARN', 'blank-band', `${blank.length} tall section(s) render empty: ${u(blank)}`]);
  if (empty.length) out.push(['WARN', 'empty-control', `${empty.length} button/link without text, icon or label: ${u(empty)}`]);
  if (edge.length) out.push(['INFO', 'edge-clipped-art', `art runs past the right edge: ${u(edge)}; keep the subject fully visible or bleed at least a third of it`]);
  if (numAlign.length) out.push(['INFO', 'numeric-alignment', `${numAlign.length} numeric table column(s) lack font-variant-numeric: tabular-nums: ${u(numAlign)}`]);
  if (!out.length) out.push(['INFO', 'dom-check', 'no layout defects found']);
  return out;
}
