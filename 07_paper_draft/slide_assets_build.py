# Generate dark-themed charts + cropped example tiles for the new presentation.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
import os

BG = "#0E1624"
CARD = "#18233A"
TXT = "#F2F5FA"
MUT = "#9FB0C9"
AMBER = "#F5A623"
BLUE = "#7FB3E8"
GREEN = "#3DCB8F"
RED = "#E0566B"
GRID = "#2A3A5C"

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
    "text.color": TXT, "axes.edgecolor": GRID, "axes.labelcolor": MUT,
    "xtick.color": MUT, "ytick.color": MUT, "font.family": "DejaVu Sans",
    "axes.grid": False,
})

OUT = "slide_assets"
os.makedirs(OUT, exist_ok=True)
FE = "../06_method_results/Final_Evaluation"

# ---------- A. Main results grouped bars ----------
df = pd.read_csv(f"{FE}/main_results_table.csv")
keep = ["Best Fusion", "GridAware DINOv2", "DINOv2 PatchMemory", "EfficientAD", "CompositionHistogram"]
labels = {"Best Fusion": "Fusion (mean)", "GridAware DINOv2": "Region-Aware\nMemory",
          "DINOv2 PatchMemory": "Patch\nMemory", "EfficientAD": "Global Image-Stat\n(proxy)",
          "CompositionHistogram": "Composition\nHistogram"}
d = df[df.method.isin(keep)].set_index("method").loc[keep]
x = np.arange(len(keep)); w = 0.26
fig, ax = plt.subplots(figsize=(8.6, 4.2), dpi=200)
b1 = ax.bar(x - w, d["logical"], w, label="Logical", color=BLUE)
b2 = ax.bar(x, d["structural"], w, label="Structural", color=GREEN)
b3 = ax.bar(x + w, d["overall"], w, label="Overall", color=AMBER)
for bars in (b1, b2, b3):
    for r in bars:
        ax.text(r.get_x() + r.get_width()/2, r.get_height() + 0.012, f"{r.get_height():.3f}",
                ha="center", va="bottom", fontsize=7.2, color=TXT)
ax.set_xticks(x); ax.set_xticklabels([labels[k] for k in keep], fontsize=9)
ax.set_ylim(0.4, 0.9); ax.set_ylabel("Image-level AUROC (5-category mean)", fontsize=9)
ax.axhline(0.5, color=MUT, lw=0.8, ls="--", alpha=0.6)
ax.text(-0.58, 0.507, "chance", fontsize=7.5, color=MUT, ha="left")
ax.legend(frameon=False, fontsize=9, loc="upper right", ncols=3, bbox_to_anchor=(1.0, 1.08))
for s in ("top", "right"): ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig(f"{OUT}/chart_main_results.png", bbox_inches="tight"); plt.close()

# ---------- B. Per-category heatmap (Best Fusion) ----------
pc = pd.read_csv(f"{FE}/per_category_results_table.csv")
fus = pc[pc.method == "Best Fusion"].pivot(index="category", columns="anomaly_type", values="auroc")
fus = fus[["logical", "structural", "overall"]]
cats = ["breakfast_box", "juice_bottle", "pushpins", "screw_bag", "splicing_connectors"]
fus = fus.loc[cats]
fig, ax = plt.subplots(figsize=(6.6, 3.6), dpi=200)
vals = fus.values
im = ax.imshow(vals, cmap="RdYlGn", vmin=0.45, vmax=1.0, aspect="auto")
ax.set_xticks(range(3)); ax.set_xticklabels(["Logical", "Structural", "Overall"], fontsize=10)
ax.set_yticks(range(5))
ax.set_yticklabels([c.replace("_", " ") for c in cats], fontsize=10)
for i in range(vals.shape[0]):
    for j in range(vals.shape[1]):
        ax.text(j, i, f"{vals[i, j]:.3f}", ha="center", va="center", fontsize=10,
                color="#10151D", fontweight="bold")
ax.set_title("Best Fusion — AUROC by category", fontsize=11, color=TXT, pad=10)
for s in ax.spines.values(): s.set_visible(False)
plt.tight_layout(); plt.savefig(f"{OUT}/chart_percat_heatmap.png", bbox_inches="tight"); plt.close()

# ---------- C. Leave-one-out importance ----------
loo = pd.read_csv(f"{FE}/feature_importance_leave_one_out.csv")
loo = loo[loo.branch != "DINOv2 PatchMemory (dup)"].copy()
loo = loo.sort_values("importance_delta")
fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=200)
colors = [RED if v < 0 else GREEN for v in loo.importance_delta]
bars = ax.barh(loo.branch, loo.importance_delta, color=colors, height=0.55)
for r, v in zip(bars, loo.importance_delta):
    off = 0.0008 if v >= 0 else -0.0008
    ax.text(v + off, r.get_y() + r.get_height()/2, f"{v:+.4f}", va="center",
            ha="left" if v >= 0 else "right", fontsize=9, color=TXT)
ax.axvline(0, color=MUT, lw=0.8)
ax.set_xlabel("Δ overall AUROC when branch removed from fusion (higher = more important)", fontsize=8.5)
ax.set_xlim(-0.022, 0.058)
ax.tick_params(axis="y", labelsize=9.5)
for s in ("top", "right"): ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig(f"{OUT}/chart_loo_importance.png", bbox_inches="tight"); plt.close()

