from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
FIG_DIR = Path(__file__).resolve().parent / "figures"


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
    FIG_DIR.mkdir(exist_ok=True)
    fig.savefig(FIG_DIR / f"{name}.png", bbox_inches="tight", dpi=160)
