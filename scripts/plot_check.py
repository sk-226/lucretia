"""Lucretia chart-palette check plots.

Generates marker-less line plots with the Lucretia chart colors
(roles.presentation.chart-1..7 in palette.json) on three backgrounds:
  1. lucretia_light : bg #FDFCF7, grid
  2. lucretia_paper : paper bg #F8F5EB, grid
  3. matlab_default : white bg, box on, MATLAB-style grid

Unlike build.py this script needs numpy + matplotlib, so it is run manually;
the committed PNGs under assets/plots/ are referenced by review/overview.html.
Rerun it after changing the chart-1..7 roles; colors are resolved from scripts/palette.py.
"""

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

from palette import build_palette

OUT = Path(__file__).resolve().parent.parent / "assets" / "plots"

PALETTE = build_palette()


def role(group, name):
    return PALETTE["roles"][group][name]["hex"]


CHART = [
    (f"chart-{i} {PALETTE['roles']['presentation'][f'chart-{i}']['ref']}",
     role("presentation", f"chart-{i}"))
    for i in range(1, 8)
]

x = np.linspace(0, 10, 400)
curves = [
    np.exp(-0.12 * x) * np.sin(x - 0.55 * k) + 0.12 * k
    for k in range(len(CHART))
]

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 10,
    "axes.titlesize": 11,
    "legend.frameon": False,
    "lines.linewidth": 1.6,
})


def draw_lines(ax):
    for (label, hexcolor), y in zip(CHART, curves):
        ax.plot(x, y, color=hexcolor, label=label)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_xlim(0, 10)


def lucretia_fig(bg, grid, spine, tx, tx2, title):
    fig, ax = plt.subplots(figsize=(7.2, 4.2), facecolor=bg)
    ax.set_facecolor(bg)
    draw_lines(ax)

    ax.grid(True, color=grid, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(spine)
    ax.tick_params(colors=tx2, labelcolor=tx2, direction="out")

    ax.set_title(title, color=tx, loc="left", fontweight="bold")
    ax.xaxis.label.set_color(tx2)
    ax.yaxis.label.set_color(tx2)
    leg = ax.legend(loc="upper right", ncols=2, fontsize=8)
    for t in leg.get_texts():
        t.set_color(tx)
    fig.tight_layout()
    return fig


def matlab_fig(title):
    fig, ax = plt.subplots(figsize=(7.2, 4.2), facecolor="white")
    ax.set_facecolor("white")
    draw_lines(ax)

    # MATLAB defaults: box on, inward ticks, GridColor 0.15 @ alpha 0.15
    ax.grid(True, color=(0.15, 0.15, 0.15), alpha=0.15, linewidth=0.6)
    ax.set_axisbelow(True)
    for side in ax.spines.values():
        side.set_color((0.15, 0.15, 0.15))
        side.set_linewidth(0.8)
    ax.tick_params(direction="in", top=True, right=True,
                   colors=(0.15, 0.15, 0.15), labelcolor=(0.15, 0.15, 0.15))

    ax.set_title(title, color=(0.15, 0.15, 0.15), fontweight="bold")
    leg = ax.legend(loc="upper right", ncols=2, fontsize=8)
    fig.tight_layout()
    return fig


figs = {
    "lucretia_light": lucretia_fig(
        bg=role("light", "bg"), grid=role("light", "ui-2"),
        spine=role("light", "ui-3"),
        tx=role("light_high", "tx"), tx2=role("light_quiet", "tx-2"),
        title="Lucretia chart palette - light bg"),
    "lucretia_paper": lucretia_fig(
        bg=role("paper", "bg"), grid=role("paper", "ui-2"),
        spine=role("paper", "ui-3"),
        tx=role("paper", "tx"), tx2=role("paper", "tx-2"),
        title="Lucretia chart palette - paper bg"),
    "matlab_default": matlab_fig("Lucretia chart palette - MATLAB default axes"),
}

OUT.mkdir(parents=True, exist_ok=True)
for name, fig in figs.items():
    fig.savefig(OUT / f"{name}.png", dpi=180)
    print("saved", OUT / f"{name}.png")