# ---------- D. Feature selection ----------
fs = pd.read_csv(f"{FE}/feature_selection_table.csv")
order = list(fs.model)[::-1]
fsr = fs.set_index("model").loc[order]
short = {"All features (5, incl. duplicate)": "All 5 branches (incl. duplicate)",
         "Drop redundant duplicate (4 unique)": "4 unique branches",
         "Feature-selected (3: drop redundant + harmful)": "3 selected branches",
         "Strong DINOv2 memories only (2)": "2 strong memories only",
         "Best single representation": "Best single branch"}
fig, ax = plt.subplots(figsize=(7.2, 3.4), dpi=200)
cols = [AMBER if "3:" in m else "#5577AA" for m in order]
bars = ax.barh([short[m] for m in order], fsr.overall, color=cols, height=0.55)
for r, v in zip(bars, fsr.overall):
    ax.text(v + 0.003, r.get_y() + r.get_height()/2, f"{v:.4f}", va="center", fontsize=9.5, color=TXT)
ax.set_xlim(0.5, 0.82); ax.set_xlabel("Overall image AUROC (5-category mean)", fontsize=9)
ax.tick_params(axis="y", labelsize=9.5)
for s in ("top", "right"): ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig(f"{OUT}/chart_feature_selection.png", bbox_inches="tight"); plt.close()

# ---------- E. Fusion rules ----------
rules = ["Mean", "Weighted avg", "Rank average", "Max"]
vals = [0.7609, 0.7609, 0.7201, 0.7137]
fig, ax = plt.subplots(figsize=(5.2, 3.0), dpi=200)
cols = [AMBER, "#5577AA", "#5577AA", "#5577AA"]
bars = ax.bar(rules, vals, color=cols, width=0.55)
for r, v in zip(bars, vals):
    ax.text(r.get_x() + r.get_width()/2, v + 0.004, f"{v:.3f}", ha="center", fontsize=9.5, color=TXT)
ax.set_ylim(0.6, 0.8); ax.set_ylabel("Overall AUROC", fontsize=9)
ax.tick_params(axis="x", labelsize=9.5)
for s in ("top", "right"): ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig(f"{OUT}/chart_fusion_rules.png", bbox_inches="tight"); plt.close()

# ---------- F. Speed vs accuracy ----------
pts = [("Region-Aware Memory", 154, 0.750, AMBER),
       ("Patch Memory", 367, 0.724, BLUE),
       ("Composition Histogram", 28, 0.576, "#5577AA"),
       ("Global Image-Stat (proxy)", 21, 0.655, GREEN)]
fig, ax = plt.subplots(figsize=(6.6, 3.6), dpi=200)
for name, ms, auc, c in pts:
    ax.scatter(ms, auc, s=150, color=c, zorder=3, edgecolors=TXT, linewidths=0.8)
offsets = {"Region-Aware Memory": (10, 0.008), "Patch Memory": (-10, 0.010),
           "Composition Histogram": (8, 0.008), "Global Image-Stat (proxy)": (8, -0.022)}
for name, ms, auc, c in pts:
    dx, dy = offsets[name]
    ax.text(ms + dx, auc + dy, name, fontsize=9, color=TXT,
            ha="right" if dx < 0 else "left")
ax.set_xlabel("Inference time (ms / image, CPU)", fontsize=9)
ax.set_ylabel("Overall AUROC", fontsize=9)
ax.set_xlim(0, 430); ax.set_ylim(0.54, 0.80)
ax.grid(True, color=GRID, lw=0.5, alpha=0.5)
for s in ("top", "right"): ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig(f"{OUT}/chart_speed_accuracy.png", bbox_inches="tight"); plt.close()

# ---------- G. Crop tiles from eda_mask_overlay_cleaned.png ----------
src = Image.open("../04_probe_results/eda_mask_overlay_cleaned.png")
W, H = src.size
print("mask overlay size:", W, H)
# 4 rows x 5 cols grid, matplotlib layout; estimate tile boxes proportionally
# Tiles from displayed 600x479: row tops ~ [18,138,258,378]/479, col lefts ~ [14,132,250,368,486]/600, tile ~97x97/600
def crop(rc, cc, name):
    r0 = [0.038, 0.288, 0.538, 0.788][rc]
    c0 = [0.023, 0.220, 0.417, 0.613, 0.810][cc]
    th, tw = 0.205, 0.165
    box = (int(c0*W), int(r0*H), int((c0+tw)*W), int((r0+th)*H))
    src.crop(box).save(f"{OUT}/{name}")
    print(name, box)

crop(1, 3, "ex_pushpins_logical.png")      # pushpins logical_anomalies/000
crop(0, 2, "ex_breakfast_structural.png")  # breakfast_box structural
crop(0, 0, "ex_breakfast_logical.png")     # breakfast_box logical
crop(2, 2, "ex_screwbag_logical.png")      # screw_bag logical
crop(3, 1, "ex_splicing_logical.png")      # splicing logical
crop(1, 1, "ex_juice_structural.png")      # juice structural

print("done")
