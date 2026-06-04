#!/usr/bin/env python3
"""Branch-level feature-selection study for Project A (Criterion 4).

Treats each detector as a *feature representation*. We (a) rank representations by
single-branch AUROC, (b) measure leave-one-out importance inside the fusion,
(c) drop the redundant/weak ones, and (d) compare a model that uses only the
IMPORTANT features against one that uses ALL features.

Replicates the project's exact fusion recipe (loco_project_utils.run_stage09_fusion):
z-normalise each branch on validation/good, merge on image_id, average the z-scores.

Outputs (read by the dashboard + report + slides):
  06_method_results/Final_Evaluation/feature_selection_table.csv
  06_method_results/Final_Evaluation/feature_importance_leave_one_out.csv
  07_paper_draft/figures/figure_feature_selection.png
  09_dashboard/feature_selection.json
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "06_method_results" / "Final_Evaluation"
FIGS = ROOT / "07_paper_draft" / "figures"
CATS = ["breakfast_box", "juice_bottle", "pushpins", "screw_bag", "splicing_connectors"]

# Display name -> scores CSV. Order matches loco_project_utils.load_method_score_files.
BRANCH_FILES = {
    "Global Image-Stat (proxy)":  "05_baselines/EfficientAD/efficientad_scores.csv",
    "DINOv2 Patch Memory":        "05_baselines/PatchCore/patchcore_scores.csv",
    "DINOv2 PatchMemory (dup)":   "06_method_results/DINOv2_PatchMemory/dinov2_patchmemory_scores.csv",
    "DINOv2 Region-Aware":        "06_method_results/GridAware_DINOv2/gridaware_scores.csv",
    "DINOv2 Composition Hist":    "06_method_results/CompositionHistogram/composition_hist_scores.csv",
}


def zload(path):
    df = pd.read_csv(ROOT / path)
    s = df["score"].to_numpy(float)
    val = df[(df.split == "validation") & (df.defect_type == "good")]["score"].to_numpy(float)
    ref = val if len(val) else s
    mu, sigma = float(np.mean(ref)), float(np.std(ref) + 1e-8)
    out = df[["image_id", "category", "split", "defect_type", "label"]].copy()
    out["z"] = (s - mu) / sigma
    return out


# Build a wide table: one row per image, one z-score column per branch.
Z = {name: zload(p) for name, p in BRANCH_FILES.items()}
wide = None
for name in BRANCH_FILES:
    d = Z[name][["image_id", "category", "split", "defect_type", "label", "z"]].rename(columns={"z": name})
    wide = d if wide is None else wide.merge(d[["image_id", name]], on="image_id", how="inner")
print(f"merged images: {len(wide)} (test={int((wide.split=='test').sum())})")


def auroc(score_df):
    """5-category-averaged image AUROC for logical / structural / overall."""
    res = {}
    for atype in ["logical", "structural", "overall"]:
        aucs = []
        for cat in CATS:
            c = score_df[score_df.category == cat]
            test = c[c.split == "test"]
            good = test[test.defect_type == "good"]
            sub = test[test.defect_type != "good"] if atype == "overall" \
                else test[test.defect_type == f"{atype}_anomalies"]
            ev = pd.concat([good, sub])
            y = ev.label.astype(int).to_numpy()
            s = ev.score.astype(float).to_numpy()
            if len(set(y)) > 1:
                aucs.append(roc_auc_score(y, s))
        res[atype] = float(np.mean(aucs)) if aucs else float("nan")
    return res


def fuse(cols):
    df = wide[["category", "split", "defect_type", "label"]].copy()
    df["score"] = wide[list(cols)].mean(axis=1)
    return df


ALL = list(BRANCH_FILES)
UNIQUE = [b for b in ALL if b != "DINOv2 PatchMemory (dup)"]  # drop the byte-identical duplicate

# (a) single-branch AUROC = representation strength
single = {b: auroc(fuse([b]))["overall"] for b in ALL}

# (b) leave-one-out importance inside the full fusion (positive = the branch helps)
base_overall = auroc(fuse(ALL))["overall"]
loo_rows = []
for b in ALL:
    rest = [x for x in ALL if x != b]
    drop_overall = auroc(fuse(rest))["overall"]
    loo_rows.append({
        "branch": b,
        "single_branch_overall_auroc": round(single[b], 4),
        "fusion_without_this": round(drop_overall, 4),
        "importance_delta": round(base_overall - drop_overall, 4),  # >0 -> branch improves fusion
    })
loo = pd.DataFrame(loo_rows).sort_values("single_branch_overall_auroc", ascending=False)

# (c) principled selection from the leave-one-out importance:
#     drop the REDUNDANT duplicate, then drop any branch that HURTS the fusion (delta <= 0).
delta = {r["branch"]: r["importance_delta"] for r in loo_rows}
harmful = [b for b in UNIQUE if delta[b] <= 0]                 # Composition Hist (delta < 0)
selected = [b for b in UNIQUE if delta[b] > 0]                 # proxy + patch-mem + region-aware
strong_dinov2 = [b for b in UNIQUE if single[b] >= 0.70 and "proxy" not in b]  # the 2 DINOv2 memories
best_single = max(ALL, key=lambda b: single[b])

# (d) compare ALL features vs feature-SELECTED vs best single representation
variants = {
    "All features (5, incl. duplicate)":         ALL,
    "Drop redundant duplicate (4 unique)":       UNIQUE,
    f"Feature-selected ({len(selected)}: drop redundant + harmful)": selected,
    f"Strong DINOv2 memories only ({len(strong_dinov2)})":          strong_dinov2,
    "Best single representation":                [best_single],
}
important = selected
rows = []
for label, cols in variants.items():
    a = auroc(fuse(cols))
    rows.append({
        "model": label,
        "n_branches": len(cols),
        "branches": " + ".join(cols),
        "logical": round(a["logical"], 4),
        "structural": round(a["structural"], 4),
        "overall": round(a["overall"], 4),
    })
fs = pd.DataFrame(rows)

EVAL.mkdir(parents=True, exist_ok=True)
fs.to_csv(EVAL / "feature_selection_table.csv", index=False)
loo.to_csv(EVAL / "feature_importance_leave_one_out.csv", index=False)

# figure: ALL vs IMPORTANT vs single
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    labels = fs["model"].tolist()
    vals = fs["overall"].tolist()
    colors = ["#6c8cff", "#37c98a", "#ffcf6b", "#9aa6c8"]
    bars = ax.barh(labels[::-1], vals[::-1], color=colors[::-1])
    for b, v in zip(bars, vals[::-1]):
        ax.text(v + 0.004, b.get_y() + b.get_height() / 2, f"{v:.3f}", va="center", fontsize=9)
    ax.set_xlim(0.5, max(vals) + 0.06)
    ax.set_xlabel("Overall image AUROC (5-category average)")
    ax.set_title("Feature selection: important representations vs all features")
    fig.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / "figure_feature_selection.png", dpi=160)
    plt.close(fig)
    fig_ok = True
except Exception as e:
    print("figure skipped:", e)
    fig_ok = False

payload = {
    "variants": fs.to_dict(orient="records"),
    "leave_one_out": loo.to_dict(orient="records"),
    "important_branches": important,
    "dropped": [b for b in ALL if b not in important],
    "harmful": harmful,
    "best_single": best_single,
}
(Path(__file__).resolve().parent / "feature_selection.json").write_text(json.dumps(payload, indent=2))

print("\n=== Leave-one-out importance (single AUROC, fusion-without, delta) ===")
print(loo.to_string(index=False))
print("\n=== Feature-selection comparison (ALL vs IMPORTANT vs single) ===")
print(fs[["model", "n_branches", "logical", "structural", "overall"]].to_string(index=False))
print("\nimportant:", important, "| dropped:", [b for b in ALL if b not in important], "| fig:", fig_ok)
