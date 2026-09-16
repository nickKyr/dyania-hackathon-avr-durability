import os
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
FIG_DIR = Path(os.environ.get("AVR_FIG_DIR", Path(__file__).resolve().parent.parent / "figures"))


def use_style():
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": ["Helvetica Neue", "Arial", "DejaVu Sans"],
        "font.size": 10,
        "text.color": INK,
        "axes.labelcolor": INK_SECONDARY,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlepad": 12,
        "axes.edgecolor": AXIS,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK_SECONDARY,
        "ytick.labelcolor": INK_SECONDARY,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "legend.frameon": False,
        "lines.linewidth": 2,
        "figure.dpi": 110,
    })


def hbar(ax, labels, values, color=SERIES[0], value_fmt="{:,.0f}", xlabel=None):
    y = range(len(labels))
    ax.barh(y, values, height=0.62, color=color, edgecolor=SURFACE, linewidth=2)
    ax.set_yticks(list(y), labels)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.spines["left"].set_visible(False)
    top = max(values) if len(values) else 0
    for i, v in enumerate(values):
        ax.text(v + top * 0.01, i, value_fmt.format(v), va="center", fontsize=8.5, color=INK_SECONDARY)
    ax.set_xlim(0, top * 1.12 if top else 1)
    if xlabel:
        ax.set_xlabel(xlabel)
    return ax


def year_axis(ax):
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=12))
    ax.grid(axis="x", visible=False)


def save(fig, name):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / f"{name}.png", bbox_inches="tight", dpi=160)


CLASS_COLORS = {"no SVD": SERIES[0], "SVD": SERIES[1], "died first": SERIES[2]}
DIVERGING = ["#184f95", "#3987e5", "#9ec5f4", "#f0efec", "#f5b3b2", "#e66767", "#b02a2a"]


def diverging_cmap():
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list("blue_red", DIVERGING)


def box_by_class(ax, values, classes, title):
    order = [c for c in CLASS_COLORS if c in set(classes.dropna())]
    data = [values[(classes == c) & values.notna()] for c in order]
    parts = ax.boxplot(data, tick_labels=order, widths=0.55, patch_artist=True, showfliers=False,
                       medianprops=dict(color=INK, linewidth=1.5), whiskerprops=dict(color=MUTED), capprops=dict(color=MUTED))
    for patch, c in zip(parts["boxes"], order):
        patch.set_facecolor(CLASS_COLORS[c])
        patch.set_edgecolor(SURFACE)
        patch.set_alpha(0.85)
    ax.set_title(title, fontsize=9.5)
    ax.grid(axis="x", visible=False)
    ax.tick_params(axis="x", labelsize=8)
    ax.tick_params(axis="y", labelsize=8)


def heatmap(ax, frame, vmin=-1, vmax=1, fmt="{:.2f}", annotate=True, cmap=None):
    im = ax.imshow(frame.to_numpy(float), cmap=cmap or diverging_cmap(), vmin=vmin, vmax=vmax, aspect="auto")
    ax.set_xticks(range(frame.shape[1]), frame.columns, rotation=90, fontsize=7.5)
    ax.set_yticks(range(frame.shape[0]), frame.index, fontsize=7.5)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    if annotate:
        for i in range(frame.shape[0]):
            for j in range(frame.shape[1]):
                v = frame.iat[i, j]
                if np.isfinite(v):
                    ax.text(j, i, fmt.format(v), ha="center", va="center", fontsize=6.5, color=SURFACE if abs(v) > 0.6 * max(abs(vmin), abs(vmax)) else INK)
    return im


def pca_scatter(ax, coords, classes, explained):
    for c, color in CLASS_COLORS.items():
        m = (classes == c).to_numpy()
        if m.any():
            ax.scatter(coords[m, 0], coords[m, 1], s=9, color=color, alpha=0.55 if c == "no SVD" else 0.85, edgecolors=SURFACE, linewidths=0.3, label=f"{c} (n={m.sum()})")
    ax.set_xlabel(f"PC1 ({explained[0]:.0%} of variance)")
    ax.set_ylabel(f"PC2 ({explained[1]:.0%} of variance)")
    ax.legend(fontsize=8.5, markerscale=2)
