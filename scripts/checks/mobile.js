() => {
  const out = [], vw = innerWidth;
  const vis = e => { const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
                     return r.width > 2 && r.height > 2 && cs.display !== 'none' && cs.visibility !== 'hidden' && parseFloat(cs.opacity) !== 0 && cs.clip !== 'rect(0px, 0px, 0px, 0px)' && cs.clipPath !== 'inset(50%)'; };
  if (document.documentElement.scrollWidth > vw + 2)
    out.push(['WARN', 'mobile-overflow-x', `page is ${document.documentElement.scrollWidth}px wide at ${vw}px (horizontal scroll)`]);
  const small = [], tiny = [];
  for (const e of document.querySelectorAll('a, button, input, select, textarea, [role=button]')) {
    if (!vis(e) || (e.tagName === 'INPUT' && (e.type || '').toLowerCase() === 'hidden')) continue;
    const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    const cls = typeof e.className === 'string' ? e.className : (e.getAttribute('class') || '');
    const isControl = e.tagName !== 'A' || e.getAttribute('role') === 'button';
    const hasBoxBorder = parseFloat(cs.borderTopWidth) > 0 && parseFloat(cs.borderBottomWidth) > 0 && parseFloat(cs.borderLeftWidth) > 0 && parseFloat(cs.borderRightWidth) > 0;
    const hasBg = cs.backgroundColor !== 'rgba(0, 0, 0, 0)' && cs.backgroundColor !== 'transparent';
    const isBtnLink = e.tagName === 'A' && (/\b(btn|button|cta)\b/i.test(cls) || (cs.display !== 'inline' && (hasBg || hasBoxBorder)));
    const isSmallStandaloneLink = e.tagName === 'A' && cs.display !== 'inline' && !e.closest('p, li') && r.width <= 120;
    if (r.height < 36 && (isControl || isBtnLink || isSmallStandaloneLink))
      small.push((e.innerText || e.getAttribute('aria-label') || e.placeholder || e.tagName).trim().slice(0, 18) + ` (${Math.round(r.width)}x${Math.round(r.height)})`);
  }
  for (const e of document.querySelectorAll('p, li, span, a, button, td')) {
    if (!vis(e)) continue;
    const cs = getComputedStyle(e);
    if ([...e.childNodes].some(nd => nd.nodeType === 3 && nd.textContent.trim().length > 3) && parseFloat(cs.fontSize) < 11)
      tiny.push(e.textContent.trim().slice(0, 14));
  }
  if (small.length) out.push(['INFO', 'mobile-tap-targets', `${small.length} control(s) under 36px tall: ${small.slice(0, 4).join(', ')}`]);
  if (tiny.length) out.push(['WARN', 'mobile-tiny-text', `${tiny.length} text run(s) under 11px: ${tiny.slice(0, 4).join(', ')}`]);
  return out;
}
