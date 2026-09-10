"""App-specific formats. All colors are passed in from the palette generator."""
from color import hex_to_rgb

KINDS = ('light', 'dark', 'paper')
ANSI_NAMES = ('black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white',
              'brightBlack', 'brightRed', 'brightGreen', 'brightYellow',
              'brightBlue', 'brightMagenta', 'brightCyan', 'brightWhite')

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


def ansi(pal, theme):
    """Map ANSI names to palette hues, with distinct normal and bright bands."""
    BASE = {str(s): v['hex'] for s, v in pal['base'].items()}
    PBASE = {str(s): v['hex'] for s, v in pal['paper']['base'].items()}
    AC = {n: {str(s): v['hex'] for s, v in scale.items()} for n, scale in pal['accents'].items()}
    WHITE, BLACK = pal['special']['white'], pal['special']['black']
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


def selection_color(pal, light):
    AC = {n: {str(s): v['hex'] for s, v in scale.items()} for n, scale in pal['accents'].items()}
    return AC['blue']['150'] if light else AC['blue']['850']


def vscode_theme(pal, kind):
    R = {g: {k: v['hex'] for k, v in roles.items() if k != 'scrim'}
         for g, roles in pal['roles'].items()}
    BASE = {str(s): v['hex'] for s, v in pal['base'].items()}
    PBASE = {str(s): v['hex'] for s, v in pal['paper']['base'].items()}
    AC = {n: {str(s): v['hex'] for s, v in scale.items()} for n, scale in pal['accents'].items()}
    WHITE, BLACK = pal['special']['white'], pal['special']['black']
    HL = {n: v['hex'] for n, v in pal['highlight'].items()}
    BG, BG2 = pal['bg']['bg'], pal['bg']['bg2']
    PBG, PBG2 = pal['paper']['bg'], pal['paper']['bg2']
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
    sel = selection_color(pal, light)
    inp = PBASE['50'] if kind == 'paper' else WHITE if light else BASE['900']
    err = AC['red']['600' if light else '300']
    warn = AC['orange']['600' if light else '300']
    info = AC['blue']['600' if light else '300']
    a = ansi(pal, kind)

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


def theme_context(pal, kind):
    """Resolve shared UI, syntax, and Markdown colors for one appearance."""
    if kind not in KINDS:
        raise ValueError(f'Unknown appearance: {kind}')
    roles = {g: {k: v['hex'] for k, v in values.items() if k != 'scrim'}
             for g, values in pal['roles'].items()}
    ui = roles['light'] | roles['light_high'] if kind == 'light' else roles[kind].copy()
    syn = roles[f'syntax_{kind}']
    if kind == 'dark':
        md = dict(heading=ui['tx'], body=ui['tx'], link=ui['link']) | {
            'code-inline-bg': ui['bg-2'], 'code-block-bg': ui['bg-2'],
            'quote-text': ui['tx-2'], 'quote-border': ui['ui-3'], 'hr': ui['ui-2']}
    else:
        md = roles['markdown_paper' if kind == 'paper' else 'markdown']
    return ui, syn, md


def ghostty_theme(pal, kind):
    ui, _, _ = theme_context(pal, kind)
    values = {
        'background': ui['bg'], 'foreground': ui['tx'],
        'cursor-color': ui['tx'], 'cursor-text': ui['bg'],
        'selection-background': selection_color(pal, kind != 'dark'),
        'selection-foreground': ui['tx'],
    }
    lines = [f'# Lucretia {kind.capitalize()}. Generated by scripts/build.py.',
             '# See THIRD_PARTY_NOTICES.md.']
    lines += [f'{key} = {value}' for key, value in values.items()]
    colors = ansi(pal, kind)
    lines += [f'palette = {i}={colors[name]}' for i, name in enumerate(ANSI_NAMES)]
    return '\n'.join(lines) + '\n'


def palette_colors(pal):
    """Named palette values, before app-specific role assignments."""
    colors = dict(pal['special'])
    colors.update({'page-light': pal['bg']['bg'], 'page-light-2': pal['bg']['bg2'],
                   'page-paper': pal['paper']['bg'], 'page-paper-2': pal['paper']['bg2']})
    for name, scale in {'base': pal['base'], 'pbase': pal['paper']['base'],
                        **pal['accents']}.items():
        colors.update({f'{name}-{step}': value['hex'] for step, value in scale.items()})
    colors.update({f'hl-{name}': value['hex'] for name, value in pal['highlight'].items()})
    return colors


