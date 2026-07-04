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
PBASE = {s: v['hex'] for s, v in pal['paper']['base'].items()}
PBG, PBG2 = pal['paper']['bg'], pal['paper']['bg2']

# VS Code 互換エディタは拡張 ID だけでなく version もローカルキャッシュや
# .obsolete 判定に使う。開発中に同じ version の VSIX / symlink / 手動削除を
# 行き来すると、Cursor 側で「現在の拡張」が古い削除済みエントリと衝突し、
# 拡張一覧から消えることがある。更新作業では version を進め、両エディタへ
# 同じ VSIX を入れることで、キャッシュを自然に新しい拡張として扱わせる。
# ここを package.json 側の単一ソースにして、生成物の手修正を避ける。
VSCODE_EXTENSION_VERSION = '0.2.2'

# ============================================================
# VS Code テーマ (plan.md §6.3: sparse highlighting)
# ============================================================

def token_colors(syn, tx2):
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
        # --- markup (Markdown / LaTeX 等)。装飾は色でなく書体で表現する ---
        dict(name='Markup heading / LaTeX section',
             scope=['markup.heading', 'entity.name.section'],
             settings=dict(fontStyle='bold')),
        dict(name='Markup bold (\\textbf 等)',
             scope=['markup.bold', 'strong'],
             settings=dict(fontStyle='bold')),
        dict(name='Markup italic (\\textit, \\emph 等)',
             scope=['markup.italic', 'emphasis'],
             settings=dict(fontStyle='italic')),
        dict(name='Markup bold+italic (入れ子)',
             scope=['markup.bold markup.italic',
                    'markup.italic markup.bold'],
             settings=dict(fontStyle='bold italic')),
        dict(name='Markup underline (\\underline 等)',
             scope=['markup.underline'],
             settings=dict(fontStyle='underline')),
        dict(name='Markup strikethrough',
             scope=['markup.strikethrough'],
             settings=dict(fontStyle='strikethrough')),
        dict(name='Markup quote',
             scope=['markup.quote'],
             settings=dict(foreground=tx2, fontStyle='italic')),
        dict(name='Reference / citation key (\\ref, \\cite 等, Tier 3)',
             scope=['constant.other.reference'],
             settings=dict(foreground=syn['definition'])),
    ]


def semantic_tokens(syn, tx):
    """semanticTokenColors: Tier 設計 (plan.md §6.3) を LSP semantic token にも適用。
    variable 系を tx に明示固定し (Tier 1)、着色は定義箇所と既存 hue に限定する。
    これがないと言語サーバー既定のマッピングで TextMate ルール外の色が混入しうる"""
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
    """ターミナル ANSI 16 色 (plan.md §6.3: 色名は ANSI と自然に整合)"""
    if theme in ('light', 'paper'):
        n, b = '600', '400'   # normal / bright
        # paper は無彩色スロットのみ暖色 pbase に置換 (有彩 6 色は共通)
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


