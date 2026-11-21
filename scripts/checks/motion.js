async (opts = {}) => {
  const out = [];
  const mode = (opts && opts.mode) || 'all';
  const skipTrigger = Boolean(opts && opts.skipTrigger);
  const triggerSelector = (opts && opts.triggerSelector) || null;
  const action = (opts && opts.action) || 'check';

  const toKebab = p => String(p || '').replace(/[A-Z]/g, m => '-' + m.toLowerCase()).trim().toLowerCase();

  const parseTimeMs = str => {
    if (!str) return 0;
    const s = String(str).trim().toLowerCase();
    if (s.endsWith('ms')) return parseFloat(s) || 0;
    if (s.endsWith('s')) return (parseFloat(s) || 0) * 1000;
    return parseFloat(s) || 0;
  };

  const parseTimeListMs = str => String(str || '').split(',').map(parseTimeMs);

  const where = e => {
    if (!e || !e.tagName) return 'element';
    const id = e.id ? '#' + e.id : '';
    const c = (e.className && e.className.baseVal === undefined ? String(e.className) : '')
      .trim().split(/\s+/).filter(Boolean).slice(0, 2).join('.');
    return e.tagName.toLowerCase() + id + (c ? '.' + c : '');
  };

  const vis = e => {
    if (!e || e.nodeType !== 1) return false;
    const cs = getComputedStyle(e);
    if (cs.display === 'none' || cs.visibility === 'hidden') return false;
    const r = e.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };

  const findTrigger = sel => {
    const isInteractiveVisible = e => {
      if (!vis(e)) return false;
      if (e.disabled || e.getAttribute('aria-disabled') === 'true') return false;
      const cs = getComputedStyle(e);
      return cs.pointerEvents !== 'none';
    };
    if (sel) {
      return [...document.querySelectorAll(sel)].filter(isInteractiveVisible)[0] || null;
    }
    const explicit = [...document.querySelectorAll('[data-motion-trigger]')].filter(isInteractiveVisible);
    if (explicit.length) return explicit[0];
    const candidates = [...document.querySelectorAll('button, [role="tab"]')].filter(isInteractiveVisible);
    if (!candidates.length) return null;
    if (candidates[0].getAttribute('role') === 'tab' && candidates[0].getAttribute('aria-selected') === 'true') {
      const unselected = candidates.find(e => e.getAttribute('role') === 'tab' && e.getAttribute('aria-selected') === 'false');
      if (unselected) return unselected;
    }
    return candidates[0];
  };

  const startProbeAndClick = target => {
    if (!target) return null;
    const state = {
      t0: performance.now(),
      firstMutationMs: null,
      nextFrameMs: null,
      targetLabel: where(target),
      done: false,
      _mo: null,
    };
    let initialAnims = new Set();
    try {
      initialAnims = new Set(document.getAnimations());
    } catch (e) {}
    const mo = new MutationObserver(records => {
      if (state.firstMutationMs === null && records && records.length > 0) {
        state.firstMutationMs = performance.now() - state.t0;
      }
    });
    mo.observe(document.documentElement, {
      subtree: true,
      childList: true,
      attributes: true,
      characterData: true,
    });
    state._mo = mo;
    requestAnimationFrame(() => {
      state.nextFrameMs = performance.now() - state.t0;
      if (state.firstMutationMs === null) {
        try {
          const currentAnims = document.getAnimations();
          if (currentAnims.some(a => !initialAnims.has(a))) {
            state.firstMutationMs = state.nextFrameMs;
          }
        } catch (e) {}
      }
    });
    state.finish = () => {
      if (state.done) return state;
      state.done = true;
      try {
        const pending = mo.takeRecords();
        if (state.firstMutationMs === null && pending && pending.length > 0) {
          state.firstMutationMs = performance.now() - state.t0;
        }
        mo.disconnect();
      } catch (e) {}
      return state;
    };
    try {
      target.click();
    } catch (e) {}
    return state;
  };

  if (action === 'probe') {
    const trig = findTrigger(triggerSelector);
    if (!trig) {
      window.__motionProbe = null;
      return { triggered: false };
    }
    window.__motionProbe = startProbeAndClick(trig);
    return { triggered: true, target: where(trig) };
  }

  const LAYOUT_EXACT = new Set([
    'width', 'height', 'min-width', 'max-width', 'min-height', 'max-height',
    'top', 'left', 'right', 'bottom', 'inset',
  ]);
  const isLayoutProp = prop => {
    const p = toKebab(prop);
    if (!p || p === 'none' || p === 'all') return false;
    return LAYOUT_EXACT.has(p) || p.startsWith('inset-') || p === 'margin' || p.startsWith('margin-') || p === 'padding' || p.startsWith('padding-');
  };

  const isSpatialProp = prop => {
    const p = toKebab(prop);
    if (!p || p === 'none') return false;
    if (p === 'transform' || p === 'translate' || p === 'scale' || p === 'rotate' ||
        p === 'perspective' || p === 'clip-path' || p === 'offset-path' || p === 'offset-distance' || p === 'all') {
      return true;
    }
    return isLayoutProp(p);
  };

  const collectKeyframes = () => {
    const kfMap = new Map();
    const walk = rules => {
      if (!rules) return;
      for (const r of rules) {
        try {
          if (r.type === 7 && r.name) {
            const props = kfMap.get(r.name) || new Set();
            for (const kf of r.cssRules || []) {
              for (let i = 0; i < kf.style.length; i++) {
                props.add(toKebab(kf.style[i]));
              }
            }
            kfMap.set(r.name, props);
          } else if (r.cssRules) {
            if (r.type === 4 && r.media && r.media.mediaText && !window.matchMedia(r.media.mediaText).matches) {
              continue;
            }
            walk(r.cssRules);
          }
        } catch (e) {}
      }
    };
    for (const sheet of document.styleSheets || []) {
      try {
        walk(sheet.cssRules);
      } catch (e) {}
    }
    return kfMap;
  };

  const getKeyframeAnimatedProps = anim => {
    const props = new Set();
    try {
      const kfs = anim.effect && typeof anim.effect.getKeyframes === 'function' ? anim.effect.getKeyframes() : [];
      const skipKeys = new Set(['offset', 'computedOffset', 'easing', 'composite']);
      const valuesByProp = new Map();
      for (const kf of kfs) {
        for (const k of Object.keys(kf)) {
          if (skipKeys.has(k)) continue;
          const keb = toKebab(k);
          if (!valuesByProp.has(keb)) valuesByProp.set(keb, new Set());
          valuesByProp.get(keb).add(String(kf[k]));
        }
      }
      for (const [k, vals] of valuesByProp.entries()) {
        if (vals.size > 1 || anim.transitionProperty === k) props.add(k);
      }
    } catch (e) {}
    if (anim.transitionProperty) props.add(toKebab(anim.transitionProperty));
    return props;
  };

  const isUiFeedbackEl = e => {
    if (!e || e.nodeType !== 1) return false;
    if (e.matches('main > section:first-child, .hero, .hero-card, [class*="hero"]')) return false;
    if (e.matches('button, [role="button"], [role="tab"], [role="switch"], [role="menuitem"], [role="dialog"], dialog, input, select, textarea, summary')) {
      return true;
    }
    const cls = typeof e.className === 'string' ? e.className : '';
    return /\b(btn|button|card|modal|dialog|drawer|popover|tooltip|tab|toast|badge|pill|chip|alert|input|control)\b/i.test(cls)
      || /-(btn|button|card|modal|dialog|tab|toast)\b/i.test(cls);
  };

  const isLoadingIndicator = e => {
    if (!e || e.nodeType !== 1) return false;
    return Boolean(e.closest(
      '[role="status"], [role="progressbar"], [aria-busy="true"], .spinner, .skeleton, .animate-pulse, .animate-spin, [class*="spinner"], [class*="skeleton"], [class*="loading"]'
    ));
  };

  const hasPauseControl = () => [...document.querySelectorAll('button, [role="button"], input[type="checkbox"], [role="switch"], [data-pause-motion]')].some(el => {
    if (!vis(el)) return false;
    const txt = [
      el.innerText || '',
      el.getAttribute('aria-label') || '',
      el.getAttribute('title') || '',
      el.getAttribute('data-action') || '',
    ].join(' ').toLowerCase();
    return /\b(pause|duraklat|stop motion|play[- ]?state|freeze)\b/.test(txt) || el.hasAttribute('data-pause-motion');
  });

  const measureCLS = () => new Promise(resolve => {
    if (typeof PerformanceObserver === 'undefined') return resolve(0);
    const entries = [];
    let po = null;
    try {
      po = new PerformanceObserver(list => {
        for (const e of list.getEntries()) entries.push(e);
      });
      po.observe({ type: 'layout-shift', buffered: true });
    } catch (e) {
      return resolve(0);
    }
    setTimeout(() => {
      try {
        if (po && typeof po.takeRecords === 'function') {
          for (const e of po.takeRecords()) entries.push(e);
        }
        if (po) po.disconnect();
      } catch (e) {}
      const seen = new Set();
      const filtered = [];
      for (const e of entries) {
        if (e.hadRecentInput) continue;
        const key = `${e.startTime}:${e.value}`;
        if (seen.has(key)) continue;
        seen.add(key);
        filtered.push(e);
      }
      filtered.sort((a, b) => a.startTime - b.startTime);
      let maxSession = 0, sessionVal = 0, sessionStart = 0, prevTime = 0;
      for (const e of filtered) {
        if (sessionStart === 0 || (e.startTime - prevTime) > 1000 || (e.startTime - sessionStart) > 5000) {
          sessionStart = e.startTime;
          sessionVal = 0;
        }
        sessionVal += e.value || 0;
        prevTime = e.startTime;
        if (sessionVal > maxSession) maxSession = sessionVal;
      }
      resolve(maxSession);
    }, 60);
  });

  const runNormalChecks = async () => {
    let probe = window.__motionProbe || null;
    if (!probe && !skipTrigger) {
      const trig = findTrigger(triggerSelector);
      if (trig) {
        probe = startProbeAndClick(trig);
        await new Promise(r => setTimeout(r, 320));
      }
    }
    if (probe && typeof probe.finish === 'function') {
      probe.finish();
      window.__motionProbe = null;
    }

    if (probe) {
      if (probe.firstMutationMs !== null && probe.firstMutationMs > 100) {
        out.push(['WARN', 'slow-feedback', `${probe.targetLabel} took ${Math.round(probe.firstMutationMs)}ms to show DOM/visual feedback (> 100ms)`]);
      } else if (probe.firstMutationMs === null && probe.nextFrameMs !== null && probe.nextFrameMs > 200) {
        out.push(['WARN', 'slow-feedback', `${probe.targetLabel} blocked next animation frame for ${Math.round(probe.nextFrameMs)}ms (> 200ms INP threshold)`]);
      }
    }

    const kfMap = collectKeyframes();
    const layoutHits = new Set();
    const longUiHits = new Set();
    const infiniteHits = new Set();
    const pauseExists = hasPauseControl();

    for (const el of document.querySelectorAll('body *')) {
      if (!vis(el)) continue;
      const cs = getComputedStyle(el);
      const label = where(el);

      const tProps = String(cs.transitionProperty || '').split(',').map(s => s.trim()).filter(Boolean);
      const tDurs = parseTimeListMs(cs.transitionDuration);
      tProps.forEach((prop, i) => {
        const dur = tDurs[i % Math.max(1, tDurs.length)] || 0;
        if (dur <= 0) return;
        if (isLayoutProp(prop)) layoutHits.add(`${label} (${prop} ${Math.round(dur)}ms)`);
        if (dur > 500 && isUiFeedbackEl(el)) longUiHits.add(`${label} (${prop} ${Math.round(dur)}ms)`);
      });

      const aNames = String(cs.animationName || '').split(',').map(s => s.trim()).filter(Boolean);
      const aDurs = parseTimeListMs(cs.animationDuration);
      const aIters = String(cs.animationIterationCount || '').split(',').map(s => s.trim());
      const aStates = String(cs.animationPlayState || '').split(',').map(s => s.trim());
      aNames.forEach((name, i) => {
        if (!name || name === 'none') return;
        const dur = aDurs[i % Math.max(1, aDurs.length)] || 0;
        const iter = aIters[i % Math.max(1, aIters.length)] || '1';
        const pState = aStates[i % Math.max(1, aStates.length)] || 'running';
        const kfProps = kfMap.get(name);
        if (dur > 0 && kfProps) {
          for (const kp of kfProps) {
            if (isLayoutProp(kp)) layoutHits.add(`${label} (@keyframes ${name}: ${kp})`);
          }
        }
        if (dur > 500 && iter !== 'infinite' && isUiFeedbackEl(el)) {
          longUiHits.add(`${label} (@keyframes ${name} ${Math.round(dur)}ms)`);
        }
        if (iter === 'infinite' && pState !== 'paused' && !pauseExists && !isLoadingIndicator(el)) {
          infiniteHits.add(`${label} (${name})`);
        }
      });
    }

    try {
      for (const anim of document.getAnimations()) {
        const target = anim.effect && anim.effect.target;
        if (!target || !vis(target)) continue;
        const label = where(target);
        const timing = anim.effect && typeof anim.effect.getTiming === 'function' ? anim.effect.getTiming() : {};
        const dur = typeof timing.duration === 'number' ? timing.duration : 0;
        const iters = timing.iterations;
        const props = getKeyframeAnimatedProps(anim);
        for (const p of props) {
          if (isLayoutProp(p)) layoutHits.add(`${label} (${p})`);
        }
        const isPseudo = Boolean(anim.effect && anim.effect.pseudoElement);
        if (!isPseudo && dur > 500 && iters !== Infinity && isUiFeedbackEl(target)) {
          longUiHits.add(`${label} (${Math.round(dur)}ms)`);
        }
        if (iters === Infinity && anim.playState !== 'paused' && !pauseExists && !isLoadingIndicator(target)) {
          infiniteHits.add(`${label} (${anim.animationName || 'animation'})`);
        }
      }
    } catch (e) {}

    if (layoutHits.size) {
      out.push(['WARN', 'motion-layout-property', `${layoutHits.size} layout property animation(s)/transition(s) found (prefer transform/opacity): ${[...layoutHits].slice(0, 4).join(', ')}`]);
    }
    if (longUiHits.size) {
      out.push(['INFO', 'long-ui-transition', `${longUiHits.size} UI feedback transition(s)/animation(s) exceed 500ms: ${[...longUiHits].slice(0, 4).join(', ')}`]);
    }
    if (infiniteHits.size) {
      out.push(['INFO', 'infinite-motion', `${infiniteHits.size} infinite non-loading animation(s) lack a pause control: ${[...infiniteHits].slice(0, 4).join(', ')}`]);
    }

    const cls = await measureCLS();
    if (cls > 0.1) {
      out.push(['WARN', 'layout-shift', `Cumulative Layout Shift (CLS) is ${cls.toFixed(3)} (> 0.1 threshold)`]);
    }
  };

  const runReducedMotionCheck = () => {
    if (!window.matchMedia || !window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const kfMap = collectKeyframes();
    const hits = new Set();

    for (const el of document.querySelectorAll('body *')) {
      if (!vis(el)) continue;
      const cs = getComputedStyle(el);
      const label = where(el);

      const tProps = String(cs.transitionProperty || '').split(',').map(s => s.trim()).filter(Boolean);
      const tDurs = parseTimeListMs(cs.transitionDuration);
      tProps.forEach((prop, i) => {
        const dur = tDurs[i % Math.max(1, tDurs.length)] || 0;
        if (dur > 150 && isSpatialProp(prop)) {
          hits.add(`${label} (transition ${prop} ${Math.round(dur)}ms)`);
        }
      });

      const aNames = String(cs.animationName || '').split(',').map(s => s.trim()).filter(Boolean);
      const aDurs = parseTimeListMs(cs.animationDuration);
      const aStates = String(cs.animationPlayState || '').split(',').map(s => s.trim());
      aNames.forEach((name, i) => {
        if (!name || name === 'none') return;
        const dur = aDurs[i % Math.max(1, aDurs.length)] || 0;
        const pState = aStates[i % Math.max(1, aStates.length)] || 'running';
        if (dur > 150 && pState !== 'paused') {
          const kfProps = kfMap.get(name);
          if (!kfProps || [...kfProps].some(isSpatialProp)) {
            hits.add(`${label} (animation ${name} ${Math.round(dur)}ms)`);
          }
        }
      });
    }

    try {
      for (const anim of document.getAnimations()) {
        if (anim.playState === 'finished' || anim.playState === 'paused') continue;
        const target = anim.effect && anim.effect.target;
        if (!target || !vis(target)) continue;
        const computed = anim.effect && typeof anim.effect.getComputedTiming === 'function' ? anim.effect.getComputedTiming() : {};
        const dur = typeof computed.duration === 'number' ? computed.duration : 0;
        if (dur > 150) {
          const props = getKeyframeAnimatedProps(anim);
          if (!props.size || [...props].some(isSpatialProp)) {
            hits.add(`${where(target)} (${anim.animationName || anim.transitionProperty || 'motion'} ${Math.round(dur)}ms)`);
          }
        }
      }
    } catch (e) {}

    if (hits.size) {
      out.push(['WARN', 'reduced-motion-ignored', `${hits.size} spatial motion transition(s)/animation(s) still exceed 150ms under prefers-reduced-motion: reduce: ${[...hits].slice(0, 4).join(', ')}`]);
    }
  };

  if (mode === 'normal' || mode === 'all') {
    await runNormalChecks();
  }
  if (mode === 'reduced' || mode === 'all') {
    runReducedMotionCheck();
  }

  return out;
}
