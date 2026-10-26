"""PRISMA 2020 flow diagram (new systematic review, databases + citation searching).
Numbers come from prisma_numbers.json so the figure can be regenerated when full-text screening is done."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from style import plt, save
from matplotlib.patches import FancyBboxPatch

N = json.load(open(os.path.join(os.path.dirname(__file__), "prisma_numbers.json")))
def f(k):
    v = N.get(k)
    return "[pending]" if v is None else format(v, ",")

C_MAIN, C_SIDE, C_EDGE, C_BAND = "#EEF3FA", "#F7F7F7", "#4A6A94", "#2F4B73"
fig, ax = plt.subplots(figsize=(7.16, 6.1))
ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off"); ax.grid(False)

def box(x, y, w, h, text, fc=C_MAIN, bold_first=False, fs=6.6):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=0.8",
                                fc=fc, ec=C_EDGE, lw=0.7))
    lines = text.split("\n")
    if bold_first:
        ax.text(x + 1.2, y + h - 1.4, lines[0], ha="left", va="top", fontsize=fs, fontweight="bold", color="#1d1d1d")
        ax.text(x + 1.2, y + h - 4.3, "\n".join(lines[1:]), ha="left", va="top", fontsize=fs, color="#1d1d1d",
                linespacing=1.35)
    else:
        ax.text(x + 1.2, y + h - 1.4, text, ha="left", va="top", fontsize=fs, color="#1d1d1d", linespacing=1.35)

def arrow(x1, y1, x2, y2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", lw=0.7, color=C_EDGE, shrinkA=0, shrinkB=0, mutation_scale=7))

# headers
ax.add_patch(FancyBboxPatch((7, 95), 58, 4.2, boxstyle="round,pad=0.2,rounding_size=0.8", fc=C_BAND, ec=C_BAND))
ax.text(36, 97.1, "Identification of studies via databases", ha="center", va="center", color="white", fontsize=7.2,
        fontweight="bold")
ax.add_patch(FancyBboxPatch((70, 95), 29.5, 4.2, boxstyle="round,pad=0.2,rounding_size=0.8", fc="#6B7F99", ec="#6B7F99"))
ax.text(84.75, 97.1, "Identification via other methods", ha="center", va="center", color="white", fontsize=7.2,
        fontweight="bold")
# stage bands
for y0, y1, lab in [(77, 94, "Identification"), (44, 76, "Screening"), (8.5, 43, "Eligibility and inclusion")]:
    ax.add_patch(FancyBboxPatch((0, y0), 4.6, y1 - y0, boxstyle="round,pad=0.1,rounding_size=0.8", fc="#D8E2F0",
                                ec="none"))
    ax.text(2.3, (y0 + y1) / 2, lab, rotation=90, ha="center", va="center", fontsize=6.8, fontweight="bold",
            color=C_BAND)

# identification (databases)
box(7, 79, 26, 14.5, "Records identified (n = %s)\nOpenAlex (n = %s)\narXiv (n = %s)\nERIC (n = %s)" %
    (f("identified"), f("openalex"), f("arxiv"), f("eric")), bold_first=True)
box(38, 79, 27, 14.5, "Removed before screening\nDuplicates (n = %s)\nFailed automated three-block\nterm check (n = %s)" %
    (f("duplicates"), f("automation")), fc=C_SIDE, bold_first=True)
arrow(33, 86.2, 38, 86.2)
# citation searching
box(70, 79, 29.5, 14.5, "Citation searching of %s includes\nBackward and forward (n = %s)\nRemoved: known, pre-2020 or\noff-topic (n = %s)" %
    (f("seeds"), f("cit_identified"), f("cit_removed")), fc=C_SIDE, bold_first=True)

# screening
box(7, 66, 26, 8, "Records screened\nn = %s (title and abstract)" % f("screened"), bold_first=True)
box(38, 66, 27, 8, "Records excluded n = %s\nReinstated on verification n = 11" % f("screen_excluded"), fc=C_SIDE, bold_first=True)
arrow(20, 79, 20, 74); arrow(33, 70, 38, 70)
box(7, 55, 26, 8, "Reports sought for retrieval\nn = %s" % f("sought"), bold_first=True)
box(38, 55, 27, 8, "Full text not retrieved n = %s\nAbstract only %s; no abstract %s" % (f("not_retrieved"), f("abs_only"), f("awaiting")), fc=C_SIDE, bold_first=True)
arrow(20, 66, 20, 63); arrow(33, 59, 38, 59)
box(70, 66, 29.5, 8, "Records screened\nn = %s; excluded n = %s" % (f("cit_screened"), f("cit_excluded")), fc=C_SIDE,
    bold_first=True)
arrow(84.75, 79, 84.75, 74)
box(70, 55, 29.5, 8, "Sought n = %s; no full text n = %s\nAbstract only %s; no abstract %s" % (f("cit_sought"), f("cit_not_retrieved"), f("cit_abs_only"), f("cit_awaiting")),
    fc=C_SIDE, bold_first=True)
arrow(84.75, 66, 84.75, 63)

# eligibility
box(7, 30, 26, 21, "Reports assessed for eligibility\nn = %s\n\nFull text n = %s\nAbstract only n = %s" % (f("assessed_total"), f("assessed"), f("abs_only")), bold_first=True)
box(38, 30, 27, 21, "Reports excluded (n = %s)\nNot an LLM (n = %s)\nNot educational (n = %s)\nNo uncertainty/reliability focus\n(n = %s)\nOpinion, no method (n = %s)\nOther (n = %s)" %
    (f("ft_excluded"), f("ft_e1"), f("ft_e2"), f("ft_e3"), f("ft_e4"), f("ft_other")), fc=C_SIDE, bold_first=True)
arrow(20, 55, 20, 51); arrow(33, 40.5, 38, 40.5)
box(70, 30, 29.5, 21, "Reports assessed for eligibility\nn = %s (full text %s;\nabstract only %s)\n\nExcluded n = %s" %
    (f("cit_assessed_total"), f("cit_assessed"), f("cit_abs_only"), f("cit_ft_excluded")), fc=C_SIDE, bold_first=True)
arrow(84.75, 55, 84.75, 51)

# included
box(7, 9, 58, 15, "Studies included in the review\nn = %s\n(database search n = %s; citation searching n = %s)\n\nPreprints among included studies n = %s (sensitivity analysis)" %
    (f("included"), f("included_db"), f("included_cit"), f("included_preprints")), bold_first=True, fs=6.9)
arrow(20, 30, 20, 24)
ax.annotate("", xy=(65, 16.5), xytext=(84.75, 30), arrowprops=dict(arrowstyle="-|>", lw=0.7, color=C_EDGE,
            connectionstyle="angle,angleA=-90,angleB=0", mutation_scale=7))
save(fig, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures", "fig_prisma"))
print("ok")
