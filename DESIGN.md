# Design

Palette parameters and role assignments are defined in `scripts/palette.py`.

## Background and neutral colors

Light uses `#FDFCF7`, generated from OKLCH `(0.990, 0.006, 95)`.
Its second background is `#F5F3EE`. Pure white is a separate raised-surface color,
not the page background. The neutral base has chroma near `0.002`.

Dark uses `#100F0E` for the page and `base-950` for the second background.
Using `black` for the page gives `base-100` body text more contrast than `base-950`.
The palette name `black` does not mean pure `#000000`.

Paper uses `#F8F5EB`, generated from OKLCH `(0.970, 0.014, 92)`.
Its second background is `#F0EDE1`; body text is `pbase-900`, `#2F2E2A`.
Its separate warm neutral scale has hue `92` and chroma from `0.006` to `0.014`.
Paper uses warm neutrals for long-form reading and avoids large pure-white
surfaces.

## Accent scales

The eight accents are red, orange, yellow, green, cyan, blue, purple, and magenta.
Each has thirteen steps: 50, 100, 150, 200, 300, 400, 500, 600, 700, 800, 850,
900, and 950. Lower steps are lighter. The shared lightness curve has hue-specific
offsets; chroma is clamped to the sRGB gamut. Color conversions and evaluation
functions are defined in `scripts/color.py`.

## Role assignments

Variables, parameters, and properties keep the text color. Definitions use blue,
keywords magenta, strings green, and numbers purple. Operators and comments use
neutral colors. Light and Paper syntax use step 600 accents. Dark uses step 300,
except for strings at green-400. Paper substitutes its warm neutrals for the
neutral syntax colors. The JSON distinguishes syntax roles from UI text roles;
they are not interchangeable.

The ANSI mapping is shared by VS Code, Ghostty, Vim, and Neovim. Light and Paper use normal
accents at 600 and bright accents at 400. Dark uses 300 and 200. Paper changes
the neutral slots, not the chromatic ANSI hues. Bright terminal colors are kept
for terminal compatibility; they are not general-purpose body text colors.

Presentation emphasis uses blue-600 and red-600. Yellow-600 is reserved for
large or bold use rather than normal body text. Do not distinguish adjacent
orange and green marks by hue alone. Use labels, line styles, or shapes as well.

The seven chart roles are ordered:
blue-400, orange-600, purple-600, red-300, yellow-500, cyan-600, green-500.
The order mixes lightness bands. It does not remove the need for non-color cues.

Each highlighter uses lightness `0.93` and chroma `0.85` times the hue's maximum,
subject to gamut clamping. These fills need dark text, including in Dark mode.
Do not place colored links or syntax text on them without checking the result.

The light photo surface matches the light background. The dark photo surface
is `base-950`. The JSON also includes gallery scrims, an optional quiet text
profile, and presentation roles. Paper is a reading profile and has no photo
surface or presentation roles.

Tint fills (steps 50 to 200) take same-hue 800 text, as in the presentation
note and info boxes. A fill should differ from the page background by at least
ΔEok 0.02 to stay visible without a border. Tint steps can be used as text only
on same-hue backgrounds of 800 or darker, and only where the pair reaches the
quiet text target.

## Evaluation

High-contrast body text targets WCAG contrast of at least 7:1 and APCA magnitude
of at least 90. The quiet profile targets 4.5:1 and APCA magnitude 75.
Colors that reach only 3:1 and APCA magnitude 60 are limited to large or bold text.
These targets do not establish accessibility conformance for every UI element.
Font size, weight, context, and non-color cues still affect readability.
Faint syntax and decorative colors are
not substitutes for body text.

The review pages show contrast matrices, sRGB / OKLCH values, simulated protan,
deutan, and tritan vision, and simple saturation, gamma, and black-level changes.
These simulations do not establish how the theme looks on a real projector,
mobile screen, or every user's display. Check representative applications before
publishing. See `demo/README.md`.
