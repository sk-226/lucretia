"""Generated Vim files and optional native-editor checks. Standard library only."""
from io import BytesIO
from pathlib import Path
import itertools
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build
from export import ANSI_NAMES, KINDS, ansi, palette_colors, theme_context, vscode_theme
from palette import build_palette
from vim_theme import vim_theme


def highlights(text):
    """Read the static definitions, with links kept separate from attributes."""
    definitions, links = {}, {}
    for line in text.splitlines():
        parts = line.split()
        if parts[:2] == ['highlight!', 'link']:
            links[parts[2]] = parts[3]
        elif parts[:1] == ['highlight'] and parts[1] != 'clear':
            definitions[parts[1]] = dict(item.split('=', 1) for item in parts[2:])
    return definitions, links


def vim_string(value):
    return "'" + str(value).replace("'", "''") + "'"


class VimExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pal = build_palette()
        cls.outputs = build.render()

    def test_three_self_contained_schemes(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                text = self.outputs[f'dist/vim/colors/lucretia-{kind}.vim'].decode()
                self.assertEqual(text, vim_theme(self.pal, kind))
                self.assertIn(f"let g:colors_name = 'lucretia-{kind}'", text)
                self.assertIn(f'set background={"dark" if kind == "dark" else "light"}', text)
                self.assertNotRegex(text, r'(?m)^\s*(?:lua|source|runtime!?|autocmd|function!?)\b')
                self.assertNotIn('set termguicolors', text)
                # @ groups are Neovim-only. Vim does not accept these names.
                common, nvim = text.split("if has('nvim')")
                self.assertNotIn('highlight! link @', common)
                self.assertIn('highlight! link @variable Identifier', nvim)

    def test_palette_and_existing_ui_mapping(self):
        mapping = {'Normal': ('editor.foreground', 'editor.background'),
                   'Pmenu': ('quickInput.foreground', 'quickInput.background'),
                   'PmenuSel': ('list.focusForeground', 'list.focusBackground')}
        for kind in KINDS:
            with self.subTest(kind=kind):
                text = vim_theme(self.pal, kind)
                defs, _ = highlights(text)
                vscode = vscode_theme(self.pal, kind)['colors']
                for group, (fg, bg) in mapping.items():
                    self.assertEqual(defs[group]['guifg'], vscode[fg])
                    self.assertEqual(defs[group]['guibg'], vscode[bg])
                self.assertLessEqual(set(re.findall(r'#[0-9A-F]{6}', text)),
                                     set(palette_colors(self.pal).values()))

    def test_syntax_tiers_and_prose(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                ui, syn, md = theme_context(self.pal, kind)
                defs, links = highlights(vim_theme(self.pal, kind))
                for group, role in {'Function': 'definition', 'Type': 'definition',
                                    'Statement': 'keyword', 'String': 'string',
                                    'Constant': 'number', 'Operator': 'operator',
                                    'Comment': 'comment'}.items():
                    self.assertEqual(defs[group]['guifg'], syn[role])
                self.assertEqual(defs['Identifier']['guifg'], ui['tx'])
                self.assertEqual(defs['Identifier']['guibg'], 'NONE')
                for capture in ('variable', 'variable.builtin', 'variable.parameter',
                                'variable.member', 'property', 'function.call',
                                'function.method.call', 'lsp.type.variable',
                                'lsp.type.parameter', 'lsp.type.property'):
                    self.assertEqual(links[f'@{capture}'], 'Identifier')
                self.assertEqual(defs['@lsp.type.function']['guifg'], 'NONE')
                self.assertEqual(links['@lsp.typemod.function.definition'], 'Function')
                self.assertEqual(defs['Comment']['gui'], 'italic')
                self.assertEqual(defs['LucretiaHeading']['guifg'], md['heading'])
                self.assertEqual(defs['LucretiaHeading']['gui'], 'bold')
                for level in range(1, 7):
                    self.assertEqual(links[f'@markup.heading.{level}'], 'LucretiaHeading')

    def test_all_links_resolve_without_cycles(self):
        for kind in KINDS:
            defs, links = highlights(vim_theme(self.pal, kind))
            self.assertFalse(defs.keys() & links.keys())
            for name in links:
                seen = set()
                current = name
                while current in links:
                    self.assertNotIn(current, seen, f'Link cycle: {name}')
                    seen.add(current)
                    current = links[current]
                self.assertIn(current, defs, f'Missing link target: {name} -> {current}')

    def test_underlines_and_selection_preserve_syntax_foregrounds(self):
        for kind in KINDS:
            defs, _ = highlights(vim_theme(self.pal, kind))
            for name in ('Visual', 'DiffAdd', 'DiffChange', 'DiffText', 'CursorLine'):
                self.assertEqual(defs[name]['guifg'], 'NONE')
            for name in ('SpellBad', 'SpellCap', 'SpellRare', 'SpellLocal',
                         'DiagnosticUnderlineError', 'DiagnosticUnderlineWarn',
                         'DiagnosticUnderlineInfo', 'DiagnosticUnderlineHint'):
                self.assertEqual(defs[name]['guifg'], 'NONE')
                self.assertEqual(defs[name]['guibg'], 'NONE')
                self.assertEqual(defs[name]['gui'], 'undercurl')
                self.assertNotEqual(defs[name]['guisp'], 'NONE')

    def test_ansi_matches_other_apps(self):
        for kind in KINDS:
            text = vim_theme(self.pal, kind)
            colors = ansi(self.pal, kind)
            for index, name in enumerate(ANSI_NAMES):
                self.assertIn(f"let g:terminal_color_{index} = '{colors[name]}'", text)
            vim_list = text.split('let g:terminal_ansi_colors = [')[1]
            self.assertEqual(re.findall(r'#[0-9A-F]{6}', vim_list),
                             [colors[name] for name in ANSI_NAMES])

    def test_package_contains_exact_loose_files_and_notice(self):
        path = 'dist/vim/lucretia-vim.zip'
        loose = {name.removeprefix('dist/vim/'): data for name, data in self.outputs.items()
                 if name.startswith('dist/vim/') and name != path}
        self.assertEqual(set(loose), {'README.md', build.NOTICE,
            *[f'colors/lucretia-{kind}.vim' for kind in KINDS]})
        with ZipFile(BytesIO(self.outputs[path])) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()), {f'lucretia-vim/{n}' for n in loose})
            for name, data in loose.items():
                self.assertEqual(archive.read(f'lucretia-vim/{name}'), data)
        self.assertEqual(self.outputs[path], build.render()[path])

    def test_invalid_appearance_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unknown appearance'):
            vim_theme(self.pal, 'invalid')


