"""Regression, package, and failure-path tests. No third-party packages required."""
import contextlib
import hashlib
from html.parser import HTMLParser
from io import BytesIO, StringIO
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build
import color
import export
import package
import palette


def digest(value):
    # JSON turns integer step keys into strings before canonical sorting.
    value = json.loads(json.dumps(value))
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class HTMLDocument(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.elements = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class LucretiaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pal = palette.build_palette()
        cls.outputs = build.render()
        cls.baseline = json.loads((ROOT / 'tests/baseline.json').read_text())

    def test_existing_palette_is_unchanged(self):
        colors = {k: v for k, v in self.pal.items() if k != 'meta'}
        self.assertEqual(digest(colors), self.baseline['palette'])

    def test_existing_vscode_themes_are_unchanged(self):
        for kind in export.KINDS:
            with self.subTest(kind=kind):
                self.assertEqual(digest(export.vscode_theme(self.pal, kind)), self.baseline['vscode'][kind])

    def test_every_role_resolves_to_its_palette_color(self):
        for group, roles in self.pal['roles'].items():
            for name, value in roles.items():
                if name == 'scrim':
                    continue
                with self.subTest(group=group, role=name):
                    self.assertEqual(value['hex'], palette.resolve_ref(self.pal, value['ref']))

    def test_gallery_scrims_follow_palette_special_colors(self):
        pal = palette.build_palette()
        pal['special']['black'] = '#010203'
        roles = palette.build_roles(pal)
        self.assertEqual(roles['gallery']['scrim']['black'][20], 'rgba(1,2,3,0.2)')

    def test_palette_has_all_named_colors_and_monotone_scales(self):
        colors = export.palette_colors(self.pal)
        self.assertEqual(len(colors), 144)
        for name, value in colors.items():
            self.assertRegex(name, r'^[a-z][a-z0-9-]*$')
            self.assertRegex(value, r'^#[0-9A-F]{6}$')
        for scale in [self.pal['base'], self.pal['paper']['base'], *self.pal['accents'].values()]:
            self.assertEqual(list(scale), palette.STEPS)
            lightness = [color.hex_to_oklch(value['hex'])[0] for value in scale.values()]
            self.assertTrue(all(a > b for a, b in zip(lightness, lightness[1:])))

    def test_body_and_highlighter_contrast(self):
        for kind in export.KINDS:
            ui, _, _ = export.theme_context(self.pal, kind)
            with self.subTest(kind=kind):
                self.assertGreaterEqual(color.wcag(ui['tx'], ui['bg']), 7)
                self.assertGreaterEqual(abs(color.apca_lc(ui['tx'], ui['bg'])), 90)
        for name, value in self.pal['highlight'].items():
            with self.subTest(highlight=name):
                self.assertGreaterEqual(color.wcag(self.pal['special']['black'], value['hex']), 7)

    def test_color_self_test(self):
        with contextlib.redirect_stdout(StringIO()):
            self.assertTrue(color.self_test())

    def test_color_self_test_reports_numerical_failure(self):
        with patch.object(color, 'wcag', return_value=0), contextlib.redirect_stdout(StringIO()):
            self.assertFalse(color.self_test())

    def test_color_self_test_reports_gamut_failure(self):
        with patch.object(color, 'oklch_in_gamut', return_value=False), contextlib.redirect_stdout(StringIO()):
            self.assertFalse(color.self_test())

    def test_color_cli_returns_nonzero_on_failure_even_when_optimized(self):
        text = (ROOT / 'scripts/color.py').read_text()
        self.assertIn("w = wcag('#767676', '#FFFFFF')", text)
        text = text.replace("w = wcag('#767676', '#FFFFFF')", 'w = 0.0')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'color.py'
            path.write_text(text)
            result = subprocess.run([sys.executable, '-O', str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('TESTS FAILED', result.stdout)

    def test_ghostty_matches_vscode_terminal(self):
        for kind in export.KINDS:
            with self.subTest(kind=kind):
                text = self.outputs[f'dist/ghostty/Lucretia {kind.capitalize()}'].decode()
                options = {}
                slots = []
                for line in text.splitlines():
                    if line.startswith('#'):
                        continue
                    name, value = line.split(' = ', 1)
                    if name == 'palette':
                        number, value = value.split('=', 1)
                        slots.append((int(number), value))
                    else:
                        self.assertNotIn(name, options)
                        options[name] = value
                self.assertEqual(set(options), {'background', 'foreground', 'cursor-color', 'cursor-text',
                                               'selection-background', 'selection-foreground'})
                vscode = export.vscode_theme(self.pal, kind)['colors']
                expected = [vscode[f'terminal.ansi{name[0].upper()}{name[1:]}'] for name in export.ANSI_NAMES]
                self.assertEqual(slots, list(enumerate(expected)))
                self.assertEqual(options['background'], vscode['terminal.background'])
                self.assertEqual(options['foreground'], vscode['terminal.foreground'])
                self.assertEqual(options['selection-background'], vscode['editor.selectionBackground'])
                for value in options.values():
                    self.assertRegex(value, r'^#[0-9A-F]{6}$')

    def test_tokens_are_namespaced_and_complete_for_each_appearance(self):
        css = self.outputs['dist/palette/tokens.css'].decode()
        names = re.findall(r'(--[\w-]+)\s*:', css)
        self.assertTrue(names)
        self.assertTrue(all(name.startswith('--lu-') for name in names))
        sets = []
        for kind in export.KINDS:
            block = re.search(r'\[data-lu-theme="' + kind + r'"\] \{([^}]+)\}', css).group(1)
            values = dict(re.findall(r'--lu-([\w-]+):\s*([^;]+);', block))
            ui, syn, _ = export.theme_context(self.pal, kind)
            self.assertEqual(values['bg'], ui['bg'])
            self.assertEqual(values['tx'], ui['tx'])
            self.assertEqual(values['syntax-keyword'], syn['keyword'])
            sets.append(set(values))
        self.assertEqual(sets[0], sets[1])
        self.assertEqual(sets[1], sets[2])

    def test_obsidian_common_colors_are_identical_for_both_methods(self):
        for kind in export.KINDS:
            common = export.obsidian_variables(self.pal, kind)
            minimal = export.obsidian_variables(self.pal, kind, minimal=True)
            self.assertEqual(common, {key: minimal[key] for key in common})
            self.assertEqual(minimal['bg1'], common['background-primary'])
            self.assertEqual(minimal['tx1'], common['text-normal'])
            self.assertNotIn('bg1', common)
            self.assertEqual(minimal['ax1'], common['link-color'])

    def test_obsidian_declares_one_false_default_toggle_and_no_layout(self):
        for minimal in (False, True):
            css = export.obsidian_css(self.pal, minimal)
            self.assertEqual(css.count('/* @settings'), 1)
            self.assertIn('id: lucretia\n', css)
            self.assertIn('  - id: lucretia-light\n', css)
            self.assertIn('title: Lucretia Paper / Light\n', css)
            self.assertIn('type: class-toggle\n', css)
            self.assertIn('default: false\n', css)
            self.assertIn('addCommand: true\n', css)
            self.assertNotIn('!important', css)
            self.assertNotRegex(css, r'(?m)^\s+(?:font[\w-]*|margin[\w-]*|padding[\w-]*|display|width|height|position):')
            self.assertLess(css.index('body.theme-light'), css.index('body.theme-dark'))
            self.assertIn('lucretia-light {', css)
            self.assertNotIn('body.theme-dark.lucretia-light', css)

    def test_vsix_manifest_and_archive(self):
        version = (ROOT / 'VERSION').read_text().strip()
        with ZipFile(BytesIO(self.outputs['dist/vscode/lucretia-theme.vsix'])) as z:
            self.assertIsNone(z.testzip())
            names = z.namelist()
            self.assertEqual(len(names), len(set(names)))
            self.assertEqual(set(names), {'extension.vsixmanifest', '[Content_Types].xml',
                'extension/package.json', 'extension/README.md', 'extension/THIRD_PARTY_NOTICES.md',
                *{f'extension/themes/lucretia-{k}-color-theme.json' for k in export.KINDS}})
            pkg = json.loads(z.read('extension/package.json'))
            self.assertEqual(pkg['publisher'] + '.' + pkg['name'], 'sugu.lucretia-theme')
            self.assertEqual(pkg['version'], version)
            self.assertNotIn('main', pkg)
            self.assertNotIn('browser', pkg)
            self.assertNotIn('activationEvents', pkg)
            self.assertNotIn('license', pkg)
            self.assertEqual(len(pkg['contributes']['themes']), 3)
            for kind, theme in zip(export.KINDS, pkg['contributes']['themes']):
                self.assertEqual(theme['label'], f'Lucretia {kind.capitalize()}')
                self.assertEqual(theme['uiTheme'], 'vs-dark' if kind == 'dark' else 'vs')
                data = json.loads(z.read('extension/' + theme['path'].removeprefix('./')))
                self.assertEqual(digest(data), self.baseline['vscode'][kind])
            manifest = ET.fromstring(z.read('extension.vsixmanifest'))
            ns = {'v': package.VSIX_NS}
            self.assertEqual(manifest.tag, f'{{{package.VSIX_NS}}}PackageManifest')
            identity = manifest.find('v:Metadata/v:Identity', ns)
            self.assertEqual(identity.get('Id'), pkg['name'])
            self.assertEqual(identity.get('Publisher'), pkg['publisher'])
            self.assertEqual(identity.get('Version'), version)
            self.assertEqual(manifest.find('v:Installation/v:InstallationTarget', ns).get('Id'), 'Microsoft.VisualStudio.Code')
            props = {p.get('Id'): p.get('Value') for p in manifest.findall('v:Metadata/v:Properties/v:Property', ns)}
            self.assertEqual(props['Microsoft.VisualStudio.Code.Engine'], pkg['engines']['vscode'])
            for asset in manifest.findall('v:Assets/v:Asset', ns):
                self.assertIn(asset.get('Path'), names)
            types = ET.fromstring(z.read('[Content_Types].xml'))
            extensions = {item.get('Extension') for item in types}
            self.assertTrue({'.json', '.md', '.vsixmanifest'} <= extensions)
            self.assertEqual(z.read('extension/THIRD_PARTY_NOTICES.md'), (ROOT / build.NOTICE).read_bytes())

    def test_obsidian_archive_layout_version_and_contents(self):
        with ZipFile(BytesIO(self.outputs['dist/obsidian/Lucretia.zip'])) as z:
            self.assertIsNone(z.testzip())
            self.assertEqual(set(z.namelist()), {'Lucretia/manifest.json', 'Lucretia/theme.css', 'Lucretia/THIRD_PARTY_NOTICES.md'})
            manifest = json.loads(z.read('Lucretia/manifest.json'))
            self.assertEqual(manifest['name'], 'Lucretia')
            self.assertEqual(manifest['version'], (ROOT / 'VERSION').read_text().strip())
            self.assertNotIn('isDesktopOnly', manifest)  # This is a theme, not a plugin manifest.
            self.assertEqual(z.read('Lucretia/theme.css').decode(), export.obsidian_css(self.pal))
            self.assertEqual(z.read('Lucretia/THIRD_PARTY_NOTICES.md'), (ROOT / build.NOTICE).read_bytes())

    def test_all_distribution_directories_include_notice(self):
        notice = (ROOT / build.NOTICE).read_bytes()
        for folder in ('palette', 'vscode', 'ghostty', 'obsidian'):
            self.assertEqual(self.outputs[f'dist/{folder}/{build.NOTICE}'], notice)

    def test_build_is_deterministic_and_does_not_read_generated_palette(self):
        def checked_read(path, *args, **kwargs):
            self.assertNotIn('dist', path.parts)
            return original(path, *args, **kwargs)
        original = Path.read_text
        with patch.object(Path, 'read_text', checked_read):
            self.assertEqual(build.render(), self.outputs)

    def test_build_owns_only_expected_locations(self):
        for name in self.outputs:
            self.assertFalse(Path(name).is_absolute())
            self.assertNotIn('..', Path(name).parts)
            self.assertTrue(name.startswith(('dist/', 'review/')) or name == 'docs/index.html')
        self.assertEqual(len([n for n in self.outputs if n.endswith('.vsix')]), 1)
        self.assertFalse(any('node_modules' in n or 'photos' in n for n in self.outputs))

    def test_generated_files_match_working_tree(self):
        self.assertEqual(build.differences(ROOT, self.outputs), [])

    def test_finder_metadata_is_not_treated_as_a_distribution_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build.write_outputs(root, self.outputs)
            (root / 'dist/.DS_Store').write_bytes(b'Finder metadata')
            self.assertEqual(build.differences(root, self.outputs), [])

    def test_check_detects_missing_stale_extra_and_corrupt_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build.write_outputs(root, self.outputs)
            (root / 'dist/palette/palette.json').unlink()
            (root / 'dist/ghostty/Lucretia Light').write_text('background = #000000\n')
            (root / 'dist/vscode/old.vsix').write_bytes(b'old')
            (root / 'dist/vscode/lucretia-theme.vsix').write_bytes(b'broken ZIP')
            errors = build.differences(root, self.outputs)
            self.assertEqual(set(errors), {'Missing: dist/palette/palette.json',
                'Stale: dist/ghostty/Lucretia Light', 'Unexpected output: dist/vscode/old.vsix',
                'Stale: dist/vscode/lucretia-theme.vsix'})

    def test_build_removes_obsolete_outputs_but_keeps_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'dist/vsix').mkdir(parents=True)
            (root / 'dist/vsix/old.vsix').write_bytes(b'old')
            (root / 'docs').mkdir()
            (root / 'docs/style.css').write_text('do not replace me')
            (root / 'README.md').write_text('source')
            build.write_outputs(root, self.outputs)
            self.assertFalse((root / 'dist/vsix').exists())
            self.assertEqual((root / 'docs/style.css').read_text(), 'do not replace me')
            self.assertEqual((root / 'README.md').read_text(), 'source')
            self.assertEqual(build.differences(root, self.outputs), [])

    def test_check_cli_is_non_destructive_and_returns_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / 'scripts', root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
            for name in ('VERSION', build.NOTICE):
                shutil.copyfile(ROOT / name, root / name)
            build.write_outputs(root, self.outputs)
            target = root / 'dist/vscode/lucretia-theme.vsix'
            target.write_bytes(b'deliberately broken')
            result = subprocess.run([sys.executable, str(root / 'scripts/build.py'), '--check'],
                                    cwd=directory, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('Stale: dist/vscode/lucretia-theme.vsix', result.stderr)
            self.assertEqual(target.read_bytes(), b'deliberately broken')

    def test_invalid_version_fails_before_changing_outputs(self):
        original = Path.read_text
        def read(path, *args, **kwargs):
            return 'not-a-version' if path.name == 'VERSION' else original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', read):
            with self.assertRaisesRegex(ValueError, 'VERSION'):
                build.render()

    def test_preview_starts_in_paper_and_includes_every_color(self):
        text = self.outputs['docs/index.html'].decode()
        self.assertNotIn('@@', text)
        doc = HTMLDocument(text)
        self.assertIn(('html', {'lang': 'en', 'data-lu-theme': 'paper'}), doc.elements)
        choices = [attrs for tag, attrs in doc.elements if 'data-theme' in attrs]
        self.assertEqual([c['data-theme'] for c in choices], list(export.KINDS))
        self.assertEqual([c['data-theme'] for c in choices if c['aria-pressed'] == 'true'], ['paper'])
        self.assertTrue(all('disabled' in c for c in choices))
        full = [a for _, a in doc.elements if a.get('class') == 'scale-color']
        self.assertEqual(len(full), 144)
        self.assertCountEqual([a['data-copy'] for a in full], export.palette_colors(self.pal).values())
        self.assertFalse(any(tag == 'details' and 'open' in attrs for tag, attrs in doc.elements))

    def test_html_local_resources_exist_and_preview_has_no_external_assets(self):
        for name, content in self.outputs.items():
            if not name.endswith('.html'):
                continue
            document = HTMLDocument(content.decode())
            for tag, attrs in document.elements:
                for key in ('src', 'href'):
                    ref = attrs.get(key)
                    if not ref:
                        continue
                    parts = urlsplit(ref)
                    if parts.scheme or parts.netloc:
                        if name == 'docs/index.html':
                            self.assertNotIn(tag, ('script', 'link', 'img', 'iframe'))
                        continue
                    if not parts.path:
                        continue
                    target = (ROOT / name).parent / unquote(parts.path)
                    with self.subTest(page=name, ref=ref):
                        self.assertTrue(target.is_file(), f'Missing link target: {target}')
            for ref in re.findall(r"url\(['\"]?([^)\'\"\s]+)", content.decode()):
                parts = urlsplit(ref)
                if not parts.scheme and parts.path:
                    self.assertTrue(((ROOT / name).parent / unquote(parts.path)).is_file(), ref)


    def test_documented_colors_and_links(self):
        text = (ROOT / 'README.md').read_text()
        for kind in export.KINDS:
            ui, _, _ = export.theme_context(self.pal, kind)
            self.assertIn(f"| {kind.capitalize()} | `{ui['bg']}` | `{ui['tx']}` |", text)
        for path in (ROOT / 'README.md', ROOT / 'DEVELOPMENT.md', ROOT / 'demo/README.md'):
            for ref in re.findall(r'\]\(([^)]+)\)', path.read_text()):
                parts = urlsplit(ref)
                if not parts.scheme and parts.path:
                    self.assertTrue((path.parent / unquote(parts.path)).is_file(), ref)


if __name__ == '__main__':
    unittest.main(verbosity=2)
