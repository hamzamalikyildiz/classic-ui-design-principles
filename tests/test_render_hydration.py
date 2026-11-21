"""Tests for render.py hydration & DOM stability waiting (--wait-for, hydration-mismatch)."""
import contextlib
import http.server
import importlib.util
import io
import pathlib
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('render', ROOT / 'scripts' / 'render.py')
rd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rd)


def _browser_available():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            rd.launch_browser(p).close()
        return True
    except BaseException:
        return False


class _MinimalMockPage:
    """Mock page without wait_for_load_state or wait_for_selector to verify backward compatibility."""

    def __init__(self):
        self.visited = []
        self.timeouts = []
        self.evaluated = []

    def goto(self, uri):
        self.visited.append(uri)

    def wait_for_timeout(self, ms):
        self.timeouts.append(ms)

    def evaluate(self, expr):
        # Single-argument evaluate only (raises TypeError if 2 args passed, just like _FakePage in test_render_url.py)
        self.evaluated.append(expr)
        if expr == 'document.documentElement.scrollHeight':
            return 900
        return []


class HydrationUnitTests(unittest.TestCase):
    def test_cli_wait_for_option_parses_into_render_options(self):
        opts = rd.parse_options([
            '--url', 'http://localhost:3000/app',
            '--out', 'app.png',
            '--wait-for', '[data-ready="true"]',
            '--check',
        ])
        self.assertEqual(opts.wait_for, '[data-ready="true"]')
        self.assertTrue(opts.check)
        help_text = rd.build_parser().format_help()
        self.assertIn('--wait-for SELECTOR', help_text)

    def test_mock_page_backward_compatibility_without_load_state_or_selector(self):
        page = _MinimalMockPage()
        rd._prepare_page(page, 'http://localhost:3000/test', dark=True, wait_for='[data-ready]')
        self.assertEqual(page.visited, ['http://localhost:3000/test'])
        self.assertIn(500, page.timeouts)
        self.assertIn(800, page.timeouts)
        self.assertIn("document.documentElement.classList.add('dark')", page.evaluated)
        self.assertIn(rd.SCROLL_SWEEP_JS, page.evaluated)

    def test_wait_for_hydration_call_sequence_and_soft_networkidle_fallback(self):
        events = []
        page = mock.MagicMock()

        def fake_load_state(state, timeout=None):
            events.append(('load_state', state, timeout))
            if state == 'networkidle':
                raise TimeoutError('SSE stream kept connection open')

        def fake_evaluate(script, arg=None):
            events.append(('evaluate', arg))
            return {'timedOut': False, 'detected': True, 'elapsedMs': 520}

        def fake_wait_selector(selector, state=None, timeout=None):
            events.append(('wait_selector', selector, state, timeout))

        page.wait_for_load_state.side_effect = fake_load_state
        page.evaluate.side_effect = fake_evaluate
        page.wait_for_selector.side_effect = fake_wait_selector

        rd.wait_for_hydration(page, wait_for='[data-ready]', quiet_ms=500, max_wait_ms=5000)

        self.assertEqual(events[0], ('load_state', 'load', 5000))
        self.assertEqual(events[1], ('load_state', 'networkidle', 2500))
        self.assertEqual(events[2], ('evaluate', {'quietMs': 500, 'maxWaitMs': 5000, 'checkFramework': True}))
        self.assertEqual(events[3], ('wait_selector', '[data-ready]', 'visible', 5000))
        page.wait_for_timeout.assert_not_called()

    def test_wait_for_dom_stability_and_run_actions_order(self):
        order = []
        page = mock.MagicMock()

        def fake_eval(script, arg=None):
            if isinstance(arg, dict) and 'quietMs' in arg:
                order.append(('stability', arg['quietMs'], arg['maxWaitMs']))
                return {'timedOut': False, 'detected': False, 'elapsedMs': 300}
            return []

        page.evaluate.side_effect = fake_eval
        page.fill.side_effect = lambda sel, val: order.append(('fill', sel, val))
        page.click.side_effect = lambda sel: order.append(('click', sel))

        rd.run_actions(page, [
            {'type': 'fill', 'selector': '#email', 'value': 'a@b.com'},
            {'type': 'click', 'selector': '#submit'},
        ])

        self.assertEqual(order, [
            ('stability', 300, 3000),
            ('fill', '#email', 'a@b.com'),
            ('stability', 300, 3000),
            ('click', '#submit'),
            ('stability', 300, 3000),
        ])

    def test_hydration_mismatch_separated_from_js_errors(self):
        page = _MinimalMockPage()
        console_errors = [
            'Error: Hydration failed because the initial UI does not match what was rendered on the server.',
            'Warning: Text content did not match. Server: "0" Client: "1"',
            'Uncaught TypeError: Cannot read properties of undefined',
        ]
        with mock.patch.object(rd, 'run_axe', return_value=[]):
            findings = rd._run_dom_checks(
                page,
                None,
                'http://localhost:3000/',
                rd.RenderOptions(url='http://localhost:3000/', check=True),
                console_errors,
                [],
            )
        by_rule = {rule: (sev, msg) for sev, rule, msg in findings}
        self.assertIn('hydration-mismatch', by_rule)
        self.assertEqual(by_rule['hydration-mismatch'][0], 'WARN')
        self.assertIn('2 hydration mismatch(es)', by_rule['hydration-mismatch'][1])
        self.assertIn('js-errors', by_rule)
        self.assertIn('1 console/page error(s)', by_rule['js-errors'][1])
        self.assertNotIn('Hydration failed', by_rule['js-errors'][1])


