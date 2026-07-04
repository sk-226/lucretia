"""配布物の生成 (plan.md Phase 4 試作 / Phase 5, §6.3)

palette.json (単一ソース) から生成:
- dist/vscode/                    : VS Code テーマ拡張 (light / dark + ターミナル ANSI 16)
- dist/obsidian/lucretia.css      : Obsidian CSS スニペット (リンク・ハイライター等)

実行: python3 scripts/build_dist.py  (先に scripts/build.py で palette.json を更新すること)
"""
import json
import os

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


# ============================================================
# VS Code テーマ (plan.md §6.3: sparse highlighting)
# ============================================================

def token_colors(syn):
    """Tier 設計 (plan.md §6.3)。変数はルールなし = エディタ前景色のまま (Tier 1)"""
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
    ]


def ansi(theme):
    """ターミナル ANSI 16 色 (plan.md §6.3: 色名は ANSI と自然に整合)"""
    if theme == 'light':
        n, b = '600', '400'   # normal / bright
        return dict(black=BLACK, white=BASE['150'],
                    brightBlack=BASE['600'], brightWhite=WHITE,
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


def vscode_theme(kind):
    light = kind == 'light'
    ui = R['light'] | R['light_high'] if light else R['dark']
    syn = R['syntax_light'] if light else R['syntax_dark']
    bg, bg2 = (BG, BG2) if light else (ui['bg'], ui['bg-2'])
    tx, tx2, tx3 = ui['tx'], ui['tx-2'], ui['tx-3']
    sel = AC['blue']['150'] if light else AC['blue']['850']
    a = ansi(kind)
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
        'input.background': WHITE if light else BASE['900'],
        'input.foreground': tx,
        'input.border': ui['ui-3'],
        'editorWarning.foreground': AC['orange']['600' if light else '300'],
        'editorError.foreground': AC['red']['600' if light else '300'],
        'editorInfo.foreground': AC['blue']['600' if light else '300'],
    }
    for k, v in a.items():
        colors[f'terminal.ansi{k[0].upper()}{k[1:]}'] = v
    return dict(name=f'Lucretia {"Light" if light else "Dark"}',
                type='light' if light else 'dark',
                colors=colors, tokenColors=token_colors(syn))


VSCODE_PKG = dict(
    name='lucretia-theme', displayName='Lucretia',
    description='Flexoki-inspired quiet color theme (sparse highlighting)',
    version='0.1.0', publisher='sugu', engines={'vscode': '^1.75.0'},
    categories=['Themes'],
    contributes=dict(themes=[
        dict(label='Lucretia Light', uiTheme='vs',
             path='./themes/lucretia-light-color-theme.json'),
        dict(label='Lucretia Dark', uiTheme='vs-dark',
             path='./themes/lucretia-dark-color-theme.json'),
    ]))


# ============================================================
# Obsidian CSS スニペット (plan.md §6.2)
# ============================================================

def obsidian_css():
    md, hi = R['markdown'], R['light_high']
    ln = [
        '/* lucretia — Obsidian CSS snippet. scripts/build_dist.py が生成 (手編集しない)',
        '   .obsidian/snippets/ に置いて設定 > Appearance > CSS snippets で有効化 */',
        '.theme-light {',
        f'  --background-primary: {BG};',
        f'  --background-secondary: {BG2};',
        f'  --text-normal: {hi["tx"]};',
        f'  --text-muted: {hi["tx-2"]};',
        f'  --text-faint: {hi["tx-3"]};',
        f'  --link-color: {md["link"]};',
        f'  --link-external-color: {md["link"]};',
        f'  --code-background: {md["code-inline-bg"]};',
        f'  --blockquote-border-color: {md["quote-border"]};',
        f'  --hr-color: {md["hr"]};',
        f'  --text-highlight-bg: {HL["yellow"]};  /* 既定マーカー = hl-yellow */',
        '}',
        '/* ハイライター 8 色 (黒文字専用の規約, plan.md §9-13)。',
        '   <mark class="hl-blue"> などで使う */',
    ]
    for n, v in HL.items():
        ln.append(f'.theme-light mark.hl-{n}, .theme-light .hl-{n} {{ background: {v}; }}')
    return '\n'.join(ln) + '\n'


# ============================================================
if __name__ == '__main__':
    vs = os.path.join(DIST, 'vscode')
    os.makedirs(os.path.join(vs, 'themes'), exist_ok=True)
    with open(os.path.join(vs, 'package.json'), 'w') as f:
        json.dump(VSCODE_PKG, f, indent=2)
    for kind in ('light', 'dark'):
        p = os.path.join(vs, 'themes', f'lucretia-{kind}-color-theme.json')
        with open(p, 'w') as f:
            json.dump(vscode_theme(kind), f, ensure_ascii=False, indent=2)
    ob = os.path.join(DIST, 'obsidian')
    os.makedirs(ob, exist_ok=True)
    with open(os.path.join(ob, 'lucretia.css'), 'w') as f:
        f.write(obsidian_css())
    print('generated: dist/vscode/{package.json,themes/*.json}, dist/obsidian/lucretia.css')
