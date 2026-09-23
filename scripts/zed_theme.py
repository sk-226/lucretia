"""Zed theme family, using the shared palette rather than copied HEX values."""
from color import hex_to_rgb, rgb_to_hex
from export import KINDS, ansi, selection_color, theme_context

SCHEMA = 'https://zed.dev/schema/themes/v0.2.0.json'


def zed_manifest(version):
    """The build validates VERSION before generating this data-only extension."""
    return ('id = "lucretia"\n'
            'name = "Lucretia"\n'
            f'version = "{version}"\n'
            'schema_version = 1\n'
            'authors = ["sk-226"]\n'
            'description = "Light, Dark, and Paper color themes for code and notes."\n'
            'repository = "https://github.com/sk-226/lucretia"\n')


def zed_theme(pal, kind):
    ui, syn, md = theme_context(pal, kind)
    light = kind != 'dark'
    bg, bg2 = ui['bg'], ui['bg-2']
    tx, tx2, tx3 = ui['tx'], ui['tx-2'], ui['tx-3']
    selection = selection_color(pal, light)
    transparent = '#00000000'

    def accent(name, light_step=600, dark_step=300):
        # Accept both the generator's integer keys and JSON's string keys.
        scale = {str(step): value['hex'] for step, value in pal['accents'][name].items()}
        return scale[str(light_step if light else dark_step)]

    style = {
        'background': bg,
        'background.appearance': 'opaque',
        'surface.background': bg2,
        'elevated_surface.background': bg2,
        'border': ui['ui-3'],
        'border.variant': ui['ui'],
        'border.focused': ui['focus-ring'],
        'border.selected': ui['focus-ring'],
        'border.transparent': transparent,
        'border.disabled': ui['ui'],
        'element.background': bg2,
        'element.hover': ui['ui'],
        'element.active': ui['ui-2'],
        'element.selected': selection,
        'element.disabled': bg2,
        'ghost_element.background': transparent,
        'ghost_element.hover': ui['ui'],
        'ghost_element.active': ui['ui-2'],
        'ghost_element.selected': selection,
        'ghost_element.disabled': transparent,
        'drop_target.background': selection + '80',
        'text': tx,
        'text.muted': tx2,
        'text.placeholder': tx3,
        'text.disabled': tx3,
        'text.accent': ui['link'],
        'icon': tx2,
        'icon.muted': tx3,
        'icon.placeholder': tx3,
        'icon.disabled': tx3,
        'icon.accent': ui['link'],
        'link_text.hover': ui['link-hover'],
        'status_bar.background': bg2,
        'title_bar.background': bg2,
        'title_bar.inactive_background': bg2,
        'toolbar.background': bg,
        'tab_bar.background': bg2,
        'tab.active_background': bg,
        'tab.inactive_background': bg2,
        'panel.background': bg2,
        'panel.focused_border': ui['focus-ring'],
        'panel.indent_guide': ui['ui'],
        'panel.indent_guide_hover': ui['ui-2'],
        'panel.indent_guide_active': ui['ui-3'],
        'pane.focused_border': ui['focus-ring'],
        'pane_group.border': ui['ui'],
        'scrollbar.thumb.background': tx3 + '33',
        'scrollbar.thumb.hover_background': tx3 + '55',
        'scrollbar.thumb.border': transparent,
        'scrollbar.track.background': transparent,
        'scrollbar.track.border': transparent,
        'editor.background': bg,
        'editor.foreground': tx,
        'editor.gutter.background': bg,
        'editor.subheader.background': bg2,
        'editor.active_line.background': bg2,
        'editor.highlighted_line.background': ui['ui'],
        'editor.line_number': tx3,
        'editor.active_line_number': tx2,
        'editor.invisible': ui['ui-2'],
        'editor.wrap_guide': ui['ui'],
        'editor.active_wrap_guide': ui['ui-3'],
        'editor.indent_guide': ui['ui'],
        'editor.indent_guide_active': ui['ui-3'],
        'editor.document_highlight.read_background': accent('blue', 100, 850) + '80',
        'editor.document_highlight.write_background': accent('magenta', 100, 850) + '80',
        'editor.document_highlight.bracket_background': ui['ui'],
        'search.match_background': (pal['highlight']['yellow']['hex'] if light
                                    else accent('yellow', 150, 850)),
        'terminal.background': bg,
        'terminal.foreground': tx,
        'terminal.bright_foreground': tx,
        'terminal.dim_foreground': tx2,
        'terminal.ansi.background': bg,
    }
    # Git and diagnostic status colors share the same palette hues as VS Code.
    statuses = {
        'conflict': accent('orange'), 'created': accent('green', 600, 400),
        'deleted': accent('red'), 'error': accent('red'), 'hidden': tx3,
        'hint': tx3, 'ignored': tx3, 'info': accent('blue'),
        'modified': accent('blue'), 'predictive': tx3, 'renamed': accent('blue'),
        'success': accent('green', 600, 400), 'unreachable': tx3,
        'warning': accent('orange'),
    }
    for name, color in statuses.items():
        style[name] = color
        style[f'{name}.background'] = color + '14'
        style[f'{name}.border'] = color + '66'

    terminal = ansi(pal, kind)
    for name, color in terminal.items():
        zed_name = 'bright_' + name[6:].lower() if name.startswith('bright') else name
        style[f'terminal.ansi.{zed_name}'] = color
        if not name.startswith('bright'):
            # Zed has eight extra dim slots. Blend toward the current background
            # so dim text is subdued on light as well as dark appearances.
            dim = rgb_to_hex(*(round((2 * fg + back) / 3)
                               for fg, back in zip(hex_to_rgb(color), hex_to_rgb(bg))))
            style[f'terminal.ansi.dim_{name}'] = dim

    hues = ('blue', 'orange', 'purple', 'cyan', 'magenta', 'green')
    style['accents'] = [accent(name) for name in hues]
    # Player zero is the local cursor; do not inherit another theme's selection.
    style['players'] = [dict(cursor=tx, background=tx, selection=selection)]
    style['players'] += [dict(cursor=accent(name), background=accent(name),
                              selection=accent(name) + '40') for name in hues]

    def token(color, font_style='normal', font_weight=400):
        # Explicit normal styles prevent fallback themes from adding italics.
        return dict(color=color, font_style=font_style, font_weight=font_weight)

    syntax = {}
    groups = (
        (tx, ('attribute', 'embedded', 'label', 'namespace', 'primary', 'property',
              'variable', 'variable.special', 'variable.parameter', 'parameter')),
        (syn['definition'], ('constructor', 'enum', 'function', 'method', 'type',
                             'type.builtin', 'tag')),
        (syn['keyword'], ('keyword', 'preproc', 'tag.doctype')),
        (syn['string'], ('string', 'string.regex', 'string.special')),
        (syn['number'], ('boolean', 'constant', 'constant.builtin', 'number',
                         'string.escape', 'string.special.symbol', 'variant')),
        (syn['operator'], ('operator', 'punctuation', 'punctuation.bracket',
                           'punctuation.delimiter', 'punctuation.list_marker',
                           'punctuation.special')),
        (tx3, ('hint', 'predictive')),
        (ui['link'], ('link_text', 'link_uri')),
    )
    for color, captures in groups:
        syntax.update({capture: token(color) for capture in captures})
    for capture in ('comment', 'comment.doc', 'comment.documentation'):
        syntax[capture] = token(syn['comment'], font_style='italic')
    syntax['title'] = token(tx, font_weight=700)
    syntax['emphasis'] = token(tx, font_style='italic')
    syntax['emphasis.strong'] = token(tx, font_weight=700)
    syntax['text.literal'] = token(tx) | {'background_color': md['code-inline-bg']}
    style['syntax'] = syntax
    return dict(name=f'Lucretia {kind.capitalize()}',
                appearance='light' if light else 'dark', style=style)


def zed_theme_family(pal):
    return {'$schema': SCHEMA, 'name': 'Lucretia', 'author': 'sk-226',
            'themes': [zed_theme(pal, kind) for kind in KINDS]}
