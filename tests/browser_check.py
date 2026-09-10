"""Check rendered styles and interactions in Chromium, without running native apps.

The generated page and its local CSS/JS are loaded directly into a blank page.
No server is needed. Clipboard success is stubbed; failure uses real text selection.
"""
import argparse
from io import BytesIO
from pathlib import Path
import sys
import unittest
from zipfile import ZipFile

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from export import KINDS, theme_context, obsidian_variables
from palette import build_palette


def rgb(value):
    return 'rgb(' + ', '.join(str(int(value[i:i+2], 16)) for i in (1, 3, 5)) + ')'


class BrowserTests(unittest.TestCase):
    chromium = None
    screenshot_dir = None

    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        options = {'headless': True}
        if cls.chromium:
            options['executable_path'] = cls.chromium
        cls.browser = cls.playwright.chromium.launch(**options)
        cls.pal = build_palette()
        cls.html = (ROOT / 'docs/index.html').read_text()
        # The core suite checks that both local resource references exist.
        cls.html = cls.html.replace('<link rel="stylesheet" href="style.css">', '')
        cls.html = cls.html.replace('<script src="preview.js" defer></script>', '')
        cls.css = (ROOT / 'docs/style.css').read_text()
        cls.js = (ROOT / 'docs/preview.js').read_text()
        print(f'Chromium {cls.browser.version}. Direct document loading; no URL navigation.')

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.page = self.browser.new_page(viewport={'width': 1320, 'height': 1100})
        self.page.set_default_timeout(5000)
        self.errors = []
        self.requests = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('request', lambda request: self.requests.append(request.url))
        self.page.set_content(self.html)
        self.page.add_style_tag(content=self.css)
        self.page.add_script_tag(content=self.js)

    def tearDown(self):
        self.page.close()
        self.assertEqual(self.errors, [])
        self.assertEqual(self.requests, [])

    def screenshot(self, name):
        if self.screenshot_dir:
            self.page.screenshot(path=str(self.screenshot_dir / name), full_page=True)

    def test_three_appearances_and_live_color_codes(self):
        self.assertEqual(self.page.locator('html').get_attribute('data-lu-theme'), 'paper')
        for kind in ('paper', 'light', 'dark'):
            with self.subTest(kind=kind):
                self.page.locator(f'[data-theme="{kind}"]').click()
                ui, syn, _ = theme_context(self.pal, kind)
                self.assertEqual(self.page.evaluate('getComputedStyle(document.body).backgroundColor'), rgb(ui['bg']))
                self.assertEqual(self.page.evaluate('getComputedStyle(document.body).color'), rgb(ui['tx']))
                self.assertEqual(self.page.locator('pre .keyword').first.evaluate('el => getComputedStyle(el).color'), rgb(syn['keyword']))
                self.assertEqual(self.page.locator('[data-theme][aria-pressed="true"]').count(), 1)
                for role in ('bg', 'tx', 'link'):
                    button = self.page.locator(f'[data-token="{role}"]')
                    self.assertEqual(button.get_attribute('data-copy'), ui[role])
                    self.assertEqual(button.locator('code').inner_text(), ui[role])
                self.screenshot(f'{kind}-desktop.png')

    def test_keyboard_operation_and_focus(self):
        light = self.page.locator('[data-theme="light"]')
        light.focus()
        self.page.keyboard.press('Enter')
        self.assertEqual(self.page.locator('html').get_attribute('data-lu-theme'), 'light')
        self.page.keyboard.press('Tab')
        self.assertTrue(self.page.locator('[data-theme="dark"]').evaluate('el => el === document.activeElement'))
        self.page.keyboard.press('Space')
        self.assertEqual(self.page.locator('html').get_attribute('data-lu-theme'), 'dark')
        self.assertTrue(self.page.locator('[data-theme="dark"]').evaluate('el => el.matches(":focus-visible")'))
        self.assertNotEqual(self.page.locator('[data-theme="dark"]').evaluate('el => getComputedStyle(el).outlineStyle'), 'none')

    def test_copy_success_uses_current_value_with_stubbed_clipboard(self):
        self.page.evaluate('''() => {
          window.copiedValues = [];
          Object.defineProperty(navigator, 'clipboard', {configurable: true,
            value: {writeText: async value => { window.copiedValues.push(value); }}});
        }''')
        expected = []
        for kind in KINDS:
            self.page.locator(f'[data-theme="{kind}"]').click()
            for token in ('bg', 'link', 'accent-green'):
                button = self.page.locator(f'[data-token="{token}"]')
                value = button.get_attribute('data-copy')
                button.click()
                self.page.wait_for_function('(value) => document.querySelector(".copy-status").textContent === `Copied ${value}.`', arg=value)
                expected.append(value)
        self.page.locator('summary').click()
        swatch = self.page.locator('.scale-color').last
        expected.append(swatch.get_attribute('data-copy'))
        swatch.click()
        self.page.wait_for_function('(n) => window.copiedValues.length === n', arg=len(expected))
        self.assertEqual(self.page.evaluate('copiedValues'), expected)

    def test_clipboard_denial_and_absence_select_text_without_claiming_copy(self):
        for implementation in ('undefined', '{writeText: async () => {throw new Error("denied");}}'):
            self.page.evaluate(f'''() => Object.defineProperty(navigator, 'clipboard',
                {{configurable: true, value: {implementation}}})''')
            for kind in KINDS:
                self.page.locator(f'[data-theme="{kind}"]').click()
                button = self.page.locator('[data-token="bg"]')
                value = button.get_attribute('data-copy')
                button.click()
                self.page.wait_for_function('(v) => document.querySelector(".copy-status").textContent.startsWith(`Selected ${v}.`)', arg=value)
                self.assertEqual(self.page.evaluate('getSelection().toString()'), value)
                self.assertNotIn('Copied', self.page.locator('.copy-status').inner_text())

    def test_delayed_clipboard_denial_after_theme_change(self):
        self.page.evaluate('''() => Object.defineProperty(navigator, 'clipboard', {
            configurable: true, value: {writeText: () => new Promise((resolve, reject) => {
                window.rejectCopy = reject;
            })}
        })''')
        self.page.locator('[data-token="bg"]').click()
        self.page.locator('[data-theme="dark"]').click()
        self.page.evaluate('async () => { window.rejectCopy(new Error("denied")); await Promise.resolve(); }')
        self.assertEqual(self.page.locator('.copy-status').inner_text(), '')
        self.assertEqual(self.page.evaluate('getSelection().toString()'), '')

    def test_narrow_layouts_and_expanded_palette(self):
        for width in (320, 390, 768, 1320):
            self.page.set_viewport_size({'width': width, 'height': 900})
            for kind in KINDS:
                self.page.locator(f'[data-theme="{kind}"]').click()
                for expanded in (False, True):
                    self.page.locator('details').evaluate('(el, open) => { el.open = open; }', expanded)
                    with self.subTest(width=width, kind=kind, expanded=expanded):
                        sizes = self.page.evaluate('({width: innerWidth, scroll: document.documentElement.scrollWidth})')
                        self.assertLessEqual(sizes['scroll'], sizes['width'])
                        for button in self.page.locator('[data-theme]').all():
                            rect = button.bounding_box()
                            self.assertGreaterEqual(rect['height'], 44)
            if width == 390:
                self.page.locator('details').evaluate('el => { el.open = false; }')
                self.screenshot('paper-mobile.png')

    def test_without_javascript_still_shows_paper_and_color_values(self):
        page = self.browser.new_page(java_script_enabled=False)
        try:
            page.set_content(self.html.replace('</head>', '<style>' + self.css + '</style></head>'),
                             wait_until='domcontentloaded')
            self.assertTrue(page.locator('noscript').is_visible())
            self.assertTrue(page.locator('[data-theme="paper"]').is_disabled())
            self.assertEqual(page.locator('[data-token="bg"] code').inner_text(), '#F8F5EB')
            self.assertTrue(page.locator('.note').is_visible())
        finally:
            page.close()

    def test_obsidian_css_appearance_transitions_and_host_typography(self):
        # This is a controlled host fixture, not Obsidian or Minimal itself.
        with ZipFile(BytesIO((ROOT / 'dist/obsidian/Lucretia.zip').read_bytes())) as z:
            standalone = z.read('Lucretia/theme.css').decode()
        minimal = (ROOT / 'dist/obsidian/lucretia-minimal.css').read_text()
        for is_minimal, css in ((False, standalone), (True, minimal)):
            self.page.set_content('''<!doctype html><html><head><style>
                body { font-family: monospace; font-size: 19px; margin: 23px;
                  background: var(--background-primary); color: var(--text-normal); }
                body.theme-light.test-preset, body.theme-dark.test-preset {
                  --bg1: #ff0000; --text-normal: #ff0000; }
                mark {background: var(--text-highlight-bg)}
                </style></head><body><h1>Reading</h1><p>Text <mark>highlight</mark></p>
                <span class="hl-blue">Blue</span></body></html>''')
            self.page.add_style_tag(content=css)
            for mode, light, kind in [('light', False, 'paper'), ('light', True, 'light'),
                                       ('dark', True, 'dark'), ('dark', False, 'dark'),
                                       ('light', False, 'paper'), ('light', True, 'light')]:
                classes = f'theme-{mode}' + (' lucretia-light' if light else '') + (' test-preset' if is_minimal else '')
                self.page.evaluate('(classes) => {document.body.className = classes;}', classes)
                expected = obsidian_variables(self.pal, kind, is_minimal)
                actual = self.page.evaluate('''() => {
                    const s = getComputedStyle(document.body);
                    return {bg: s.backgroundColor, color: s.color, font: s.fontSize,
                      margin: s.marginTop, family: s.fontFamily,
                      vars: Object.fromEntries([...s].filter(k => k.startsWith('--')).map(k => [k.slice(2), s.getPropertyValue(k).trim()]))};
                }''')
                with self.subTest(minimal=is_minimal, mode=mode, light=light):
                    self.assertEqual(actual['bg'], rgb(expected['background-primary']))
                    self.assertEqual(actual['color'], rgb(expected['text-normal']))
                    self.assertEqual(actual['font'], '19px')
                    self.assertEqual(actual['margin'], '23px')
                    self.assertEqual(actual['family'], 'monospace')
                    for name, value in expected.items():
                        self.assertEqual(actual['vars'][name], value, name)
                    self.assertEqual(self.page.locator('mark').evaluate('el => getComputedStyle(el).color'), rgb(self.pal['special']['black']))
                    self.assertEqual(self.page.locator('.hl-blue').evaluate('el => getComputedStyle(el).backgroundColor'), rgb(self.pal['highlight']['blue']['hex']))

    def test_obsidian_mobile_paper_overrides_do_not_leak_into_light(self):
        from export import obsidian_css, rgba
        for minimal in (False, True):
            self.page.set_content('<html><head></head><body></body></html>')
            self.page.add_style_tag(content=obsidian_css(self.pal, minimal))
            for mode, light, kind in [('light', False, 'paper'), ('light', True, 'light'),
                                      ('dark', True, 'dark'), ('light', False, 'paper')]:
                classes = f'theme-{mode} is-mobile' + (' lucretia-light' if light else '')
                self.page.evaluate('(classes) => {document.body.className = classes;}', classes)
                expected = obsidian_variables(self.pal, kind, minimal)
                if kind == 'paper':
                    ui, _, _ = theme_context(self.pal, kind)
                    expected['workspace-background-translucent'] = rgba(ui['bg'], '0.84')
                    expected['background-modifier-cover'] = rgba(ui['tx'], '0.22')
                for name in ('workspace-background-translucent', 'background-modifier-cover'):
                    actual = self.page.evaluate('(name) => getComputedStyle(document.body).getPropertyValue(`--${name}`).trim()', name)
                    self.assertEqual(actual, expected[name])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chromium', help='Path to an existing Chromium executable.')
    parser.add_argument('--screenshots', type=Path, help='Save preview screenshots to this directory.')
    args = parser.parse_args()
    BrowserTests.chromium = args.chromium
    BrowserTests.screenshot_dir = args.screenshots
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BrowserTests))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