def tokens_css(pal):
    lines = ['/* Generated by scripts/build.py. See THIRD_PARTY_NOTICES.md. */', ':root {']
    lines += [f'  --lu-{name}: {value};' for name, value in palette_colors(pal).items()]
    for kind, steps in pal['roles']['gallery']['scrim'].items():
        lines += [f'  --lu-scrim-{kind}-{step}: {value};' for step, value in steps.items()]
    lines.append('}')
    for kind in KINDS:
        ui, syn, md = theme_context(pal, kind)
        # Every appearance defines the same convenience variables, including nested previews.
        ui = {'card': ui['bg-2'], 'photo-surface': ui['bg'], **ui}
        lines.append(f'[data-lu-theme="{kind}"] {{')
        lines += [f'  --lu-{name}: {value};' for name, value in ui.items()]
        lines += [f'  --lu-syntax-{name}: {value};' for name, value in syn.items()]
        lines += [f'  --lu-markdown-{name}: {value};' for name, value in md.items()]
        lines.append(f'  --lu-selection: {selection_color(pal, kind != "dark")};')
        for name, scale in pal['accents'].items():
            step = 300 if kind == 'dark' else 600
            lines.append(f'  --lu-accent-{name}: {scale[step]["hex"]};')
        lines.append('}')
    return '\n'.join(lines) + '\n'


def css_rgb(hex_color):
    return ', '.join(map(str, hex_to_rgb(hex_color)))


def rgba(hex_color, alpha):
    return f'rgba({css_rgb(hex_color)}, {alpha})'


def obsidian_variables(pal, kind, minimal=False):
    """Colors only. Layout and typography remain the active theme's responsibility."""
    import colorsys
    ui, syn, md = theme_context(pal, kind)
    light = kind != 'dark'
    neutral = pal['paper']['base'] if kind == 'paper' else pal['base']
    base = lambda step: neutral[step]['hex']
    accent = lambda name: pal['accents'][name][600 if light else 300]['hex']
    bg, bg2, tx, tx2, tx3 = (ui[k] for k in ('bg', 'bg-2', 'tx', 'tx-2', 'tx-3'))
    hover = rgba(tx, '0.055')
    select = rgba(selection_color(pal, light), '0.55')
    form = base(50) if light else base(900)
    white = pal['special']['white']
    highlight = pal['highlight']['yellow']['hex']
    h, l, s = colorsys.rgb_to_hls(*(v / 255 for v in hex_to_rgb(ui['link'])))
    # Obsidian's base scale runs from the background to the foreground in both modes.
    steps = ((None, None, 50, 100, 150, 200, 300, 400, 500, 600, 700, None) if light
             else (None, None, 900, 850, 800, 700, 600, 500, 400, 300, 200, None))
    values = {f'color-base-{i:02d}': base(step) for i, step in
              zip((0, 5, 10, 20, 25, 30, 35, 40, 50, 60, 70, 100), steps) if step is not None}
    values.update({'color-base-00': bg, 'color-base-05': bg2, 'color-base-100': tx})
    values.update({
        'accent-h': f'{h * 360:.3f}', 'accent-s': f'{s * 100:.3f}%', 'accent-l': f'{l * 100:.3f}%',
        'color-accent': ui['link'], 'color-accent-1': ui['link'], 'color-accent-2': ui['link-hover'],
        'background-primary': bg, 'background-primary-alt': bg2,
        'background-secondary': bg2, 'background-secondary-alt': bg,
        'background-table-rows': bg2,
        'background-modifier-hover': hover, 'background-modifier-active-hover': hover,
        'background-modifier-border': ui['ui'], 'background-modifier-border-hover': ui['ui-2'],
        'background-modifier-border-focus': ui['ui-3'],
        'background-modifier-cover': rgba(tx, '0.18' if light else '0.08'),
        'background-modifier-form-field': form, 'background-modifier-form-field-highlighted': form,
        'divider-color': ui['ui'], 'frame-divider-color': ui['ui'],
        'ribbon-background': bg2, 'titlebar-background': bg2, 'titlebar-background-focused': bg2,
        'titlebar-text-color-focused': tx, 'mobile-sidebar-background': bg,
        'workspace-background-translucent': rgba(bg, '0.78'),
        'modal-background': bg, 'modal-border-color': ui['ui-2'], 'prompt-border-color': ui['ui-3'],
        'text-normal': tx, 'text-muted': tx2, 'text-faint': tx3, 'text-formatting': tx3,
        'text-accent': ui['link'], 'text-accent-hover': ui['link-hover'],
        'text-selection': select, 'text-highlight-bg': highlight,
        'text-highlight-bg-active': pal['accents']['yellow'][100]['hex'],
        'text-bold': tx, 'text-italic': tx, 'text-code': base(600) if light else tx2,
        'text-blockquote': tx2,
        'link-color': ui['link'], 'link-color-hover': ui['link-hover'],
        'link-external-color': ui['link'], 'link-external-color-hover': ui['link-hover'],
        'interactive-accent': ui['link'], 'interactive-accent-hover': ui['link-hover'],
        'interactive-accent-rgb': css_rgb(ui['link']),
        'interactive-normal': form, 'interactive-hover': ui['ui'],
        'text-on-accent': white if light else pal['special']['black'],
        'checkbox-color': ui['link'], 'checkbox-color-hover': ui['link-hover'],
        'checkbox-marker-color': white if light else pal['special']['black'],
        'focus-ring-color': ui['focus-ring'],
        'nav-item-color': tx2, 'nav-item-color-hover': tx, 'nav-item-color-active': tx,
        'nav-item-background-hover': hover, 'nav-item-background-active': hover,
        'nav-indentation-guide-color': ui['ui'], 'icon-color': tx2, 'icon-color-hover': tx,
        'icon-color-active': tx, 'scrollbar-thumb-bg': ui['ui'], 'scrollbar-active-thumb-bg': ui['ui-3'],
        'active-line-bg': rgba(tx, '0.035'), 'quote-opening-modifier': md['quote-border'],
        'blockquote-color': md['quote-text'], 'blockquote-border-color': md['quote-border'],
        'hr-color': md['hr'], 'code-background': md['code-inline-bg'],
        'code-normal': syn['variable'], 'code-comment': syn['comment'],
        'code-function': syn['definition'], 'code-keyword': syn['keyword'],
        'code-important': accent('red'), 'code-operator': syn['operator'],
        'code-property': syn['definition'], 'code-punctuation': syn['operator'],
        'code-string': syn['string'], 'code-tag': syn['keyword'], 'code-value': syn['number'],
        'tag-color': tx2, 'tag-background': base(100) if light else base(900),
        'tag-background-hover': base(150) if light else base(850),
        'tag-border-color': base(150) if light else base(850),
        'table-border-color': ui['ui'], 'table-header-background': bg2,
        'table-row-background-hover': hover,
    })
    for name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'inline-title'):
        values[f'{name}-color'] = md['heading']
    for name in pal['accents']:
        css_name = 'pink' if name == 'magenta' else name
        values[f'color-{css_name}'] = accent(name)
        values[f'color-{css_name}-rgb'] = css_rgb(accent(name))
    if minimal:
        values.update({
            'bg1': bg, 'bg2': bg2, 'bg3': hover,
            'ui1': ui['ui'], 'ui2': ui['ui-2'], 'ui3': ui['ui-3'],
            'tx1': tx, 'tx2': tx2, 'tx3': tx3, 'tx4': base(600) if light else tx2,
            'ax1': ui['link'], 'ax2': ui['link-hover'], 'ax3': ui['link'],
            'hl1': select, 'hl2': highlight,
            'sp1': white if light else pal['special']['black'],
            'mono100': tx, 'mono0': bg,
        })
    return values


