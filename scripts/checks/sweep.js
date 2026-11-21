async () => { const h = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
    for (let y = 0; y < h; y += 600) { window.scrollTo({ top: y, behavior: 'instant' }); await new Promise(r => setTimeout(r, 60)); }
    window.scrollTo({ top: 0, behavior: 'instant' }); }
