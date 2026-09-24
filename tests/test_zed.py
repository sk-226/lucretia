import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from export import ANSI_NAMES, KINDS, ansi, selection_color, theme_context
from palette import build_palette
from zed_theme import SCHEMA, zed_theme, zed_theme_family


class ZedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pal = build_palette()
        cls.family = zed_theme_family(cls.pal)

    def test_family_has_three_named_appearances(self):
        self.assertEqual(self.family['$schema'], SCHEMA)
        self.assertEqual(self.family['name'], 'Lucretia')
        self.assertEqual(self.family['author'], 'sk-226')
        self.assertEqual([t['name'] for t in self.family['themes']],
                         ['Lucretia Light', 'Lucretia Dark', 'Lucretia Paper'])
        self.assertEqual([t['appearance'] for t in self.family['themes']],
                         ['light', 'dark', 'light'])
        with self.assertRaisesRegex(ValueError, 'Unknown appearance'):
            zed_theme(self.pal, 'unknown')

    def test_syntax_tiers_and_typography(self):
        for kind, theme in zip(KINDS, self.family['themes']):
            with self.subTest(kind=kind):
                ui, syn, _ = theme_context(self.pal, kind)
                syntax = theme['style']['syntax']
                for capture in ('variable', 'variable.special', 'variable.parameter',
                                'parameter', 'property'):
                    self.assertEqual(syntax[capture], dict(color=ui['tx'],
                                     font_style='normal', font_weight=400))
                for capture, role in (('function', 'definition'), ('type', 'definition'),
                                      ('keyword', 'keyword'), ('string', 'string'),
                                      ('number', 'number'), ('constant', 'number'),
                                      ('punctuation.bracket', 'operator')):
                    self.assertEqual(syntax[capture]['color'], syn[role])
                for capture in ('comment', 'comment.doc', 'comment.documentation'):
                    self.assertEqual(syntax[capture]['color'], syn['comment'])
                    self.assertEqual(syntax[capture]['font_style'], 'italic')
                self.assertEqual(syntax['emphasis']['font_style'], 'italic')
                for capture in ('title', 'emphasis.strong'):
                    self.assertEqual(syntax[capture]['font_weight'], 700)
                    self.assertEqual(syntax[capture]['color'], ui['tx'])
                # Zed's v0.2.0 syntax schema has no underline/strikethrough fields.
                for token in syntax.values():
                    self.assertLessEqual(set(token), {'color', 'background_color',
                                         'font_style', 'font_weight'})

    def test_ui_selection_and_ansi_use_shared_palette(self):
        for kind, theme in zip(KINDS, self.family['themes']):
            with self.subTest(kind=kind):
                ui, _, _ = theme_context(self.pal, kind)
                style = theme['style']
                for key in ('background', 'editor.background', 'editor.gutter.background',
                            'terminal.background', 'tab.active_background'):
                    self.assertEqual(style[key], ui['bg'])
                self.assertEqual(style['panel.background'], ui['bg-2'])
                self.assertEqual(style['players'][0]['cursor'], ui['tx'])
                self.assertEqual(style['players'][0]['selection'],
                                 selection_color(self.pal, kind != 'dark'))
                colors = ansi(self.pal, kind)
                for name in ANSI_NAMES:
                    key = 'bright_' + name[6:].lower() if name.startswith('bright') else name
                    self.assertEqual(style[f'terminal.ansi.{key}'], colors[name])
                self.assertEqual(len([k for k in style if k.startswith('terminal.ansi.dim_')]), 8)
                for key in ('surface.background', 'elevated_surface.background',
                            'panel.background', 'title_bar.background'):
                    if kind == 'paper':
                        self.assertNotEqual(style[key], '#FFFFFF')

    def test_colors_and_style_values_are_serializable(self):
        family = json.loads(json.dumps(self.family))
        for theme in family['themes']:
            style = theme['style']
            self.assertEqual(style['background.appearance'], 'opaque')
            def check_color(value):
                self.assertRegex(value, r'^#[0-9A-F]{6}([0-9A-F]{2})?$')
            for key, value in style.items():
                if key not in ('syntax', 'players', 'accents', 'background.appearance'):
                    check_color(value)
            for value in style['accents']:
                check_color(value)
            for player in style['players']:
                self.assertEqual(set(player), {'cursor', 'background', 'selection'})
                for value in player.values():
                    check_color(value)
            for token in style['syntax'].values():
                check_color(token['color'])
                self.assertIn(token['font_style'], ('normal', 'italic', 'oblique'))
                self.assertIn(token['font_weight'], range(100, 1000, 100))
                if 'background_color' in token:
                    check_color(token['background_color'])

    def test_fresh_palette_and_json_keys_are_supported_without_mutation(self):
        pal = copy.deepcopy(self.pal)
        pal['roles']['syntax_paper']['keyword']['hex'] = '#123456'
        pal['accents']['blue'][600]['hex'] = '#654321'
        before = copy.deepcopy(pal)
        theme = zed_theme(pal, 'paper')
        self.assertEqual(theme['style']['syntax']['keyword']['color'], '#123456')
        self.assertEqual(theme['style']['terminal.ansi.blue'], '#654321')
        self.assertEqual(pal, before)
        self.assertEqual(zed_theme_family(json.loads(json.dumps(pal))), zed_theme_family(pal))

    def test_generated_theme_extension_and_notices_match_sources(self):
        folder = ROOT / 'extensions/zed'
        version = (ROOT / 'VERSION').read_text().strip()
        self.assertEqual((folder / 'themes/lucretia.json').read_bytes(),
                         (json.dumps(self.family, ensure_ascii=False, indent=2) + '\n').encode())
        manifest = (folder / 'extension.toml').read_text()
        self.assertIn('id = "lucretia-theme"\n', manifest)
        self.assertIn(f'version = "{version}"\n', manifest)
        self.assertIn('schema_version = 1\n', manifest)
        self.assertEqual((folder / 'THIRD_PARTY_NOTICES.md').read_bytes(),
                         (ROOT / 'THIRD_PARTY_NOTICES.md').read_bytes())
        self.assertEqual({p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()},
                         {'extension.toml', 'themes/lucretia.json', 'README.md',
                          'THIRD_PARTY_NOTICES.md'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