STYLE_SETTINGS = '''/* @settings
name: Lucretia
id: lucretia
settings:
  - id: lucretia-light
    title: Lucretia Paper / Light
    description: Use Light instead of Paper in light mode. Dark mode is unchanged.
    type: class-toggle
    default: false
    addCommand: true
*/
'''


def obsidian_css(pal, minimal=False):
    lines = ['/* Generated by scripts/build.py. See THIRD_PARTY_NOTICES.md. */', STYLE_SETTINGS]
    for kind in ('paper', 'light', 'dark'):
        mode = 'dark' if kind == 'dark' else 'light'
        selector = f'body.theme-{mode}'
        if minimal:
            # Minimal presets use two classes. Match them so snippet load order applies.
            selector += f'.theme-{mode}'
        if kind == 'light':
            selector += '.lucretia-light'
        lines += [selector + ' {', f'  color-scheme: {mode};']
        lines += [f'  --{name}: {value};' for name, value in obsidian_variables(pal, kind, minimal).items()]
        lines.append('}')
        if kind == 'paper':
            # Retain the original Paper snippet's mobile backdrop opacity.
            ui, _, _ = theme_context(pal, kind)
            lines += [selector + ':not(.lucretia-light).is-mobile {',
                      f'  --workspace-background-translucent: {rgba(ui["bg"], "0.84")};',
                      f'  --background-modifier-cover: {rgba(ui["tx"], "0.22")};', '}']
    # Highlight fills are light in every appearance; they need dark text in Dark too.
    lines += ['body:is(.theme-light, .theme-dark) :is(mark, .cm-highlight) {',
              f'  color: {pal["special"]["black"]};', '}']
    for name, value in pal['highlight'].items():
        lines += [f'body:is(.theme-light, .theme-dark) .hl-{name} {{',
                  f'  background-color: {value["hex"]};',
                  f'  color: {pal["special"]["black"]};', '}']
    return '\n'.join(lines) + '\n'
