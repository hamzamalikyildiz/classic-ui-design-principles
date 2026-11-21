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
  const btns = [...document.querySelectorAll('button, [role=button]')]
    .filter(b => (b.innerText || '').trim() && b.getBoundingClientRect().width && getComputedStyle(b).display !== 'none' && b.type !== 'submit' && !b.disabled && b.getAttribute('aria-disabled') !== 'true').slice(0, 8);
  let dead = [];
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
  if (dead.length) out.push(['INFO', 'dead-buttons', `${dead.length} button(s) changed nothing when clicked: ${dead.slice(0, 5).join(', ')}`]);
  return out;
}
