"""Generate the palette and the HTML review pages.

Outputs:
- palette.json      : the single source of truth for colors and role mappings
- out/swatches.html : final bg preview, scales, and syntax hierarchy checks
- out/contrast.html : WCAG/APCA matrices and tint-step usage checks
- out/cvd.html      : P/D/T simulations and pairwise ΔEok matrices
- out/roles.html    : role tables plus slide, Markdown, editor, and gallery mocks
- out/degrade.html  : simple projection/display degradation simulations
- out/tokens.css    : CSS variables generated from palette.json

The constants near the top are intentionally the edit surface; rerunning this
script refreshes every generated artifact.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from color import (oklch_to_hex, hex_to_oklch, clamp_chroma, deltaE_ok,
                   wcag, apca_lc, cvd_hex, hex_to_rgb, rgb_to_hex)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'out')

# ============================================================
# Design parameters from plan.md §4.3, seeded from measured Flexoki values.
# ============================================================
STEPS = [50, 100, 150, 200, 300, 400, 500, 600, 700, 800, 850, 900, 950]

# Shared lightness curve (step -> L).
L_BASE = {50: .96, 100: .92, 150: .88, 200: .84, 300: .76, 400: .66,
          500: .59, 600: .53, 700: .46, 800: .39, 850: .35, 900: .30, 950: .24}

# Chroma peaks in the middle but never reaches zero, preserving an ink-like tint.
C_FACTOR = {50: .25, 100: .35, 150: .45, 200: .55, 300: .75, 400: .95,
            500: 1.0, 600: 1.0, 700: .92, 800: .80, 850: .72, 900: .62, 950: .50}

# Hue-specific lightness offsets are strongest near the center of each scale.
L_DELTA_W = {50: .15, 100: .30, 150: .45, 200: .60, 300: .85, 400: 1.0,
             500: 1.0, 600: 1.0, 700: .85, 800: .65, 850: .55, 900: .45, 950: .30}

# Hue, max chroma, and the lightness delta measured at step 600.
ACCENTS = {
    #        H,    Cmax,  Ldelta
    'red':     (28,  .165, -.026),
    'orange':  (47,  .152, +.037),
    'yellow':  (87,  .135, +.103),
    'green':   (122, .134, +.029),
    'cyan':    (187, .100, +.024),
    'blue':    (252, .132, -.048),
    'purple':  (294, .145, -.076),
    'magenta': (350, .161, -.035),
}

# The neutral base won in Phase 1; the earlier warm-base option is not used.
BASE = dict(H=97, C_light=.002, C_dark=.002)

# Phase 1 finalized former option A as the general-purpose background.
BG = (0.990, 0.006, 95)
BG2_OFFSET = (-0.025, +0.002)  # bg-2 = (L+dL, C+dC)

WHITE = '#FFFFFF'
BLACK_L, BLACK_C = 0.17, 0.002

# ------------------------------------------------------------
# lucretia paper is scoped to long-form reading. It lowers L and raises warm C
# to approximate paper comfort; presentation and gallery use stay on the
# neutral profile because those contexts need less color cast around images.
# ------------------------------------------------------------
# P2 is the final paper background; P1/P3 remain rejected alternatives.
PAPER_BG = (0.970, 0.014, 92)
# Paper gets its own warm base because the neutral base looks cool on warm bg.
PAPER_BASE = dict(H=92, C_light=.014, C_dark=.006)


# ============================================================
# Generation
# ============================================================

def gen_accent(name):
    H, cmax, ld = ACCENTS[name]
    out = {}
    for s in STEPS:
        L = min(0.97, max(0.08, L_BASE[s] + ld * L_DELTA_W[s]))
        C = clamp_chroma(L, cmax * C_FACTOR[s], H)
        out[s] = dict(hex=oklch_to_hex(L, C, H), oklch=[round(L, 4), round(C, 4), H])
    return out


# Highlighters are brighter and more chromatic than tint-150 so they read as
# marker ink, not panels. They are restricted to black text; L=0.93 is the
# lowest tested value where every hue still reaches body-grade |Lc| >= 90.
HL_L, HL_CFACTOR = 0.93, 0.85


def gen_highlight():
    out = {}
    for n, (H, cmax, _) in ACCENTS.items():
        C = clamp_chroma(HL_L, cmax * HL_CFACTOR, H)
        out[n] = dict(hex=oklch_to_hex(HL_L, C, H), oklch=[HL_L, round(C, 4), H])
    return out


def gen_base(cfg=BASE):
    out = {}
    for s in STEPS:
        L = L_BASE[s]
        t = (L - L_BASE[950]) / (L_BASE[50] - L_BASE[950])  # 1=light, 0=dark
        C = cfg['C_dark'] + (cfg['C_light'] - cfg['C_dark']) * t
        C = clamp_chroma(L, C, cfg['H'])
        out[s] = dict(hex=oklch_to_hex(L, C, cfg['H']),
                      oklch=[round(L, 4), round(C, 4), cfg['H']])
    return out


# ============================================================
# Role mappings stay as palette references so generated artifacts cannot drift
# from palette.json. Hex values are resolved only at output time.
# References: 'white', 'black', 'bg', 'bg2', 'base-600', 'blue-600', etc.
# ============================================================
ROLES = {
    # Shared light UI roles.
    'light': dict(
        bg='bg', bg_2='bg2', card='white',
        ui='base-100', ui_2='base-150', ui_3='base-200',
        link='blue-600', link_hover='blue-800', visited='purple-600',
        focus_ring='blue-400',
        # White is reserved for raised surfaces; using it as a page bg was too stark.
        photo_surface='bg',
    ),
    # Two text profiles let quiet surfaces opt out of maximum contrast.
    'light_high': dict(tx='black', tx_2='base-700', tx_3='base-500'),
    'light_quiet': dict(tx='base-800', tx_2='base-600', tx_3='base-400'),
    # Dark coding/gallery surfaces use true black because base-950 left
    # base-100 below the APCA body target in measurement.
    'dark': dict(
        bg='black', bg_2='base-950',
        ui='base-900', ui_2='base-850', ui_3='base-800',
        tx='base-100', tx_2='base-300', tx_3='base-500',
        link='blue-300', link_hover='blue-200', visited='purple-300',
        focus_ring='blue-300',
        photo_surface='base-950',       # Final: a near-neutral surface one step above black.
    ),
    # Keywords use magenta because purple sat too close to definition blue under
    # deuteranopia simulation; numbers keep purple within the original plan.
    'syntax_light': dict(
        variable='black', definition='blue-600', keyword='magenta-600',
        string='green-600', number='purple-600',
        operator='base-500', comment='base-400',
    ),
    # Dark syntax centers on step 300; step 400 was too dim on black. Strings
    # alone stay at green-400 so they do not outrank Tier-2 definitions.
    'syntax_dark': dict(
        variable='base-100', definition='blue-300', keyword='magenta-300',
        string='green-400', number='purple-300',
        operator='base-300', comment='base-500',
    ),
    # Presentation inherits high-contrast light text roles.
    'presentation': dict(
        emphasis_1='blue-600', emphasis_2='red-600',
        sub_1='green-600', sub_2='orange-600',
        sub_3='yellow-600',             # Large/bold only; yellow is weak for body text.
        note_fill='red-100', note_text='red-800',
        info_fill='blue-100', info_text='blue-800',
        # The chart order assumes multi-series plots and mixes lightness bands
        # for CVD resilience. A greedy search maximized the worst pairwise ΔEok
        # for each prefix, but marks/line styles are still required.
        chart_1='blue-400', chart_2='orange-600', chart_3='purple-600',
        chart_4='red-300', chart_5='yellow-500', chart_6='cyan-600',
        chart_7='green-500',
    ),
    # Markdown editor roles.
    'markdown': dict(
        heading='black', body='black', link='blue-600',
        code_inline_bg='base-50', code_block_bg='bg2',
        quote_text='base-700', quote_border='base-150', hr='base-150',
    ),
    # Gallery scrims are expanded into alpha steps during role resolution.
    'gallery': dict(caption='base-600', meta='base-400'),
    # Highlighters are only for base text or bold base text. They are not used
    # under colored links because color-on-color muddies the semantic cue.
    'highlight': {n: f'hl-{n}' for n in ACCENTS},
    # Paper uses pbase-900 as book ink: it meets high-contrast targets without
    # the glare of black on a warm page. White is intentionally absent.
    'paper': dict(
        bg='paper-bg', bg_2='paper-bg2',
        ui='pbase-100', ui_2='pbase-150', ui_3='pbase-200',
        tx='pbase-900', tx_2='pbase-700', tx_3='pbase-500',
        link='blue-600', link_hover='blue-800', visited='purple-600',
        focus_ring='blue-400',
    ),
    # Paper syntax keeps the light hue/step assignments; only neutral tokens
    # swap to warm pbase after contrast checks on P2.
    'syntax_paper': dict(
        variable='pbase-900', definition='blue-600', keyword='magenta-600',
        string='green-600', number='purple-600',
        operator='pbase-500', comment='pbase-400',
    ),
    # Reading headings stay neutral and slightly deeper to create hierarchy.
    'markdown_paper': dict(
        heading='pbase-950', body='pbase-900', link='blue-600',
        code_inline_bg='pbase-100', code_block_bg='paper-bg2',
        quote_text='pbase-700', quote_border='pbase-200', hr='pbase-150',
    ),
}
SCRIM_ALPHAS = (5, 10, 20, 40, 60, 80)  # % (plan.md §6.4 overlay-scrim)


def resolve_ref(pal, ref):
    if ref in ('white', 'black'):
        return pal['special'][ref]
    if ref in ('bg', 'bg2'):
        return pal['bg'][ref]
    if ref in ('paper-bg', 'paper-bg2'):
        return pal['paper'][ref.replace('paper-', '')]
    if ref.startswith('hl-'):
        return pal['highlight'][ref[3:]]['hex']
    name, step = ref.rsplit('-', 1)
    if name == 'base':
        scale = pal['base']
    elif name == 'pbase':
        scale = pal['paper']['base']
    else:
        scale = pal['accents'][name]
    return scale[int(step)]['hex']


def build_roles(pal):
    out = {}
    for group, roles in ROLES.items():
        out[group] = {k.replace('_', '-'): dict(ref=v, hex=resolve_ref(pal, v))
                      for k, v in roles.items()}
    out['gallery']['scrim'] = dict(
        black={a: f'rgba(16,15,14,{a / 100})' for a in SCRIM_ALPHAS},
        white={a: f'rgba(255,255,255,{a / 100})' for a in SCRIM_ALPHAS})
    return out


def build_palette():
    pal = dict(meta=dict(source='build.py',
                         note='Phase 1 finalized bg=option A and base=neutral. '
                              'Phase 3 roles remain draft where marked provisional.'))
    pal['special'] = dict(white=WHITE,
                          black=oklch_to_hex(BLACK_L, BLACK_C, 97))
    L, C, H = BG
    bg = oklch_to_hex(L, C, H)
    bg2 = oklch_to_hex(L + BG2_OFFSET[0], C + BG2_OFFSET[1], H)
    pal['bg'] = dict(bg=bg, bg2=bg2, oklch=[L, C, H],
                     dE_white=round(deltaE_ok(bg, WHITE), 4),
                     dE_paper=round(deltaE_ok(bg, '#FFFCF0'), 4))
    # Paper profile.
    pL, pC, pH = PAPER_BG
    pbg = oklch_to_hex(pL, pC, pH)
    pal['paper'] = dict(
        bg=pbg, bg2=oklch_to_hex(pL + BG2_OFFSET[0], pC + BG2_OFFSET[1], pH),
        oklch=[pL, pC, pH],
        dE_bg=round(deltaE_ok(pbg, bg), 4),
        dE_white=round(deltaE_ok(pbg, WHITE), 4),
        base=gen_base(PAPER_BASE))
    pal['base'] = gen_base()
    pal['accents'] = {n: gen_accent(n) for n in ACCENTS}
    pal['highlight'] = gen_highlight()
    pal['roles'] = build_roles(pal)
    return pal


# ============================================================
# Shared HTML helpers.
# ============================================================
CSS = """
body{font-family:-apple-system,'Helvetica Neue',sans-serif;margin:0;padding:24px;
     background:#F2F2F2;color:#222;font-size:14px}
h1{font-size:20px}h2{font-size:16px;margin-top:32px}h3{font-size:14px}
.small{color:#666;font-size:12px}
table{border-collapse:collapse;background:#fff}
td,th{border:1px solid #DDD;padding:4px 8px;font-size:12px;text-align:center}
.chip{display:inline-block;width:64px;padding:14px 0 4px;margin:1px;border-radius:4px;
      text-align:center;font-size:10px;vertical-align:top}
.card{display:inline-block;vertical-align:top;margin:8px;padding:20px;border-radius:8px;
      width:300px;border:1px solid #DDD}
.wbox{background:#FFFFFF;border-radius:6px;padding:10px;margin:10px 0;
      box-shadow:0 1px 3px rgba(0,0,0,.06)}
pre{border-radius:8px;padding:14px;font-size:12.5px;line-height:1.6;
    font-family:ui-monospace,'SF Mono',Menlo,monospace}
.p2{background:#E8F5E9}.p1{background:#FFFDE7}.p0{background:#FFF3E0}.pf{background:#FFEBEE}
"""

# Public preview pages are committed under out/, so their sample copy should not
# encode the author's research topics, local workflow, or personal captions. The
# examples below intentionally use generic product/content language: it still
# exercises headings, links, code, warnings, highlights, and long-form reading,
# but it does not leak personal context. We avoid Lorem Ipsum because real words
# are better for judging rhythm, contrast, and link/highlight weight.
READING_SAMPLE = (
    'Long-form reading depends on a careful balance between page brightness '
    'and ink density. Stable spacing, line height, and quieter secondary text '
    'make it easier to return to the body copy. The reading profile therefore '
    'avoids overly white surfaces while letting links and inline code rise '
    'only as much as they need to.'
)


def text_color_for(hexbg):
    return '#111' if hex_to_oklch(hexbg)[0] > 0.62 else '#FFF'


def chip(hexv, label):
    return (f'<div class="chip" style="background:{hexv};color:{text_color_for(hexv)}">'
            f'{label}<br>{hexv}</div>')


# ============================================================
# swatches.html
# ============================================================

def html_swatches(pal):
    h = [f'<!doctype html><meta charset="utf-8"><title>swatches</title><style>{CSS}</style>']
    h.append('<h1>Color Theme Swatches (Generated Draft)</h1>'
             '<p class="small">Generated from the initial parameters in plan.md §4. '
             'Use this page during Phase 1-2 to tune the constants in build.py.</p>')

    # Phase 1 finalized this single background, so the preview compares usage.
    h.append('<h2>1. Background (Phase 1 final: former option A) - '
             'white cards, body text, accents, and tint fills</h2>')
    blk = pal['special']['black']
    b6, r6 = pal['accents']['blue'][600]['hex'], pal['accents']['red'][600]['hex']
    g6 = pal['accents']['green'][600]['hex']
    tx2 = pal['base'][600]['hex']

    # Tint fills use same-hue dark text to verify practical alert/info boxes.
    TINT_HUES = ('blue', 'red', 'yellow', 'orange', 'green')

    def tint_rows():
        rows = []
        for n in TINT_HUES:
            c50 = pal['accents'][n][50]['hex']
            c100 = pal['accents'][n][100]['hex']
            c800 = pal['accents'][n][800]['hex']
            rows.append(
                f'<div style="display:flex;gap:4px;margin:3px 0;font-size:11px">'
                f'<div style="flex:1;background:{c50};color:{c800};border-radius:4px;'
                f'padding:3px 6px">{n}-50 {c50}</div>'
                f'<div style="flex:1;background:{c100};color:{c800};border-radius:4px;'
                f'padding:3px 6px">{n}-100 {c100}</div></div>')
        return ''.join(rows)

    for k, d in (('bg', pal['bg']),):
        h.append(
            f'<div class="card" style="background:{d["bg"]}">'
            f'<b style="color:{blk}">{k}</b> <span class="small">{d["bg"]} '
            f'(ΔE white {d["dE_white"]}, paper {d["dE_paper"]})</span>'
            f'<div class="wbox"><span style="color:{blk}">Body text on a white card.</span> '
            f'<span style="color:{b6}">emphasis</span> / <span style="color:{r6}">warning</span></div>'
            f'<p style="color:{blk};margin:6px 0">Body text directly on bg. '
            f'<span style="color:{tx2}">Secondary text (gray).</span> '
            f'<b style="color:{g6}">Green secondary color.</b></p>'
            f'<div style="background:{d["bg2"]};border-radius:6px;padding:8px;color:{blk}">'
            f'bg-2 panel {d["bg2"]}</div>'
            f'<div style="margin-top:8px">{tint_rows()}</div>'
            f'</div>')
    # Flexoki paper remains a visual reference, not a candidate.
    h.append(f'<div class="card" style="background:#FFFCF0">'
             f'<b style="color:{blk}">Reference: Flexoki paper</b> <span class="small">#FFFCF0</span>'
             f'<div class="wbox"><span style="color:{blk}">Body text on a white card.</span></div>'
             f'<p style="color:{blk}">Body text directly on bg.</p>'
             f'<div style="margin-top:8px">{tint_rows()}</div></div>')

    # Neutral base scale.
    h.append('<h2>2. base scale (Phase 1 final: neutral)</h2><div>')
    h.append(chip(pal['special']['white'], 'white'))
    for s in STEPS:
        h.append(chip(pal['base'][s]['hex'], f'base-{s}'))
    h.append(chip(pal['special']['black'], 'black'))
    h.append('</div>')

    # Accent scales.
    h.append('<h2>3. Accent palette: 8 hues x 13 steps</h2>')
    for name in ACCENTS:
        h.append(f'<h3>{name}</h3><div>')
        for s in STEPS:
            h.append(chip(pal['accents'][name][s]['hex'], f'{s}'))
        h.append('</div>')

    # Highlighters.
    h.append('<h2>3b. Highlighters (hl-*, marker colors for black text only)</h2><div>')
    for name in ACCENTS:
        h.append(chip(pal['highlight'][name]['hex'], f'hl-{name}'))
    h.append('</div>')

    # Syntax hierarchy demo.
    h.append('<h2>4. Code Hierarchy Demo (§6.3 sparse highlighting)</h2>'
             '<p class="small">Tier 1 variables = tx (neutral) / '
             'Tier 2 definitions = blue, keywords = magenta / '
             'Tier 3 strings = green, numbers = purple / Tier 4 comments = tx-3</p>')

    def code_sample(bg, tx, tx2, tx3, kw, fn, st, num):
        return (f'<pre style="background:{bg};color:{tx}">'
                f'<span style="color:{tx3}"># Build a display label for the public catalog</span>\n'
                f'<span style="color:{kw}">def</span> <span style="color:{fn}">format_product_label</span>(item, locale):\n'
                f'    total = item.price <span style="color:{tx2}">*</span> item.quantity\n'
                f'    total = total <span style="color:{tx2}">*</span> <span style="color:{num}">1.10</span>\n'
                f'    <span style="color:{kw}">if</span> locale <span style="color:{tx2}">==</span> '
                f'<span style="color:{st}">"en"</span>:\n'
                f'        <span style="color:{kw}">return</span> item.name <span style="color:{tx2}">+</span> '
                f'<span style="color:{st}">" - $"</span> <span style="color:{tx2}">+</span> str(round(total, '
                f'<span style="color:{num}">2</span>))\n'
                f'    <span style="color:{kw}">return</span> item.name  '
                f'<span style="color:{tx3}"># default label</span></pre>')

    # Pull colors from ROLES so this preview stays aligned with generated themes.
    sd = {k: v['hex'] for k, v in pal['roles']['syntax_dark'].items()}
    sl = {k: v['hex'] for k, v in pal['roles']['syntax_light'].items()}
    dk = {k: v['hex'] for k, v in pal['roles']['dark'].items()}
    h.append('<h3>Dark (syntax_dark role / bg = black)</h3>')
    h.append(code_sample(dk['bg'], sd['variable'], sd['operator'], sd['comment'],
                         sd['keyword'], sd['definition'], sd['string'], sd['number']))
    h.append('<h3>Light (syntax_light role / bg = bg)</h3>')
    h.append(code_sample(pal['bg']['bg'], sl['variable'], sl['operator'], sl['comment'],
                         sl['keyword'], sl['definition'], sl['string'], sl['number']))
    return ''.join(h)


# ============================================================
# contrast.html
# ============================================================

def rate(w, lc):
    """Classify contrast using the WCAG/APCA targets from plan.md."""
    a = abs(lc)
    if w >= 7 and a >= 90:
        return 'p2', 'High body'
    if w >= 4.5 and a >= 75:
        return 'p1', 'Quiet body OK'
    if w >= 3 and a >= 60:
        return 'p0', 'Large/bold only'
    return 'pf', 'Fail'


def matrix(title, fgs, bgs, note=''):
    h = [f'<h2>{title}</h2>']
    if note:
        h.append(f'<p class="small">{note}</p>')
    h.append('<table><tr><th>fg \\ bg</th>')
    for bn, bh in bgs:
        h.append(f'<th>{bn}<br>{bh}</th>')
    h.append('</tr>')
    for fn, fh in fgs:
        h.append(f'<tr><th style="background:{fh};color:{text_color_for(fh)}">{fn}<br>{fh}</th>')
        for bn, bh in bgs:
            w, lc = wcag(fh, bh), apca_lc(fh, bh)
            cls, lab = rate(w, lc)
            h.append(f'<td class="{cls}">{w:.2f}:1<br>Lc {lc:+.0f}<br>{lab}</td>')
        h.append('</tr>')
    h.append('</table>')
    return ''.join(h)


def html_contrast(pal):
    ac, bs = pal['accents'], pal['base']
    blk, wht = pal['special']['black'], pal['special']['white']
    h = [f'<!doctype html><meta charset="utf-8"><title>contrast</title><style>{CSS}</style>',
         '<h1>Contrast Matrix (WCAG 2.x + APCA Lc)</h1>',
         '<p class="small">Ratings follow the targets in plan.md: '
         'High body = body text (≥7:1 & |Lc|≥90) / '
         'Quiet body OK = quiet body text (≥4.5 & ≥75) / '
         'Large/bold only = display or bold text only (≥3 & ≥60) / '
         'Fail = decorative use only</p>']

    light_bgs = [('bg', pal['bg']['bg']), ('bg-2', pal['bg']['bg2']), ('white', wht)]
    light_fgs = ([('black', blk)]
                 + [(f'base-{s}', bs[s]['hex']) for s in (800, 700, 600)]
                 + [('tx-navy (blue-900)', ac['blue'][900]['hex'])]
                 + [(f'{n}-600', ac[n][600]['hex']) for n in ACCENTS])
    h.append(matrix('Light theme', light_fgs, light_bgs))

    dark_bgs = [('base-950', bs[950]['hex']), ('black', blk)]
    dark_fgs = ([('white', wht)]
                + [(f'base-{s}', bs[s]['hex']) for s in (100, 200, 300)]
                + [(f'{n}-400', ac[n][400]['hex']) for n in ACCENTS]
                + [(f'{n}-300', ac[n][300]['hex']) for n in ('blue', 'green')])
    h.append(matrix('Dark theme', dark_fgs, dark_bgs,
                    'APCA is negative for light text on dark backgrounds. '
                    'WCAG 2.x tends to overestimate dark-theme contrast (plan.md §5.1).'))

    tint_bgs = [(f'{n}-100', ac[n][100]['hex']) for n in ('red', 'blue', 'green', 'yellow')]
    tint_fgs = ([('black', blk)]
                + [(f'{n}-800', ac[n][800]['hex']) for n in ('red', 'blue', 'green', 'yellow')])
    h.append(matrix('Text on tint fills (100)', tint_fgs, tint_bgs,
                    'Checks the planned use of same-hue 800 text on tint-100 fills (plan.md §6.1).'))

    # Tint visibility is checked separately because WCAG/APCA do not model fills.
    h.append('<h2>Tint Fill Visibility (50-200): ΔEok vs Background</h2>'
             '<p class="small">Checks whether a fill remains visible on bg without a border. '
             'The screening threshold is ΔEok ≥ 0.02 (plan.md §4.4). '
             'Projection can still erase these fills, so use a border or luminance gap as needed (§5.4).</p>')
    h.append('<table><tr><th>color \\ fill</th>')
    for s in (50, 100, 150, 200):
        h.append(f'<th>{s}</th>')
    h.append('</tr>')
    bgh = pal['bg']['bg']
    for n in ACCENTS:
        h.append(f'<tr><th>{n} (vs bg)</th>')
        for s in (50, 100, 150, 200):
            hx = ac[n][s]['hex']
            d = deltaE_ok(hx, bgh)
            cls = 'p2' if d >= 0.02 else 'pf'
            mark = 'OK' if d >= 0.02 else 'Fail'
            h.append(f'<td class="{cls}" style="background:{hx}">'
                     f'{hx}<br>ΔE {d:.3f} {mark}</td>')
        h.append('</tr>')
    h.append('</table>')

    # Highlighters must preserve body-grade black-text contrast.
    hl_bgs = [(f'hl-{n}', pal['highlight'][n]['hex']) for n in ACCENTS]
    h.append(matrix('Black Text on Highlighters (hl-*)', [('black', blk)], hl_bgs,
                    'Marker lines are allowed only behind tx (black) and its bold form. '
                    'Body-grade contrast (≥7:1 & |Lc|≥90) is required.'))

    # Tint steps may be text only on much darker same-hue backgrounds.
    h.append('<h2>Tint Steps (50-200) as Text: APCA on Same-Hue Dark Backgrounds (700-950)</h2>'
             '<p class="small">Marked OK at quiet body grade |Lc| ≥ 75. '
             'This documents use rules such as red-100 text only on red-800 or darker (plan.md §4.4).</p>')
    for n in ACCENTS:
        fgs = [(f'{n}-{s}', ac[n][s]['hex']) for s in (50, 100, 150, 200)]
        bgs = [(f'{n}-{s}', ac[n][s]['hex']) for s in (700, 800, 850, 900, 950)]
        h.append(matrix(f'{n}', fgs, bgs))
    return ''.join(h)


# ============================================================
# cvd.html (plan.md §5.1 CVD simulation)
# ============================================================
CVD_KINDS = [('Original (no simulation)', None), ('Protanopia', 'protan'),
             ('Deuteranopia', 'deutan'), ('Tritanopia', 'tritan')]

# These empirical ΔEok thresholds only screen category-confusion risk.
CVD_DE_BAD, CVD_DE_WARN = 0.04, 0.08


def html_cvd(pal):
    ac = pal['accents']
    h = [f'<!doctype html><meta charset="utf-8"><title>cvd</title><style>{CSS}</style>',
         '<h1>CVD Simulation (Machado 2009, severity 1.0)</h1>',
         '<p class="small">plan.md §5.1: checks whether emphasis colors (red/blue) and '
         'secondary accents (green/orange/yellow) do not rely on hue alone. '
         'ΔEok pair distance: '
         f'Fail &lt; {CVD_DE_BAD} (high confusion risk) / Warn &lt; {CVD_DE_WARN} / OK otherwise. '
         'These are screening thresholds; final decisions still require swatch review and real use, '
         'with no meaning carried by color alone (§1).</p>']

    for step, usage in ((600, 'light emphasis and syntax band'),
                        (400, 'shape/chart band and dark syntax band (plan.md §6.1, §6.3)')):
        h.append(f'<h2>step {step} — {usage}</h2>')
        for label, kind in CVD_KINDS:
            h.append(f'<h3>{label}</h3><div>')
            for n in ACCENTS:
                hx = ac[n][step]['hex']
                sim = cvd_hex(hx, kind) if kind else hx
                h.append(chip(sim, n))
            h.append('</div>')
            # Pairwise distances expose hue pairs that need non-color encodings.
            sims = {n: (cvd_hex(ac[n][step]['hex'], kind) if kind else ac[n][step]['hex'])
                    for n in ACCENTS}
            names = list(ACCENTS)
            h.append('<table><tr><th>ΔEok</th>')
            for n in names:
                h.append(f'<th>{n}</th>')
            h.append('</tr>')
            worst = []
            for i, n1 in enumerate(names):
                h.append(f'<tr><th>{n1}</th>')
                for j, n2 in enumerate(names):
                    if j <= i:
                        h.append('<td></td>')
                        continue
                    d = deltaE_ok(sims[n1], sims[n2])
                    cls = 'pf' if d < CVD_DE_BAD else ('p0' if d < CVD_DE_WARN else 'p2')
                    if d < CVD_DE_WARN:
                        worst.append((d, n1, n2))
                    h.append(f'<td class="{cls}">{d:.3f}</td>')
                h.append('</tr>')
            h.append('</table>')
            if worst:
                worst.sort()
                h.append('<p class="small">Watch pairs: '
                         + ', '.join(f'{a}–{b} ({d:.3f})' for d, a, b in worst) + '</p>')
    return ''.join(h)


# ============================================================
# roles.html (plan.md §6 role tables and usage mocks)
# ============================================================

def html_roles(pal):
    R = {g: {k: v['hex'] for k, v in d.items() if k != 'scrim'}
         for g, d in pal['roles'].items()}
    li, hi, qu = R['light'], R['light_high'], R['light_quiet']
    da, pr, md, sl = R['dark'], R['presentation'], R['markdown'], R['syntax_light']
    h = [f'<!doctype html><meta charset="utf-8"><title>roles</title><style>{CSS}</style>',
         '<h1>Role Mapping (Phase 3 Draft)</h1>',
         '<p class="small">plan.md §6. photo-surface and the dark gallery surface are provisional '
         '(§9 open items). The source of truth is build.py ROLES -> palette.json roles.</p>']

    # Role table.
    for group, roles in pal['roles'].items():
        h.append(f'<h2>{group}</h2><table><tr><th>Role</th><th>Reference</th><th>Hex</th><th>Sample</th></tr>')
        for k, v in roles.items():
            if k == 'scrim':
                continue
            h.append(f'<tr><td>{k}</td><td>{v["ref"]}</td><td>{v["hex"]}</td>'
                     f'<td style="background:{v["hex"]}">&nbsp;&nbsp;&nbsp;&nbsp;</td></tr>')
        h.append('</table>')

    # Slide mock.
    h.append('<h2>Mock 1: Slide (light_high + presentation)</h2>')
    h.append(
        f'<div style="width:640px;aspect-ratio:16/9;background:{li["bg"]};border:1px solid #DDD;'
        f'border-radius:8px;padding:28px;box-sizing:border-box">'
        f'<div style="font-size:22px;font-weight:700;color:{hi["tx"]}">'
        f'Accessible Color Roles</div>'
        f'<div style="font-size:12px;color:{hi["tx-2"]};margin:4px 0 14px">'
        f'Public sample slide</div>'
        f'<div style="font-size:14px;color:{hi["tx"]}">Body text, emphasis, warnings, and notes '
        f'stay predictable when each <b style="color:{pr["emphasis-1"]}">visual role is fixed</b>. '
        f'This mock keeps a Japanese check phrase: '
        f'<b style="color:{pr["emphasis-2"]}">状態の優先度</b> は色だけで伝えない。</div>'
        f'<div style="background:{pr["note-fill"]};color:{pr["note-text"]};border-radius:6px;'
        f'padding:8px 12px;margin:12px 0;font-size:13px">Warning: do not rely on color alone / 色だけで伝えない</div>'
        f'<div style="background:{pr["info-fill"]};color:{pr["info-text"]};border-radius:6px;'
        f'padding:8px 12px;font-size:13px">Note: pair color with icons or short labels.</div>'
        f'<div style="display:flex;gap:6px;align-items:center;margin-top:12px">'
        f'<span style="font-size:11px;color:{hi["tx-2"]}">chart 1–7:</span>'
        + ''.join(f'<span style="display:inline-block;width:34px;height:8px;border-radius:2px;'
                  f'background:{pr[f"chart-{i}"]}" title="chart-{i}"></span>'
                  for i in range(1, 8))
        + '</div>'
        f'<div style="margin-top:10px;font-size:11px;color:{hi["tx-3"]}">'
        f'public preview / sample content</div></div>')

    # Markdown mock.
    h.append('<h2>Mock 2: Markdown Editor (light_high + markdown)</h2>')
    h.append(
        f'<div style="width:560px;background:{li["bg"]};border:1px solid #DDD;border-radius:8px;'
        f'padding:20px 24px;color:{md["body"]};font-size:14px;line-height:1.7">'
        f'<div style="font-size:19px;font-weight:700;color:{md["heading"]};'
        f'border-bottom:1px solid {md["hr"]};padding-bottom:6px">Design Memo / デザインメモ</div>'
        f'<p>Separating links, body copy, and inline code keeps '
        f'<code style="background:{md["code-inline-bg"]};border-radius:3px;'
        f'padding:1px 5px">--color-accent</code> and other 短いトークン legible. '
        f'See <a style="color:{md["link"]}">documentation</a> for details.</p>'
        f'<p>Highlighters: '
        f'<mark style="background:{R["highlight"]["yellow"]};padding:0 2px">default yellow</mark>, '
        f'<mark style="background:{R["highlight"]["green"]};padding:0 2px">補助に緑</mark>、'
        f'<mark style="background:{R["highlight"]["blue"]};padding:0 2px">'
        f'<b>works under bold text</b></mark>, '
        f'<mark style="background:{R["highlight"]["red"]};padding:0 2px">warning red</mark>. '
        f'Black text only.</p>'
        f'<div style="border-left:3px solid {md["quote-border"]};color:{md["quote-text"]};'
        f'padding-left:12px;margin:10px 0">重要な状態は色だけでなく、ラベルでも示す。</div>'
        f'<pre style="background:{md["code-block-bg"]};color:{sl["variable"]};margin:0">'
        f'<span style="color:{sl["keyword"]}">if</span> score <span style="color:{sl["operator"]}">&lt;</span> '
        f'<span style="color:{sl["number"]}">0.8</span>:\n'
        f'    <span style="color:{sl["keyword"]}">return</span> '
        f'<span style="color:{sl["string"]}">"Needs review"</span></pre></div>')

    # Code editor mock.
    h.append('<h2>Mock 3: Code Editor (syntax_light / syntax_dark + dist/vscode equivalent)</h2>'
             '<p class="small">§6.3 sparse highlighting: variables and calls stay neutral (Tier 1); '
             'only keywords = magenta, definitions = blue, strings = green, and numbers = purple receive hue. '
             'The lower band shows terminal ANSI colors (normal / bright).</p>')

    def editor_mock(kind):
        light = kind == 'light'
        ui = {**R['light'], **R['light_high']} if light else R['dark']
        syn = R['syntax_light'] if light else R['syntax_dark']
        ebg = pal['bg']['bg'] if light else ui['bg']
        ebg2 = pal['bg']['bg2'] if light else ui['bg-2']
        sel = pal['accents']['blue'][150 if light else 850]['hex']
        tx, tx2, tx3 = ui['tx'], ui['tx-2'], ui['tx-3']
        K = lambda t: f'<span style="color:{syn["keyword"]}">{t}</span>'
        F = lambda t: f'<span style="color:{syn["definition"]}">{t}</span>'
        S = lambda t: f'<span style="color:{syn["string"]}">{t}</span>'
        N = lambda t: f'<span style="color:{syn["number"]}">{t}</span>'
        O = lambda t: f'<span style="color:{syn["operator"]}">{t}</span>'
        C = lambda t: f'<span style="color:{syn["comment"]};font-style:italic">{t}</span>'
        # The sample touches every syntax role while staying domain-neutral.
        # Variables remain tx; other token classes exercise their assigned hue.
        lines = [
            f'{K("import")} json',
            '',
            C('# Small UI model for the public preview (Tier 4 comment)'),
            f'{K("class")} {F("ProductCard")}:',
            f'    {S("&quot;&quot;&quot;Small data object used by the theme preview.&quot;&quot;&quot;")}',
            f'    {K("def")} {F("__init__")}(self, title, price{O("=")}{N("29.0")}, '
            f'featured{O("=")}{N("False")}):',
            f'        self.title {O("=")} title',
            f'        self.price {O("=")} price',
            f'        self.featured {O("=")} featured',
            f'        self.label {O("=")} {S("&quot;New&quot;")}',
            '',
            f'    {K("def")} {F("render")}(self, theme, discount{O("=")}{N("None")}):',
            f'        ratio {O("=")} {N("1.0")} {K("if")} discount {K("is")} {N("None")} '
            f'{K("else")} discount',
            f'        total {O("=")} self.price {O("*")} ratio',
            f'        {K("for")} index {K("in")} {F("range")}({N("3")}):',
            f'            total {O("=")} total {O("+")} index {O("*")} {N("0.5")}',
            f'            {K("if")} <span style="background:{sel}">total</span> {O("&lt;")} {N("20.0")}:',
            f'                self.featured {O("=")} {N("True")}',
            f'                {K("return")} theme.color({S("&quot;accent&quot;")}), total  ' + C('# sample branch'),
            f'        {K("raise")} {F("ValueError")}({S("&quot;price is outside the preview range&quot;")})',
        ]
        hl_line = 15  # 0-origin current-line highlight for the sample loop.
        rows = []
        for i, ln in enumerate(lines):
            lnc = tx2 if i == hl_line else tx3
            lbg = f'background:{ebg2};' if i == hl_line else ''
            rows.append(
                f'<div style="display:flex;{lbg}">'
                f'<span style="width:34px;text-align:right;padding-right:12px;'
                f'color:{lnc};user-select:none;flex-shrink:0">{i + 1}</span>'
                f'<span style="color:{tx};white-space:pre">{ln or " "}</span></div>')
        # ANSI chips verify terminal colors next to the editor roles.
        band_n, band_b = (600, 400) if light else (300, 200)
        ansi_chips = ''
        for band, lab in ((band_n, 'normal'), (band_b, 'bright')):
            ansi_chips += (f'<div style="display:flex;gap:4px;align-items:center;margin-top:4px">'
                           f'<span style="color:{tx3};font-size:10px;width:44px">{lab}</span>'
                           + ''.join(f'<span style="display:inline-block;width:30px;height:12px;'
                                     f'border-radius:2px;background:'
                                     f'{pal["accents"][c][band]["hex"]}"></span>'
                                     for c in ('red', 'green', 'yellow', 'blue',
                                               'magenta', 'cyan'))
                           + '</div>')
        name = f'Lucretia {"Light" if light else "Dark"}'
        return (
            f'<div style="display:inline-block;vertical-align:top;margin:8px;width:560px;'
            f'border:1px solid #CCC;border-radius:8px;overflow:hidden;'
            f'font-family:ui-monospace,\'SF Mono\',Menlo,monospace;font-size:12px">'
            # Tab bar.
            f'<div style="display:flex;background:{ebg2};font-size:11px">'
            f'<span style="background:{ebg};color:{tx};padding:6px 14px">product_card.py</span>'
            f'<span style="color:{tx2};padding:6px 14px">theme_preview.py</span></div>'
            # Editor body.
            f'<div style="background:{ebg};padding:10px 0;line-height:1.65">{"".join(rows)}</div>'
            # Terminal.
            f'<div style="background:{ebg};border-top:1px solid {ui["ui-3"]};padding:8px 12px">'
            f'<span style="color:{tx3};font-size:10px">TERMINAL (ANSI)</span>{ansi_chips}</div>'
            # Status bar.
            f'<div style="background:{ebg2};color:{tx2};font-size:10px;'
            f'padding:4px 12px">{name} — Python · UTF-8 · Ln 16, Col 13</div>'
            f'</div>')

    h.append(editor_mock('light'))
    h.append(editor_mock('dark'))

    # Gallery mock.
    h.append('<h2>Mock 4: Gallery (photo-surface + scrim)</h2>'
             '<p class="small">Uses real photos to check photo-adjacent surfaces and scrims across '
             'bright, dark, and colorful image areas (plan.md §6.4).</p>')
    # CSS layered backgrounds keep the page robust when a checkout does not have
    # the photo fixtures. The captions stay generic so the committed preview does
    # not turn into a personal photo essay; the images only provide luminance and
    # color variation for checking the gallery roles.
    photos = [
        ('../assets/photos/photo-1.jpg',
         'linear-gradient(135deg,#7A8A99 0%,#C9B8A0 55%,#E8DCC8 100%)',
         'Bright area / 明るい面 - black scrim 60%'),
        ('../assets/photos/photo-2.jpg',
         'linear-gradient(160deg,#0A0A0A 0%,#2E2E2E 60%,#6E6E6E 100%)',
         'Dark area / 暗い面 - black scrim 60%'),
        ('../assets/photos/photo-3.jpg',
         'linear-gradient(160deg,#2E3B33 0%,#8A3B2E 60%,#B98F55 100%)',
         'Colorful area / 多色面 - black scrim 60%'),
    ]
    sc = pal['roles']['gallery']['scrim']
    ga = R['gallery']
    ps_l = pal['roles']['light']['photo-surface']['ref']
    ps_d = pal['roles']['dark']['photo-surface']['ref']
    for label, surface, txc in ((f'Light (photo-surface = {ps_l})', li['photo-surface'], hi),
                                (f'Dark (photo-surface = {ps_d})', da['photo-surface'],
                                 {'tx': da['tx'], 'tx-2': da['tx-2'], 'tx-3': da['tx-3']})):
        h.append(
            f'<div class="card" style="background:{surface};width:360px">'
            f'<div style="color:{txc["tx"]};font-weight:600;margin-bottom:8px">{label}</div>')
        for i, (src, fallback, cap) in enumerate(photos):
            h.append(
                f'<div style="background:url(\'{src}\') center/cover,{fallback};'
                f'height:150px;border-radius:4px;position:relative;margin-top:{8 if i else 0}px">'
                f'<div style="position:absolute;bottom:0;left:0;right:0;background:{sc["black"][60]};'
                f'color:#FFF;font-size:11px;padding:5px 8px;border-radius:0 0 4px 4px">{cap}</div>'
                f'<div style="position:absolute;top:6px;left:6px;background:{sc["black"][40]};'
                f'color:#FFF;font-size:11px;padding:2px 8px;border-radius:3px">scrim 40%</div>'
                f'</div>'
                f'<div style="color:{ga["caption"]};font-size:12px;margin:4px 0 0">Caption / キャプション (caption)</div>'
                f'<div style="color:{ga["meta"]};font-size:11px">f/8 · 1/250s · ISO 100 (meta)</div>')
        h.append('</div>')
    return ''.join(h)


# ============================================================
# paper.html (plan.md §6.5 reading profile review)
# ============================================================

def html_paper(pal):
    P = pal['paper']
    pb = {s: v['hex'] for s, v in P['base'].items()}
    R = {g: {k: v['hex'] for k, v in pal['roles'][g].items()}
         for g in ('paper', 'syntax_paper', 'markdown_paper', 'highlight')}
    pa, syn, md = R['paper'], R['syntax_paper'], R['markdown_paper']
    h = [f'<!doctype html><meta charset="utf-8"><title>paper</title><style>{CSS}</style>',
         '<h1>lucretia paper - Long-Form Reading Profile (plan.md §6.5)</h1>',
         '<p class="small">Goal: a digital approximation of paper-like reading comfort '
         '(lower luminance, warm surface, low glare). Presentation and gallery use are out of scope. '
         'bg is finalized as P2 (natural paper tone) (plan.md §9-16).</p>']

    # Compare the final paper bg with useful references under identical text.
    h.append('<h2>1. Final bg (P2) - Compared with Reference Colors Using the Same Reading Sample</h2>')
    long_p = READING_SAMPLE
    o = P['oklch']
    refs = [('paper-bg (final P2)', P['bg'], f'({o[0]}, {o[1]}, {o[2]}°)'),
            ('current bg', pal['bg']['bg'], '(0.990, 0.006, 95°)'),
            ('Flexoki paper', '#FFFCF0', '(0.990, 0.016, 95°)')]
    for name, bgh, oklch in refs:
        mark = ' [selected]' if bgh == P['bg'] else ''
        h.append(
            f'<div class="card" style="background:{bgh};width:340px">'
            f'<b style="color:{pa["tx"]}">{name}{mark}</b> '
            f'<span class="small">{bgh} {oklch} — ΔE white '
            f'{deltaE_ok(bgh, WHITE):.3f}</span>'
            f'<p style="color:{pa["tx"]};font-size:13.5px;line-height:1.9;margin:8px 0">'
            f'{long_p}</p>'
            f'<p style="color:{pa["tx-2"]};font-size:12px;margin:4px 0">Secondary text: '
            f'notes, <a style="color:{pa["link"]}">link rendering</a>, '
            f'<code style="background:{md["code-inline-bg"]};border-radius:3px;'
            f'padding:1px 5px;color:{pa["tx"]}">inline-token</code></p>'
            f'<div style="background:{md["code-block-bg"]};border-radius:5px;padding:6px 10px;'
            f'font-size:11.5px;color:{pa["tx-2"]}">bg-2-like surface (code block background)</div>'
            f'</div>')

    # Warm paper base scale.
    h.append('<h2>2. pbase scale (warm H=92; neutral base looks bluish on warm bg)</h2><div>')
    for s in STEPS:
        h.append(chip(pb[s], f'pbase-{s}'))
    h.append('</div><div style="margin-top:6px">Comparison: neutral base')
    for s in (500, 700, 900):
        h.append(chip(pal['base'][s]['hex'], f'base-{s}'))
    h.append('</div>')

    # Paper contrast matrix.
    pfgs = ([('tx (pbase-900)', pa['tx']), ('tx-2 (pbase-700)', pa['tx-2']),
             ('tx-3 (pbase-500)', pa['tx-3']), ('black (reference)', pal['special']['black'])]
            + [(f'{n}-600', pal['accents'][n][600]['hex']) for n in ACCENTS])
    pbgs = [('paper-bg', P['bg']), ('paper-bg2', P['bg2'])]
    h.append(matrix('3. Contrast for paper roles', pfgs, pbgs,
                    'tx is the book-ink band: it reaches High body (≥7:1 & |Lc|≥90) '
                    'while avoiding the glare of black. Syntax step 600 stays at the same '
                    'level as the current light theme.'))

    # Reading mock.
    h.append('<h2>4. Reading Mock (markdown_paper + highlighters)</h2>')
    h.append(
        f'<div style="width:600px;background:{P["bg"]};border:1px solid #DDD;border-radius:8px;'
        f'padding:26px 30px;color:{md["body"]};font-size:14.5px;line-height:1.95">'
        f'<div style="font-size:20px;font-weight:700;color:{md["heading"]};'
        f'border-bottom:1px solid {md["hr"]};padding-bottom:8px">Long-Form Reading Sample</div>'
        f'<p>{long_p}</p>'
        f'<p><mark style="background:{R["highlight"]["yellow"]};padding:0 2px;color:{md["body"]}">'
        f'Important sentences keep the body text color and use only the marker layer</mark>. This works like '
        f'<code style="background:{md["code-inline-bg"]};border-radius:3px;padding:1px 5px">'
        f'line-height</code> and spacing: it makes rereading easier. See '
        f'<a style="color:{md["link"]}">reading notes</a> for details.</p>'
        f'<div style="border-left:3px solid {md["quote-border"]};color:{md["quote-text"]};'
        f'padding-left:14px;margin:12px 0">Quotes and side notes sit one step below the body copy '
        f'so they do not interrupt long paragraphs.</div>'
        f'<pre style="background:{md["code-block-bg"]};color:{syn["variable"]};margin:0">'
        f'<span style="color:{syn["keyword"]}">if</span> contrast '
        f'<span style="color:{syn["operator"]}">&lt;</span> '
        f'<span style="color:{syn["number"]}">4.5</span>:\n'
        f'    <span style="color:{syn["keyword"]}">return</span> '
        f'<span style="color:{syn["string"]}">"review"</span>  '
        f'<span style="color:{syn["comment"]};font-style:italic"># sample threshold</span></pre>'
        f'</div>')
    return ''.join(h)


# ============================================================
# tokens.css (CSS variables generated from palette.json)
# ============================================================

def gen_tokens_css(pal):
    ln = ['/* lucretia color theme - generated by scripts/build.py. Do not edit by hand. */',
          ':root {',
          f'  --lu-white: {pal["special"]["white"]};',
          f'  --lu-black: {pal["special"]["black"]};',
          f'  --lu-bg: {pal["bg"]["bg"]};',
          f'  --lu-bg-2: {pal["bg"]["bg2"]};',
          f'  --lu-paper-bg: {pal["paper"]["bg"]};',
          f'  --lu-paper-bg-2: {pal["paper"]["bg2"]};']
    for s in STEPS:
        ln.append(f'  --lu-base-{s}: {pal["base"][s]["hex"]};')
    for s in STEPS:
        ln.append(f'  --lu-pbase-{s}: {pal["paper"]["base"][s]["hex"]};')
    for n in ACCENTS:
        for s in STEPS:
            ln.append(f'  --lu-{n}-{s}: {pal["accents"][n][s]["hex"]};')
    for n in ACCENTS:
        ln.append(f'  --lu-hl-{n}: {pal["highlight"][n]["hex"]};')
    for kind, steps in pal['roles']['gallery']['scrim'].items():
        for a, v in steps.items():
            ln.append(f'  --lu-scrim-{kind}-{a}: {v};')
    ln.append('}')

    def block(sel, groups):
        ln.append(f'{sel} {{')
        for g in groups:
            for k, v in pal['roles'][g].items():
                if k == 'scrim':
                    continue
                ln.append(f'  --{k}: {v["hex"]};')
        ln.append('}')

    block('[data-theme="light"]', ('light', 'light_high'))
    block('[data-theme="light"][data-contrast="quiet"]', ('light_quiet',))
    block('[data-theme="dark"]', ('dark',))
    block('[data-theme="paper"]', ('paper',))
    return '\n'.join(ln) + '\n'


# ============================================================
# degrade.html (plan.md §5.4 degradation simulation)
# ============================================================
DEGRADE_MODES = [
    ('original', 'Original', None),
    ('desat', 'Saturation -20% (color-shifted projector)', 'desat'),
    ('gamma', 'Gamma 1.25 (darker midtones)', 'gamma'),
    ('lifted', 'Black lift + range compression (budget projection)', 'lifted'),
]


def degrade(hx, mode):
    if mode == 'desat':
        L, C, H = hex_to_oklch(hx)
        return oklch_to_hex(L, C * 0.8, H)
    if mode == 'gamma':
        return rgb_to_hex(*(round(255 * (c / 255) ** 1.25) for c in hex_to_rgb(hx)))
    if mode == 'lifted':
        return rgb_to_hex(*(round(255 * (0.12 + 0.78 * c / 255)) for c in hex_to_rgb(hx)))
    return hx


def html_degrade(pal):
    hi = {k: v['hex'] for k, v in pal['roles']['light_high'].items()}
    pr = {k: v['hex'] for k, v in pal['roles']['presentation'].items()}
    h = [f'<!doctype html><meta charset="utf-8"><title>degrade</title><style>{CSS}</style>',
         '<h1>Degradation Simulation (plan.md §5.4)</h1>',
         '<p class="small">A quick screening view for degradation from projection and budget monitors. '
         'It is not a substitute for checking a real projector. Compare whether tint fills remain visible '
         'and secondary text remains readable.</p>']
    for key, label, mode in DEGRADE_MODES:
        d = lambda x: degrade(x, mode)
        bg = d(pal['bg']['bg'])
        h.append(
            f'<div class="card" style="background:{bg}">'
            f'<b style="color:{d(hi["tx"])}">{label}</b>'
            f'<p style="color:{d(hi["tx"])};margin:6px 0;font-size:13px">Body text. '
            f'<span style="color:{d(hi["tx-2"])}">Secondary text.</span> '
            f'<span style="color:{d(hi["tx-3"])}">faint.</span></p>'
            f'<p style="margin:6px 0;font-size:13px">'
            f'<b style="color:{d(pr["emphasis-1"])}">Blue emphasis</b> / '
            f'<b style="color:{d(pr["emphasis-2"])}">Red emphasis</b> / '
            f'<span style="color:{d(pr["sub-1"])}">Green</span> / '
            f'<b style="color:{d(pr["sub-3"])}">Yellow (bold only)</b></p>'
            f'<div style="background:{d(pr["note-fill"])};color:{d(pr["note-text"])};'
            f'border-radius:5px;padding:6px 10px;font-size:12px;margin:6px 0">red-100 warning box</div>'
            f'<div style="background:{d(pr["info-fill"])};color:{d(pr["info-text"])};'
            f'border-radius:5px;padding:6px 10px;font-size:12px">blue-100 info box</div>'
            f'<div style="display:flex;gap:4px;margin-top:8px">'
            + ''.join(f'<div style="flex:1;height:22px;border-radius:3px;'
                      f'background:{d(pal["accents"][n][50]["hex"])}"></div>'
                      for n in ('blue', 'red', 'yellow', 'orange', 'green'))
            + '</div><div class="small" style="margin-top:2px">50-step fills (no border)</div>'
            f'</div>')
    return ''.join(h)


# ============================================================
if __name__ == '__main__':
    pal = build_palette()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(ROOT, 'palette.json'), 'w') as f:
        json.dump(pal, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, 'swatches.html'), 'w') as f:
        f.write(html_swatches(pal))
    with open(os.path.join(OUT, 'contrast.html'), 'w') as f:
        f.write(html_contrast(pal))
    with open(os.path.join(OUT, 'cvd.html'), 'w') as f:
        f.write(html_cvd(pal))
    with open(os.path.join(OUT, 'roles.html'), 'w') as f:
        f.write(html_roles(pal))
    with open(os.path.join(OUT, 'degrade.html'), 'w') as f:
        f.write(html_degrade(pal))
    with open(os.path.join(OUT, 'paper.html'), 'w') as f:
        f.write(html_paper(pal))
    with open(os.path.join(OUT, 'tokens.css'), 'w') as f:
        f.write(gen_tokens_css(pal))

    # Console output is intentionally compact so regeneration can be checked by eye.
    print('generated: palette.json, out/{swatches,contrast,cvd,roles,degrade,paper}.html, '
          'out/tokens.css')
    d = pal['bg']
    print(f"\n-- bg (final) --\n  {d['bg']} (bg2 {d['bg2']}, "
          f"dE_white {d['dE_white']}, dE_paper {d['dE_paper']})")
    p = pal['paper']
    print(f"\n-- paper bg (final P2) --\n  {p['bg']} (bg2 {p['bg2']}, "
          f"dE_bg {p['dE_bg']}, dE_white {p['dE_white']})")
    for role in ('tx', 'tx-2', 'tx-3'):
        hx = pal['roles']['paper'][role]['hex']
        print(f"  {role:5s} {hx}  {wcag(hx, p['bg']):5.2f}:1  Lc {apca_lc(hx, p['bg']):+6.1f}")
    print('\n-- 600 step on bg: WCAG / APCA --')
    bgh = pal['bg']['bg']
    for n in ACCENTS:
        hx = pal['accents'][n][600]['hex']
        print(f"  {n:8s} {hx}  {wcag(hx, bgh):5.2f}:1  Lc {apca_lc(hx, bgh):+6.1f}")

    print('\n-- CVD: closest 3 pairs (ΔEok, step 400 / 600) --')
    for step in (400, 600):
        for kind in ('protan', 'deutan', 'tritan'):
            sims = {n: cvd_hex(pal['accents'][n][step]['hex'], kind) for n in ACCENTS}
            names = list(ACCENTS)
            pairs = sorted((deltaE_ok(sims[a], sims[b]), a, b)
                           for i, a in enumerate(names) for b in names[i + 1:])
            print(f"  {step} {kind:7s}: "
                  + ', '.join(f'{a}-{b} {d:.3f}' for d, a, b in pairs[:3]))
