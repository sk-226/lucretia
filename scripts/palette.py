"""Palette parameters and role assignments. This is the color source."""
from color import oklch_to_hex, clamp_chroma, deltaE_ok, hex_to_rgb

# ============================================================
# Design parameters, seeded from measured Flexoki values. DESIGN.md explains them.
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

# The general-purpose scale is nearly neutral; Paper has its own warm scale.
BASE = dict(H=97, C_light=.002, C_dark=.002)

# General-purpose page background.
BG = (0.990, 0.006, 95)
BG2_OFFSET = (-0.025, +0.002)  # bg-2 = (L+dL, C+dC)

WHITE = '#FFFFFF'
BLACK_L, BLACK_C = 0.17, 0.002

# ------------------------------------------------------------
# lucretia paper is scoped to long-form reading. It lowers L and raises warm C
# to approximate paper comfort; presentation and gallery use stay on the
# neutral profile because those contexts need less color cast around images.
# ------------------------------------------------------------
# Warm page background for reading.
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
# from the generated palette. Hex values are resolved only at output time.
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
    # Dark coding/gallery surfaces use the black palette color because base-950 left
    # base-100 below the APCA body target in measurement.
    'dark': dict(
        bg='black', bg_2='base-950',
        ui='base-900', ui_2='base-850', ui_3='base-800',
        tx='base-100', tx_2='base-300', tx_3='base-500',
        link='blue-300', link_hover='blue-200', visited='purple-300',
        focus_ring='blue-300',
        photo_surface='base-950',       # A near-neutral surface one step above black.
    ),
    # Keywords use magenta because purple sat too close to definition blue under
    # deuteranopia simulation.
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
    # swap to warm pbase for the Paper background.
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
SCRIM_ALPHAS = (5, 10, 20, 40, 60, 80)  # Gallery scrim opacities, in percent.


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
    out['gallery']['scrim'] = {}
    for name in ('black', 'white'):
        r, g, b = hex_to_rgb(pal['special'][name])
        out['gallery']['scrim'][name] = {a: f'rgba({r},{g},{b},{a / 100})' for a in SCRIM_ALPHAS}
    return out


def build_palette():
    pal = dict(meta=dict(source='scripts/palette.py',
                         note='Generated by scripts/build.py. Edit scripts/palette.py, not this file.'))
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

