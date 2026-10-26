import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 7.5, "axes.titlesize": 7.8, "axes.labelsize": 7.5,
    "xtick.labelsize": 6.8, "ytick.labelsize": 6.8, "legend.fontsize": 6.5, "pdf.fonttype": 42, "ps.fonttype": 42,
    "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6, "xtick.major.width": 0.6,
    "ytick.major.width": 0.6, "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.5, "lines.linewidth": 1.3,
    "legend.frameon": False})
def save(fig, name):
    fig.savefig(name + ".pdf", bbox_inches="tight", pad_inches=0.01)
    fig.savefig(name + ".png", dpi=400, bbox_inches="tight", pad_inches=0.01)
    plt.close(fig)
