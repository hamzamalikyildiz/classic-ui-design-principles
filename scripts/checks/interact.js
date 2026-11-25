async () => {
  const out = [];
  const focusEls = [...document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea, [tabindex]:not([tabindex="-1"])')]
    .filter(e => {
      const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
      return r.width > 2 && r.height > 2 && cs.display !== 'none' && cs.visibility !== 'hidden' && parseFloat(cs.opacity) !== 0 && cs.clip !== 'rect(0px, 0px, 0px, 0px)' && cs.clipPath !== 'inset(50%)' && !e.disabled && e.getAttribute('aria-disabled') !== 'true';
    }).slice(0, 6);
  let noRing = 0;
  for (const e of focusEls) {
    e.focus({ focusVisible: true });
    const cs = getComputedStyle(e);
    const cls = typeof e.className === 'string' ? e.className : (e.getAttribute('class') || '');
    if (document.activeElement === e && cs.outlineStyle === 'none' && cs.boxShadow === 'none' && !/(?:^|\s)focus(?:-visible)?:(?:ring(?!-0\b)(?:-\S+|\b)|outline(?!-(?:none|0)\b)(?:-\S+|\b)|border-(?!transparent\b)\S+)/.test(cls)) noRing++;
  }
  if (noRing >= 3) out.push(['WARN', 'no-focus-ring', `${noRing} of ${focusEls.length} checked control(s) show no focus indicator (add focus-visible:ring-2)`]);
  const skipBtnRe = /(?<![\p{L}\p{N}_])(log\s*out|sign\s*out|[cç][ıiİ]k[ıiİ][sş]|delete|s[iıİ]l|remove|revoke|destroy|reset|disconnect|unsubscribe|cancel\s+account)(?![\p{L}\p{N}_])/iu;
  const themeMetaRe = /(?<![\p{L}\p{N}_])(theme|tema|dark|light|karanl[ıiİ]k|ayd[ıiİ]nl[ıiİ]k|gece|g[üuÜ]nd[üuÜ]z)(?![\p{L}\p{N}_])/iu;
  const themeExplicitRe = /\b(toggle\s+(?:dark|light|theme)|(?:dark|light|theme)\s+(?:mode|toggle|switcher)|tema\s+de[ğg]i[şs]tir)\b|theme[-_]?toggle/i;
  const isUnsafeOrThemeBtn = b => {
    if (b.closest('[data-theme-toggle], [data-destructive]')) return true;
    const meta = [
      b.innerText || '',
      b.getAttribute('aria-label') || '',
      b.getAttribute('title') || '',
      b.id || '',
      b.getAttribute('name') || '',
      b.getAttribute('data-action') || '',
    ].join(' ');
    if (skipBtnRe.test(meta) || themeExplicitRe.test(meta)) return true;
    if ((b.hasAttribute('aria-pressed') || b.getAttribute('role') === 'switch') && themeMetaRe.test(meta)) return true;
    return false;
  };
  const btns = [...document.querySelectorAll('button, [role=button]')]
    .filter(b => (b.innerText || '').trim() && b.getBoundingClientRect().width && getComputedStyle(b).display !== 'none' && b.type !== 'submit' && !b.disabled && b.getAttribute('aria-disabled') !== 'true' && !isUnsafeOrThemeBtn(b)).slice(0, 8);
  const rootEl = document.documentElement;
  const initClass = rootEl.className;
  const hasInitDataTheme = rootEl.hasAttribute('data-theme');
  const initDataTheme = rootEl.getAttribute('data-theme');
  let savedStorage = null;
  try {
    savedStorage = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k !== null) savedStorage.push([k, localStorage.getItem(k)]);
    }
  } catch (e) {
    savedStorage = null;
  }
  let dead = [];
  try {
    for (const b of btns) {
      let changed = false;
      const mo = new MutationObserver(() => { changed = true; });
      mo.observe(document.documentElement, { subtree: true, attributes: true, childList: true, characterData: true });
      const x = scrollX, y = scrollY; try { b.click(); } catch (e) {}
      await new Promise(r => setTimeout(r, 120)); mo.disconnect();
      if (Math.abs(scrollY - y) > 5 || Math.abs(scrollX - x) > 5) changed = true;
      if (scrollY !== y || scrollX !== x) scrollTo(x, y);
      if (!changed && !b.closest('a, form')) dead.push(b.innerText.trim().slice(0, 18));
    }
  } finally {
    try {
      if (rootEl.className !== initClass) rootEl.className = initClass;
      if (hasInitDataTheme) {
        if (rootEl.getAttribute('data-theme') !== initDataTheme) rootEl.setAttribute('data-theme', initDataTheme);
      } else if (rootEl.hasAttribute('data-theme')) {
        rootEl.removeAttribute('data-theme');
      }
    } catch (e) {}
    if (savedStorage !== null) {
      try {
        let dirty = localStorage.length !== savedStorage.length;
        if (!dirty) {
          for (const [k, v] of savedStorage) {
            if (localStorage.getItem(k) !== v) { dirty = true; break; }
          }
        }
        if (dirty) {
          localStorage.clear();
          for (const [k, v] of savedStorage) localStorage.setItem(k, v);
        }
      } catch (e) {}
    }
  }
  if (dead.length) out.push(['INFO', 'dead-buttons', `${dead.length} button(s) changed nothing when clicked: ${dead.slice(0, 5).join(', ')}`]);
  return out;
}