class EditorTests(unittest.TestCase):
    """Each editor runs independently; missing binaries are reported as skips."""
    @classmethod
    def setUpClass(cls):
        cls.pal = build_palette()

    def run_editor(self, editor, body):
        binary = shutil.which(editor)
        if binary is None:
            self.skipTest(f'{editor} is not installed')
        with tempfile.TemporaryDirectory(prefix='lucretia editor ') as directory:
            root = Path(directory)
            (root / 'colors').mkdir()
            for kind in KINDS:
                (root / f'colors/lucretia-{kind}.vim').write_text(vim_theme(self.pal, kind))
            report = root / 'errors.txt'
            script = '\n'.join([
                'set nomore', 'set termguicolors',
                "execute 'set runtimepath^=' . fnameescape(" + vim_string(root) + ')',
                "let v:errmsg = ''", 'try', body,
                "call assert_equal('', v:errmsg, 'No editor errors')", 'catch',
                "call add(v:errors, v:exception . ' at ' . v:throwpoint)", 'endtry',
                f'call writefile(v:errors, {vim_string(report)})',
                'if !empty(v:errors)', '  cquit', 'endif', 'qa!', ''])
            runner = root / 'check.vim'
            runner.write_text(script)
            args = ([binary, '--headless', '-u', 'NONE'] if editor == 'nvim'
                    else [binary, '-Nu', 'NONE', '-es'])
            result = subprocess.run(args + ['-n', '-i', 'NONE', '-S', str(runner)],
                                    capture_output=True, text=True, timeout=20, cwd=root)
            details = report.read_text() if report.exists() else 'No assertion report written.'
            self.assertEqual(result.returncode, 0, details + result.stdout + result.stderr)
            self.assertEqual(details, '')
            self.assertNotIn('Error', result.stderr)

    def switching_checks(self):
        lines = ['syntax enable', 'set nonumber nocursorline',
                 "let s:options = [&number, &cursorline, &termguicolors, &background]",
                 'highlight LucretiaUnrelated guifg=#123456 gui=bold']
        # Every ordered pair, including reloading the same appearance.
        for before, after in itertools.product(KINDS, repeat=2):
            lines += [f'colorscheme lucretia-{before}', f'colorscheme lucretia-{after}']
            ui, syn, _ = theme_context(self.pal, after)
            defs, links = highlights(vim_theme(self.pal, after))
            lines += [f"call assert_equal('lucretia-{after}', g:colors_name)",
                      f"call assert_equal('{('dark' if after == 'dark' else 'light')}', &background)"]
            # Check every explicit group, not just a few representative ones.
            in_nvim = False
            for line in vim_theme(self.pal, after).splitlines():
                if line == "if has('nvim')":
                    lines.append(line)
                    in_nvim = True
                parts = line.split()
                if parts[:1] != ['highlight'] or parts[1] == 'clear':
                    continue
                group = parts[1]
                for field, attr in [('guifg', 'fg#'), ('guibg', 'bg#'), ('guisp', 'sp#')]:
                    value = defs[group][field]
                    expected = '' if value == 'NONE' else value.lower()
                    lines.append(f"call assert_equal('{expected}', "
                                 f"synIDattr(hlID('{group}'), '{attr}', 'gui'), '{after}: {group} {attr}')")
            if in_nvim:
                lines.append('endif')
            colors = ansi(self.pal, after)
            lines += ["if has('nvim')"]
            for index, name in enumerate(ANSI_NAMES):
                lines.append(f"call assert_equal('{colors[name]}', g:terminal_color_{index})")
            lines += ['else', 'call assert_equal(' +
                      '[' + ', '.join(vim_string(colors[n]) for n in ANSI_NAMES) +
                      '], g:terminal_ansi_colors)', 'endif']
            for style in ('reverse', 'bold'):
                lines.append(f"call assert_equal('', synIDattr(hlID('StatusLine'), '{style}', 'gui'))")
            lines.append("call assert_equal('1', synIDattr(hlID('Comment'), 'italic', 'gui'))")
        lines += ["call assert_equal(s:options[:2], [&number, &cursorline, &termguicolors])",
                  "call assert_equal('', synIDattr(hlID('LucretiaUnrelated'), 'fg#', 'gui'))",
                  # Loading the file overrides a previously chosen background.
                  'set background=dark', 'colorscheme lucretia-paper',
                  "call assert_equal('lucretia-paper', g:colors_name)",
                  "call assert_equal('light', &background)",
                  # A standard colorscheme can still replace Lucretia.
                  'colorscheme default', 'colorscheme lucretia-paper']
        return '\n'.join(lines)

    def syntax_checks(self):
        lines = []
        # Load syntax both before and after the scheme; check actual buffer tokens.
        for first in (True, False):
            for kind in KINDS:
                ui, syn, _ = theme_context(self.pal, kind)
                lines += ['enew!', 'syntax off']
                if first:
                    lines += ['syntax enable']
                lines += [f'colorscheme lucretia-{kind}']
                if not first:
                    lines += ['syntax enable']
                lines += ["call setline(1, ['# comment', 'def residual(A, x, b):',",
                          "      \\ '    label = \"ready\"', '    scale = 1.5', '    return b'])",
                          'setlocal syntax=python']
                for row, col, role in [(1, 1, 'comment'), (2, 1, 'keyword'),
                                       (2, 5, 'definition'), (3, 13, 'string'), (4, 13, 'number')]:
                    lines.append(f"call assert_equal('{syn[role].lower()}', "
                                 f"synIDattr(synIDtrans(synID({row}, {col}, 1)), 'fg#', 'gui'), "
                                 f"'{kind}: Python {role}')")
        return '\n'.join(lines)

    def test_vim_loading_and_switching(self):
        self.run_editor('vim', self.switching_checks())

    def test_nvim_loading_and_switching(self):
        self.run_editor('nvim', self.switching_checks())

    def test_vim_real_syntax_tokens(self):
        self.run_editor('vim', self.syntax_checks())

    def test_nvim_real_syntax_tokens(self):
        self.run_editor('nvim', self.syntax_checks())


if __name__ == '__main__':
    unittest.main(verbosity=2)