# Late-hydrating page:
# Renders an SSR skeleton with an input and button immediately.
# If anything interacts with the input or button BEFORE 350ms hydration completes,
# it logs a console.error("Hydration failed: server HTML did not match").
# At 350ms, it attaches a React 18 __reactContainer$ key on #root, replaces the SSR DOM,
# and sets data-ready="true".
LATE_HYDRATE_HTML = b"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link rel="icon" href="data:,">
  <title>Late Hydration App</title>
  <style>
    body { font-family: sans-serif; margin: 0; padding: 24px; background: #fff; color: #111; }
    .box { max-width: 480px; padding: 16px; border: 1px solid #ccc; border-radius: 8px; }
    button, input { min-height: 40px; padding: 8px 12px; font-size: 16px; }
    button:focus-visible, input:focus-visible { outline: 2px solid #2563eb; }
  </style>
</head>
<body>
  <main id="root">
    <div class="box">
      <h1>Account Profile</h1>
      <label for="name-input">Full Name</label>
      <input id="name-input" type="text" value="" placeholder="Enter name">
      <button id=" ping-btn" type="button">Verify</button>
      <p id="status-text">SSR Skeleton</p>
    </div>
  </main>
  <script>
    window.__hydrated = false;
    const ssrInput = document.getElementById('name-input');
    const ssrBtn = document.querySelector('button');
    const trapEarlyInteraction = () => {
      if (!window.__hydrated) {
        console.error('Error: Hydration failed: server HTML did not match client DOM due to early interaction');
      }
    };
    ssrInput.addEventListener('input', trapEarlyInteraction);
    ssrInput.addEventListener('focus', trapEarlyInteraction);
    ssrBtn.addEventListener('click', trapEarlyInteraction);
    ssrBtn.addEventListener('focus', trapEarlyInteraction);

    setTimeout(() => {
      const root = document.getElementById('root');
      root['__reactContainer$xyz123'] = { tag: 3 };
      root.innerHTML = `
        <div class="box" data-ready="true">
          <h1>Account Profile</h1>
          <label for="name-input">Full Name</label>
          <input id="name-input" type="text" value="" placeholder="Enter name">
          <button id="action-btn" type="button">Verify</button>
          <p id="status-text">Hydrated Ready</p>
        </div>
      `;
      window.__hydrated = true;
      const btn = document.getElementById('action-btn');
      btn.addEventListener('click', () => {
        document.getElementById('status-text').textContent = 'Verified: ' + document.getElementById('name-input').value;
      });
    }, 350);
  </script>
</body>
</html>
"""

REAL_MISMATCH_HTML = b"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link rel="icon" href="data:,">
  <title>Broken Hydration App</title>
  <style>
    body { font-family: sans-serif; margin: 0; padding: 24px; background: #fff; color: #111; }
    .box { max-width: 480px; padding: 16px; border: 1px solid #ccc; border-radius: 8px; }
  </style>
</head>
<body>
  <main id="root" data-ready="true">
    <div class="box">
      <h1>Dashboard</h1>
      <p>Server timestamp mismatch</p>
    </div>
  </main>
  <script>
    const root = document.getElementById('root');
    root['__reactContainer$err999'] = { tag: 3 };
    console.error('Error: Hydration failed because the initial UI does not match what was rendered on the server.');
  </script>
</body>
</html>
"""


@unittest.skipUnless(_browser_available(), 'Playwright/Chromium not available')
class LiveHydrationIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        routes = {
            '/late-hydrate': (200, 'text/html; charset=utf-8', LATE_HYDRATE_HTML),
            '/real-mismatch': (200, 'text/html; charset=utf-8', REAL_MISMATCH_HTML),
        }

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path in routes:
                    status, ctype, body = routes[self.path]
                    self.send_response(status)
                    self.send_header('Content-Type', ctype)
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, *args):
                pass

        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.base_url = f'http://127.0.0.1:{cls.server.server_address[1]}'
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_late_hydrating_page_waits_before_actions_and_produces_no_false_hydration_mismatch(self):
        url = f'{self.base_url}/late-hydrate'
        with tempfile.TemporaryDirectory() as d:
            png = pathlib.Path(d) / 'late.png'
            opts = rd.RenderOptions(
                url=url,
                out=str(png),
                check=True,
                wait_for='[data-ready="true"]',
                actions=[
                    {'type': 'fill', 'selector': '#name-input', 'value': 'Ada Lovelace'},
                    {'type': 'click', 'selector': '#action-btn'},
                ],
            )
            with mock.patch.object(rd, 'find_axe', return_value=None):
                res = rd.render(opts)

            self.assertTrue(png.is_file())
            rules = [f[1] for f in res['findings']]
            self.assertNotIn('hydration-mismatch', rules, f"Unexpected findings: {res['findings']}")
            self.assertNotIn('js-errors', rules, f"Unexpected console errors: {res['console_errors']}")

    def test_real_hydration_mismatch_is_reported_under_hydration_mismatch_rule(self):
        url = f'{self.base_url}/real-mismatch'
        with tempfile.TemporaryDirectory() as d:
            png = pathlib.Path(d) / 'mismatch.png'
            stdout = io.StringIO()
            with mock.patch.object(rd, 'find_axe', return_value=None), \
                 contextlib.redirect_stdout(stdout):
                rd.main(['--url', url, '--out', str(png), '--wait-for', '[data-ready="true"]', '--check'])

            out = stdout.getvalue()
            self.assertIn('[WARN] hydration-mismatch:', out)
            self.assertIn('Hydration failed because the initial UI does not match', out)
            self.assertNotIn('[WARN] js-errors:', out)


if __name__ == '__main__':
    unittest.main()