def vscode_theme(kind):
    light = kind in ('light', 'paper')
    if kind == 'light':
        ui, syn, (bg, bg2) = R['light'] | R['light_high'], R['syntax_light'], (BG, BG2)
    elif kind == 'paper':
        # lucretia paper (plan.md §6.5): white は使わない (ハレーション回避)
        ui, syn, (bg, bg2) = R['paper'], R['syntax_paper'], (PBG, PBG2)
    else:
        ui, syn = R['dark'], R['syntax_dark']
        bg, bg2 = ui['bg'], ui['bg-2']
    tx, tx2, tx3 = ui['tx'], ui['tx-2'], ui['tx-3']
    sel = AC['blue']['150'] if light else AC['blue']['850']
    inp = PBASE['50'] if kind == 'paper' else WHITE if light else BASE['900']
    err = AC['red']['600' if light else '300']
    warn = AC['orange']['600' if light else '300']
    info = AC['blue']['600' if light else '300']
    a = ansi(kind)

    def ac(name, ls, ds):
        """アクセント色をテーマ別シェードで引く (light系 / dark)"""
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

        # --- bracket pair colorization ---
        # 括弧のみ 6 色フルサイクル (細いグリフで面積が小さく hue 数制限の例外)。
        # 同一シェード帯だと細グリフでは hue 差だけで識別できないため、
        # 全ペア間 OKLab 距離の最小値を最大化するようシェード (=明度) も振って選定。
        # CVD (D/P 型) シミュレーション距離とAPCA |Lc|>=45 (light) / 50 (dark) を制約に
        # 全探索した結果 (通常視 0.104→0.176, D 型隣接 0.049→0.173)。
        # 循環順も隣接間距離が最大になる並び: blue→orange→purple→yellow→magenta→cyan
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

        # --- 検索・選択・単語ハイライト ---
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

        # --- git diff / 変更表示 ---
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

        # --- タブ・エディタグループ ---
        'tab.activeBorderTop': ui['focus-ring'],
        'tab.hoverBackground': bg,
        'tab.border': ui['ui'],
        'editorGroupHeader.tabsBackground': bg2,

        # --- サイドバー / リスト ---
        'list.inactiveSelectionBackground': ui['ui'],
        'list.focusBackground': sel,
        'list.focusForeground': tx,
        'sideBarSectionHeader.background': bg2,
        'sideBarSectionHeader.foreground': tx2,
        'tree.indentGuidesStroke': ui['ui-2'],

        # --- Command Palette / Quick Pick ---
        'quickInput.background': bg2,
        'quickInput.foreground': tx,
        'quickInputList.focusBackground': sel,
        'quickInputList.focusForeground': tx,
        'pickerGroup.foreground': ui['link'],
        'pickerGroup.border': ui['ui'],

        # --- エディタ内ウィジェット / スクロールバー ---
        'editorWidget.background': bg2,
        'editorWidget.border': ui['ui-3'],
        'editorSuggestWidget.selectedBackground': sel,
        'editorHoverWidget.background': bg2,
        'editorHoverWidget.border': ui['ui-3'],
        'scrollbarSlider.background': tx3 + '33',
        'scrollbarSlider.hoverBackground': tx3 + '55',
        'scrollbarSlider.activeBackground': tx3 + '77',

        # --- 診断 (波線は foreground のみ。border は二重マークになるため設けない) ---
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
    # VSIX は dist/vscode を作業ディレクトリにして作るため、将来ここに確認用
    # ファイルや一時成果物が増えても配布物へ混ざらないよう明示的に絞る。
    # .vscodeignore ではなく package.json の files に置くのは、配布対象を
    # 生成元の単一ソースから読める状態にしておくため。
    files=['themes/*.json'],
    contributes=dict(themes=[
        dict(label='Lucretia Light', uiTheme='vs',
             path='./themes/lucretia-light-color-theme.json'),
        dict(label='Lucretia Dark', uiTheme='vs-dark',
             path='./themes/lucretia-dark-color-theme.json'),
        dict(label='Lucretia Paper', uiTheme='vs',
             path='./themes/lucretia-paper-color-theme.json'),
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


def obsidian_paper_css():
    """lucretia paper (plan.md §6.5): 長文読書用。lucretia.css と同時に有効化しない"""
    md, pa = R['markdown_paper'], R['paper']
    ln = [
        '/* lucretia paper — Obsidian CSS snippet. scripts/build_dist.py が生成 (手編集しない)',
        '   長文読書用の温かみプロファイル。lucretia.css とはどちらか一方だけ有効化する */',
        '.theme-light {',
        f'  --background-primary: {PBG};',
        f'  --background-secondary: {PBG2};',
        f'  --text-normal: {pa["tx"]};',
        f'  --text-muted: {pa["tx-2"]};',
        f'  --text-faint: {pa["tx-3"]};',
        f'  --link-color: {md["link"]};',
        f'  --link-external-color: {md["link"]};',
        f'  --code-background: {md["code-inline-bg"]};',
        f'  --blockquote-border-color: {md["quote-border"]};',
        f'  --hr-color: {md["hr"]};',
        f'  --text-highlight-bg: {HL["yellow"]};  /* 既定マーカー = hl-yellow */',
        '}',
        '/* 見出しは本文より一段沈めた無彩色で階層を出す (markdown_paper.heading) */',
        '.theme-light .markdown-preview-view :is(h1,h2,h3,h4,h5,h6),',
        '.theme-light .cm-header {',
        f'  color: {md["heading"]};',
        '}',
        '/* ハイライター 8 色 (黒文字専用の規約, plan.md §9-13) */',
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
    for kind in ('light', 'dark', 'paper'):
        p = os.path.join(vs, 'themes', f'lucretia-{kind}-color-theme.json')
        with open(p, 'w') as f:
            json.dump(vscode_theme(kind), f, ensure_ascii=False, indent=2)
    ob = os.path.join(DIST, 'obsidian')
    os.makedirs(ob, exist_ok=True)
    with open(os.path.join(ob, 'lucretia.css'), 'w') as f:
        f.write(obsidian_css())
    with open(os.path.join(ob, 'lucretia-paper.css'), 'w') as f:
        f.write(obsidian_paper_css())
    print('generated: dist/vscode/{package.json,themes/*.json}, '
          'dist/obsidian/{lucretia,lucretia-paper}.css')
