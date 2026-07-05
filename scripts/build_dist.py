"""Generate distribution artifacts from palette.json.

Generated outputs:
- dist/vscode/                    : VS Code theme extension
- dist/obsidian/lucretia-paper.css: Obsidian Minimal overlay for long-form reading
- dist/*/THIRD_PARTY_NOTICES.md   : attribution copied beside distributable files

Run scripts/build.py first so palette.json remains the source of truth.
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from color import hex_to_rgb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, 'dist')

pal = json.load(open(os.path.join(ROOT, 'palette.json')))
R = {g: {k: v['hex'] for k, v in d.items() if k != 'scrim'}
     for g, d in pal['roles'].items()}
BASE = {s: v['hex'] for s, v in pal['base'].items()}
AC = {n: {s: v['hex'] for s, v in scale.items()} for n, scale in pal['accents'].items()}
HL = {n: v['hex'] for n, v in pal['highlight'].items()}
WHITE, BLACK = pal['special']['white'], pal['special']['black']
BG, BG2 = pal['bg']['bg'], pal['bg']['bg2']
PBASE = {s: v['hex'] for s, v in pal['paper']['base'].items()}
PBG, PBG2 = pal['paper']['bg'], pal['paper']['bg2']

THIRD_PARTY_NOTICE_FILE = 'THIRD_PARTY_NOTICES.md'

# Bump whenever the VSIX contents change; editors cache extensions by ID/version.
VSCODE_EXTENSION_VERSION = '0.2.3'

# ============================================================
# VS Code theme (plan.md §6.3 sparse highlighting)
# ============================================================

def token_colors(syn, tx2):
    """Apply the syntax tiers while leaving variables on the editor foreground."""
    return [
        dict(name='Comment (Tier 4)', scope=['comment', 'punctuation.definition.comment'],
             settings=dict(foreground=syn['comment'], fontStyle='italic')),
        dict(name='Operator / punctuation (Tier 4)',
             scope=['keyword.operator', 'punctuation'],
             settings=dict(foreground=syn['operator'])),
        dict(name='Keyword (Tier 2)',
             scope=['keyword', 'keyword.control', 'storage.type', 'storage.modifier'],
             settings=dict(foreground=syn['keyword'])),
        dict(name='Function / type definition (Tier 2)',
             scope=['entity.name.function', 'entity.name.type', 'entity.name.class',
                    'support.function', 'entity.other.inherited-class'],
             settings=dict(foreground=syn['definition'])),
        dict(name='String (Tier 3)', scope=['string', 'string.quoted'],
             settings=dict(foreground=syn['string'])),
        dict(name='Number / constant (Tier 3)',
             scope=['constant.numeric', 'constant.language', 'constant.character'],
             settings=dict(foreground=syn['number'])),
        # Markup uses typography instead of hue so prose documents stay calmer.
        dict(name='Markup heading / LaTeX section',
             scope=['markup.heading', 'entity.name.section'],
             settings=dict(fontStyle='bold')),
        dict(name='Markup bold (\\textbf, strong)',
             scope=['markup.bold', 'strong'],
             settings=dict(fontStyle='bold')),
        dict(name='Markup italic (\\textit, \\emph, emphasis)',
             scope=['markup.italic', 'emphasis'],
             settings=dict(fontStyle='italic')),
        dict(name='Markup bold+italic (nested)',
             scope=['markup.bold markup.italic',
                    'markup.italic markup.bold'],
             settings=dict(fontStyle='bold italic')),
        dict(name='Markup underline (\\underline)',
             scope=['markup.underline'],
             settings=dict(fontStyle='underline')),
        dict(name='Markup strikethrough',
             scope=['markup.strikethrough'],
             settings=dict(fontStyle='strikethrough')),
        dict(name='Markup quote',
             scope=['markup.quote'],
             settings=dict(foreground=tx2, fontStyle='italic')),
        dict(name='Reference / citation key (\\ref, \\cite, Tier 3)',
             scope=['constant.other.reference'],
             settings=dict(foreground=syn['definition'])),
    ]


def semantic_tokens(syn, tx):
    """Mirror the syntax tiers for LSP semantic tokens.

    Variables are pinned to tx so language-server defaults cannot introduce
    extra hues outside the sparse-highlighting model.
    """
    d = syn['definition']
    return {
        'variable': tx, 'parameter': tx, 'property': tx,          # Tier 1
        'function.declaration': d, 'method.declaration': d,       # Tier 2
        'class.declaration': d, 'interface.declaration': d,
        'struct.declaration': d, 'enum.declaration': d,
        'type.declaration': d,
        'keyword': syn['keyword'],                                # Tier 2
        'string': syn['string'], 'number': syn['number'],         # Tier 3
        'operator': syn['operator'],                              # Tier 4
        'comment': dict(foreground=syn['comment'], fontStyle='italic'),
    }


def ansi(theme):
    """Map ANSI names to palette hues while keeping normal/bright bands distinct."""
    if theme in ('light', 'paper'):
        n, b = '600', '400'   # normal / bright
        # Paper only swaps neutral slots to pbase; chromatic ANSI hues stay shared.
        blk, wht, bblk = ((PBASE['950'], PBASE['150'], PBASE['600'])
                          if theme == 'paper' else (BLACK, BASE['150'], BASE['600']))
        return dict(black=blk, white=wht,
                    brightBlack=bblk, brightWhite=WHITE,
                    **{c: AC[c][n] for c in ('red', 'green', 'yellow', 'blue',
                                             'magenta', 'cyan')},
                    **{f'bright{c.capitalize()}': AC[c][b]
                       for c in ('red', 'green', 'yellow', 'blue', 'magenta', 'cyan')})
    n, b = '300', '200'
    return dict(black=BASE['850'], white=BASE['200'],
                brightBlack=BASE['500'], brightWhite=WHITE,
                **{c: AC[c][n] for c in ('red', 'green', 'yellow', 'blue',
                                         'magenta', 'cyan')},
                **{f'bright{c.capitalize()}': AC[c][b]
                   for c in ('red', 'green', 'yellow', 'blue', 'magenta', 'cyan')})


def selection_color(light):
    return AC['blue']['150'] if light else AC['blue']['850']


def vscode_theme(kind):
    light = kind in ('light', 'paper')
    if kind == 'light':
        ui, syn, (bg, bg2) = R['light'] | R['light_high'], R['syntax_light'], (BG, BG2)
    elif kind == 'paper':
        # Paper avoids white UI surfaces because they glare against the warm page.
        ui, syn, (bg, bg2) = R['paper'], R['syntax_paper'], (PBG, PBG2)
    else:
        ui, syn = R['dark'], R['syntax_dark']
        bg, bg2 = ui['bg'], ui['bg-2']
    tx, tx2, tx3 = ui['tx'], ui['tx-2'], ui['tx-3']
    sel = selection_color(light)
    inp = PBASE['50'] if kind == 'paper' else WHITE if light else BASE['900']
    err = AC['red']['600' if light else '300']
    warn = AC['orange']['600' if light else '300']
    info = AC['blue']['600' if light else '300']
    a = ansi(kind)

    def ac(name, ls, ds):
        """Choose the light/paper or dark shade for one accent role."""
        return AC[name][ls if light else ds]
    colors = {
        'editor.background': bg,
        'editor.foreground': tx,
        'editor.lineHighlightBackground': bg2,
        'editor.selectionBackground': sel,
        'editorCursor.foreground': tx,
        'editorLineNumber.foreground': tx3,
        'editorLineNumber.activeForeground': tx2,
        'editorIndentGuide.background1': ui['ui'],
        'editorWhitespace.foreground': ui['ui-2'],
        'sideBar.background': bg2,
        'sideBar.foreground': tx2,
        'activityBar.background': bg2,
        'activityBar.foreground': tx,
        'statusBar.background': bg2,
        'statusBar.foreground': tx2,
        'titleBar.activeBackground': bg2,
        'titleBar.activeForeground': tx2,
        'tab.activeBackground': bg,
        'tab.activeForeground': tx,
        'tab.inactiveBackground': bg2,
        'tab.inactiveForeground': tx2,
        'panel.background': bg,
        'panelTitle.activeForeground': tx,
        'terminal.background': bg,
        'terminal.foreground': tx,
        'focusBorder': ui['focus-ring'],
        'textLink.foreground': ui['link'],
        'textLink.activeForeground': ui['link-hover'],
        'list.activeSelectionBackground': sel,
        'list.activeSelectionForeground': tx,
        'list.hoverBackground': bg2,
        'badge.background': AC['blue']['600'],
        'badge.foreground': WHITE,
        'button.background': AC['blue']['600'],
        'button.foreground': WHITE,
        'input.background': inp,
        'input.foreground': tx,
        'input.border': ui['ui-3'],
        'input.placeholderForeground': tx3,
        'dropdown.background': inp,
        'dropdown.foreground': tx,
        'dropdown.border': ui['ui-3'],
        'editorWarning.foreground': warn,
        'editorError.foreground': err,
        'editorInfo.foreground': info,

        # Bracket pairs are the one place that uses a full six-hue cycle: the
        # glyphs are too thin for hue alone, so shades were searched as well.
        # The order maximizes adjacent distance under normal and D/P simulation
        # while keeping APCA above the bracket-specific thresholds.
        'editorBracketHighlight.foreground1': ac('blue', '700', '300'),
        'editorBracketHighlight.foreground2': ac('orange', '400', '200'),
        'editorBracketHighlight.foreground3': ac('purple', '400', '200'),
        'editorBracketHighlight.foreground4': ac('yellow', '700', '400'),
        'editorBracketHighlight.foreground5': ac('magenta', '700', '300'),
        'editorBracketHighlight.foreground6': ac('cyan', '500', '200'),
        'editorBracketHighlight.unexpectedBracket.foreground':
            ac('red', '600', '300'),
        'editorBracketMatch.background': ui['ui'],
        'editorBracketMatch.border': tx3,

        'editor.findMatchBackground':
            HL['yellow'] if light else AC['yellow']['850'],
        'editor.findMatchBorder': ac('yellow', '600', '400'),
        'editor.findMatchHighlightBackground':
            (HL['yellow'] + '66') if light else AC['yellow']['400'] + '33',
        'editor.wordHighlightBackground': ac('blue', '100', '850') + '80',
        'editor.wordHighlightStrongBackground':
            ac('magenta', '100', '850') + '80',
        'editor.selectionHighlightBackground': ac('blue', '100', '850') + '66',
        'editor.inactiveSelectionBackground': sel + '80',
        'terminal.selectionBackground': sel,

        'editorGutter.addedBackground': ac('green', '500', '400'),
        'editorGutter.modifiedBackground': ac('blue', '500', '400'),
        'editorGutter.deletedBackground': ac('red', '500', '400'),
        'diffEditor.insertedTextBackground': ac('green', '500', '400') + '26',
        'diffEditor.removedTextBackground': ac('red', '500', '400') + '26',
        'diffEditor.insertedLineBackground': ac('green', '500', '400') + '14',
        'diffEditor.removedLineBackground': ac('red', '500', '400') + '14',
        'gitDecoration.addedResourceForeground': ac('green', '600', '400'),
        'gitDecoration.untrackedResourceForeground': ac('green', '600', '400'),
        'gitDecoration.modifiedResourceForeground': ac('blue', '600', '300'),
        'gitDecoration.deletedResourceForeground': ac('red', '600', '300'),
        'gitDecoration.conflictingResourceForeground':
            ac('orange', '600', '300'),
        'gitDecoration.ignoredResourceForeground': tx3,

        'tab.activeBorderTop': ui['focus-ring'],
        'tab.hoverBackground': bg,
        'tab.border': ui['ui'],
        'editorGroupHeader.tabsBackground': bg2,

        'list.inactiveSelectionBackground': ui['ui'],
        'list.focusBackground': sel,
        'list.focusForeground': tx,
        'sideBarSectionHeader.background': bg2,
        'sideBarSectionHeader.foreground': tx2,
        'tree.indentGuidesStroke': ui['ui-2'],

        'quickInput.background': bg2,
        'quickInput.foreground': tx,
        'quickInputList.focusBackground': sel,
        'quickInputList.focusForeground': tx,
        'pickerGroup.foreground': ui['link'],
        'pickerGroup.border': ui['ui'],

        'editorWidget.background': bg2,
        'editorWidget.border': ui['ui-3'],
        'editorSuggestWidget.selectedBackground': sel,
        'editorHoverWidget.background': bg2,
        'editorHoverWidget.border': ui['ui-3'],
        'scrollbarSlider.background': tx3 + '33',
        'scrollbarSlider.hoverBackground': tx3 + '55',
        'scrollbarSlider.activeBackground': tx3 + '77',

        # Diagnostics use foreground only; borders add a duplicate visual signal.
        'editorOverviewRuler.errorForeground': err,
        'editorOverviewRuler.warningForeground': warn,
        'editorOverviewRuler.infoForeground': info,
        'editorOverviewRuler.findMatchForeground': AC['yellow']['500'] + '88',
        'editorOverviewRuler.bracketMatchForeground': ui['ui-3'],
    }
    for k, v in a.items():
        colors[f'terminal.ansi{k[0].upper()}{k[1:]}'] = v
    return dict(name=f'Lucretia {kind.capitalize()}',
                type='light' if light else 'dark',
                semanticHighlighting=True,
                semanticTokenColors=semantic_tokens(syn, tx),
                colors=colors, tokenColors=token_colors(syn, tx2))


VSCODE_PKG = dict(
    name='lucretia-theme', displayName='Lucretia',
    description='Flexoki-inspired quiet color theme (sparse highlighting)',
    version=VSCODE_EXTENSION_VERSION, publisher='sugu', engines={'vscode': '^1.75.0'},
    categories=['Themes'],
    # The VSIX is built from dist/vscode, so package files are whitelisted here
    # to keep future scratch files out of releases without a separate .vscodeignore.
    files=['themes/*.json', THIRD_PARTY_NOTICE_FILE],
    contributes=dict(themes=[
        dict(label='Lucretia Light', uiTheme='vs',
             path='./themes/lucretia-light-color-theme.json'),
        dict(label='Lucretia Dark', uiTheme='vs-dark',
             path='./themes/lucretia-dark-color-theme.json'),
        dict(label='Lucretia Paper', uiTheme='vs',
             path='./themes/lucretia-paper-color-theme.json'),
    ]))


# ============================================================
# Obsidian CSS snippets (plan.md §6.2)
# ============================================================

def css_rgb(hex_color):
    return ', '.join(str(v) for v in hex_to_rgb(hex_color))


def css_rgba(hex_color, alpha):
    return f'rgba({css_rgb(hex_color)}, {alpha})'


def obsidian_paper_css():
    md, pa, syn = R['markdown_paper'], R['paper'], R['syntax_paper']
    heading_color_vars = [
        f'  --{name}-color: {md["heading"]};'
        for name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'inline-title')
    ]
    color_vars = [
        line
        for css_name, accent_name in (
            ('red', 'red'),
            ('orange', 'orange'),
            ('yellow', 'yellow'),
            ('green', 'green'),
            ('cyan', 'cyan'),
            ('blue', 'blue'),
            ('purple', 'purple'),
            ('pink', 'magenta'),
        )
        for line in (
            f'  --color-{css_name}: {AC[accent_name]["600"]};',
            f'  --color-{css_name}-rgb: {css_rgb(AC[accent_name]["600"])};',
        )
    ]
    ln = [
        '/* lucretia paper - generated; do not edit by hand. See THIRD_PARTY_NOTICES.md. */',
        '',
        '/* Match Minimal preset specificity without !important. */',
        'body.theme-light.theme-light {',
        '  color-scheme: light;',
        f'  --bg1: {pa["bg"]};',
        f'  --bg2: {pa["bg-2"]};',
        f'  --bg3: {css_rgba(pa["tx"], "0.055")};',
        f'  --ui1: {pa["ui"]};',
        f'  --ui2: {pa["ui-2"]};',
        f'  --ui3: {pa["ui-3"]};',
        f'  --tx1: {pa["tx"]};',
        f'  --tx2: {pa["tx-2"]};',
        f'  --tx3: {pa["tx-3"]};',
        f'  --tx4: {PBASE["600"]};',
        f'  --ax1: {pa["link"]};',
        f'  --ax2: {pa["link-hover"]};',
        f'  --ax3: {pa["link"]};',
        f'  --hl1: {css_rgba(selection_color(True), "0.55")};',
        f'  --hl2: {HL["yellow"]};',
        f'  --sp1: {WHITE};',
        f'  --mono100: {pa["tx"]};',
        f'  --mono0: {PBG};',
        f'  --background-primary: var(--bg1);',
        f'  --background-primary-alt: var(--bg2);',
        f'  --background-secondary: var(--bg2);',
        f'  --background-secondary-alt: var(--bg1);',
        f'  --background-table-rows: var(--bg2);',
        f'  --background-modifier-hover: var(--bg3);',
        f'  --background-modifier-active-hover: var(--bg3);',
        f'  --background-modifier-border: var(--ui1);',
        f'  --background-modifier-border-hover: var(--ui2);',
        f'  --background-modifier-border-focus: var(--ui3);',
        f'  --background-modifier-cover: {css_rgba(PBASE["900"], "0.18")};',
        f'  --background-modifier-form-field: {PBASE["50"]};',
        f'  --background-modifier-form-field-highlighted: {PBASE["50"]};',
        f'  --divider-color: var(--ui1);',
        f'  --frame-divider-color: var(--ui1);',
        f'  --ribbon-background: var(--bg2);',
        f'  --titlebar-background: var(--bg2);',
        f'  --titlebar-background-focused: var(--bg2);',
        f'  --titlebar-text-color-focused: var(--tx1);',
        f'  --mobile-sidebar-background: var(--bg1);',
        f'  --workspace-background-translucent: {css_rgba(PBG, "0.78")};',
        f'  --modal-background: var(--bg1);',
        f'  --modal-border-color: var(--ui2);',
        f'  --prompt-border-color: var(--ui3);',
        f'  --text-normal: var(--tx1);',
        f'  --text-muted: var(--tx2);',
        f'  --text-faint: var(--tx3);',
        f'  --text-formatting: var(--tx3);',
        f'  --text-accent: var(--ax1);',
        f'  --text-accent-hover: var(--ax2);',
        f'  --text-selection: var(--hl1);',
        f'  --text-highlight-bg: var(--hl2);',
        f'  --text-highlight-bg-active: {AC["yellow"]["100"]};',
        f'  --text-bold: var(--tx1);',
        f'  --text-italic: var(--tx1);',
        f'  --text-code: var(--tx4);',
        f'  --text-blockquote: var(--tx2);',
        f'  --link-color: var(--ax1);',
        f'  --link-color-hover: var(--ax2);',
        f'  --link-external-color: var(--ax1);',
        f'  --link-external-color-hover: var(--ax2);',
        f'  --interactive-accent: var(--ax3);',
        f'  --interactive-accent-hover: var(--ax2);',
        f'  --interactive-accent-rgb: {css_rgb(pa["link"])};',
        f'  --interactive-normal: {PBASE["50"]};',
        f'  --interactive-hover: var(--ui1);',
        f'  --checkbox-color: var(--ax3);',
        f'  --focus-ring-color: {pa["focus-ring"]};',
        f'  --nav-item-color: var(--tx2);',
        f'  --nav-item-color-hover: var(--tx1);',
        f'  --nav-item-color-active: var(--tx1);',
        f'  --nav-item-background-hover: var(--bg3);',
        f'  --nav-item-background-active: var(--bg3);',
        f'  --nav-indentation-guide-color: var(--ui1);',
        f'  --icon-color: var(--tx2);',
        f'  --icon-color-hover: var(--tx1);',
        f'  --icon-color-active: var(--tx1);',
        f'  --scrollbar-thumb-bg: var(--ui1);',
        f'  --scrollbar-active-thumb-bg: var(--ui3);',
        f'  --active-line-bg: {css_rgba(PBASE["900"], "0.035")};',
        f'  --quote-opening-modifier: {md["quote-border"]};',
        f'  --blockquote-color: {md["quote-text"]};',
        f'  --blockquote-border-color: {md["quote-border"]};',
        f'  --hr-color: {md["hr"]};',
        f'  --code-background: {md["code-inline-bg"]};',
        f'  --code-normal: {syn["variable"]};',
        f'  --code-comment: {syn["comment"]};',
        f'  --code-function: {syn["definition"]};',
        f'  --code-keyword: {syn["keyword"]};',
        f'  --code-important: {AC["red"]["600"]};',
        f'  --code-operator: {syn["operator"]};',
        f'  --code-property: {syn["definition"]};',
        f'  --code-punctuation: {syn["operator"]};',
        f'  --code-string: {syn["string"]};',
        f'  --code-tag: {syn["keyword"]};',
        f'  --code-value: {syn["number"]};',
        *heading_color_vars,
        f'  --tag-color: var(--tx2);',
        f'  --tag-background: {PBASE["100"]};',
        f'  --tag-background-hover: {PBASE["150"]};',
        f'  --tag-border-color: {PBASE["150"]};',
        f'  --table-border-color: var(--ui1);',
        f'  --table-header-background: var(--bg2);',
        f'  --table-row-background-hover: var(--bg3);',
        *color_vars,
        '}',
        'body.is-mobile.theme-light.theme-light {',
        f'  --mobile-sidebar-background: var(--bg1);',
        f'  --workspace-background-translucent: {css_rgba(PBG, "0.84")};',
        f'  --background-modifier-cover: {css_rgba(PBASE["900"], "0.22")};',
        '}',
        'body.theme-light .markdown-preview-view :is(h1,h2,h3,h4,h5,h6),',
        'body.theme-light .cm-header,',
        'body.theme-light .inline-title {',
        f'  color: {md["heading"]};',
        '}',
    ]
    for n, v in HL.items():
        ln.append(f'.theme-light mark.hl-{n}, .theme-light .hl-{n} {{ background: {v}; }}')
    return '\n'.join(ln) + '\n'


# ============================================================
if __name__ == '__main__':
    vs = os.path.join(DIST, 'vscode')
    ob = os.path.join(DIST, 'obsidian')
    os.makedirs(os.path.join(vs, 'themes'), exist_ok=True)
    os.makedirs(ob, exist_ok=True)
    with open(os.path.join(vs, 'package.json'), 'w') as f:
        json.dump(VSCODE_PKG, f, indent=2)
    notice_source = os.path.join(ROOT, THIRD_PARTY_NOTICE_FILE)
    for notice_dir in (vs, ob):
        shutil.copyfile(notice_source, os.path.join(notice_dir, THIRD_PARTY_NOTICE_FILE))
    for kind in ('light', 'dark', 'paper'):
        p = os.path.join(vs, 'themes', f'lucretia-{kind}-color-theme.json')
        with open(p, 'w') as f:
            json.dump(vscode_theme(kind), f, ensure_ascii=False, indent=2)
    with open(os.path.join(ob, 'lucretia-paper.css'), 'w') as f:
        f.write(obsidian_paper_css())
    print('generated: dist/vscode/{package.json,themes/*.json,THIRD_PARTY_NOTICES.md}, '
          'dist/obsidian/{lucretia-paper.css,THIRD_PARTY_NOTICES.md}')
