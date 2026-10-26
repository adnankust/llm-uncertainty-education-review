"""Analytical framework of the review: Where -> How -> Then what -> Who, evaluated by Evidence (RQ1-RQ4)."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from style import plt, save
from matplotlib.patches import FancyBboxPatch

cols = [
    ("RQ1  Where", "Educational task", "#2F6F9F",
     ["Scoring and grading", "Feedback on\nstudent work", "Tutoring and\nquestion answering",
      "Error diagnosis and\nknowledge tracing", "Item and content\ngeneration", "Learning analytics\nand coding",
      "Advising and\nadministration", "Students' use of\ngeneral LLMs"]),
    ("RQ2  How", "Uncertainty signal", "#3B8C7A",
     ["Verbalised\nconfidence (VC)", "Token probability,\nentropy (TP)", "Sampling consistency,\nsemantic entropy (SC)",
      "Ensembles, multi-LLM\ndisagreement (EN)", "Conformal\nprediction (CP)", "Calibration, learned\nconfidence (CAL)",
      "Retrieval and\nverification (RV)", "Human or reference\ncomparison (HR)"]),
    ("RQ3  Then what", "Action on uncertainty", "#B3742E",
     ["Show it to\nthe user (DISP)", "Abstain (ABST)", "Defer to a\nhuman (DEFER)",
      "Selective automation\nby threshold (SEL)", "Ask a clarifying\nquestion (ASK)", "Verify or\nregenerate (VER)",
      "Warning or\ndisclaimer (WARN)", "Measured only\n(NONE)"]),
    ("RQ3  Who", "Human in the loop", "#8A4F8F",
     ["Teacher or\ninstructor", "Student", "Expert raters", "Institution", "No human (fully\nautomated)"]),
    ("RQ4  Evidence", "How it is evaluated", "#5B6B7F",
     ["Agreement: kappa,\nQWK, ICC", "Accuracy, F1, MAE", "Calibration:\nECE, Brier", "Discrimination:\nAUROC",
      "Coverage-risk,\nselective accuracy", "Hallucination or\nerror rate", "Trust, reliance,\nworkload",
      "Learning outcomes"]),
]
fig, ax = plt.subplots(figsize=(7.16, 4.3))
ax.set_xlim(-0.5, 100.8); ax.set_ylim(0, 77); ax.axis("off"); ax.grid(False)
W, gap, x0 = 18.2, 2.1, 0.6
for k, (rq, sub, col, items) in enumerate(cols):
    x = x0 + k * (W + gap)
    ax.add_patch(FancyBboxPatch((x, 1.0), W, 68.5, boxstyle="round,pad=0.2,rounding_size=1.2", fc="#FAFBFC",
                                ec=col, lw=0.9))
    ax.add_patch(FancyBboxPatch((x, 63.2), W, 6.3, boxstyle="round,pad=0.2,rounding_size=1.2", fc=col, ec=col))
    ax.text(x + W / 2, 67.6, rq, ha="center", va="center", color="white", fontsize=7.4, fontweight="bold")
    ax.text(x + W / 2, 64.7, sub, ha="center", va="center", color="white", fontsize=6.4, style="italic")
    y = 61.8
    for it in items:
        h = 7.3
        ax.add_patch(FancyBboxPatch((x + 0.9, y - h + 0.5), W - 1.8, h - 0.7, boxstyle="round,pad=0.12,rounding_size=0.6",
                                    fc="white", ec="#C9D1DB", lw=0.5))
        ax.text(x + 1.8, y - h / 2 + 0.15, it, ha="left", va="center", fontsize=6.0, color="#222222", linespacing=1.15)
        y -= h + 0.25
    if k < len(cols) - 1:
        ax.annotate("", xy=(x + W + gap - 0.15, 35), xytext=(x + W + 0.25, 35),
                    arrowprops=dict(arrowstyle="-|>", lw=1.0, color="#7A8899", mutation_scale=9))
ax.text(50, 74.3, "RQ5  Risks and gaps: fairness across learner groups, over- and under-reliance, robustness, openness",
        ha="center", va="center", fontsize=6.6, color="#7A2E2E", fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.35", fc="#FBEFEF", ec="#C98A8A", lw=0.6))
save(fig, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures", "fig_framework"))
print("ok")
