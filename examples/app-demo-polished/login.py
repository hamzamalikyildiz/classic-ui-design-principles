"""Login helper for scripts/render.py --routes routes.json."""


def login(page, base_url):
    target = f"{base_url.rstrip('/')}/login"
    page.goto(target)
    page.wait_for_selector('input[name="email"]')
    page.fill('input[name="email"]', 'cagla.inanc@kovan.io')
    page.fill('input[name="password"]', 'kovan-demo-2026')
    page.click('button[type="submit"]')
    page.wait_for_url('**/cv**', timeout=5000)
