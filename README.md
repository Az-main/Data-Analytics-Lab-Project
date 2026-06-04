# LOCO Anomaly Inspector — Logical & Structural Anomaly Detection on MVTec LOCO AD

An interactive, reproducible system for **unsupervised industrial anomaly detection** on the
[MVTec LOCO AD](https://www.mvtec.com/company/research/datasets/mvtec-loco) benchmark. Models are
trained on defect-free images only and must flag both **structural** anomalies (scratches, dents) and
**logical** anomalies (missing / extra / misplaced parts, where every local region still looks normal).

> **Data Analytics Lab — Project A.** Built around real, frozen **DINOv2-small** patch features, with a
> leakage-audited pipeline, four complementary detectors + fusion, feature-selection analysis, and an
> offline explainability dashboard.

---

## 🎯 Objective

Detect and **explain** anomalies in industrial product images using only normal images for training —
delivered as a self-contained dashboard backed by a fully reproducible ML pipeline, with an honest
assessment of strengths, limits, and the gap to published state of the art.

## 🔑 Key findings

- **Real DINOv2 verified** end-to-end (`feature_backend = dinov2-small`).
- **Best pre-specified fusion: 0.761 overall image AUROC** (0.731 logical / 0.804 structural).
- **Feature selection improves the model:** dropping a redundant duplicate branch (PatchCore ≡ DINOv2
  PatchMemory) and the harmful Composition-Histogram branch yields a leaner **3-representation model at
  0.764 / 0.826 structural** — beating the full fusion with fewer features.
- **Per-category:** `juice_bottle` ≈ 0.94 AUROC; `pushpins` logical anomalies stay near chance
  (patch-nearest-neighbour scoring cannot *count* parts).
- **Honest scope:** single-seed; letterbox padding not yet masked. Next steps (padding mask, DINOv2-base,
  multi-seed) target ~0.83–0.90; component-segmentation SOTA (CSAD/SALAD) reaches 0.95+.

## 🗂️ Repository structure

```
.
├── 00_project_planning/    Roadmap, peer review, submission guide, context & brief
├── 01_notebooks/           12 stage notebooks (01–12) + loco_project_utils.py (the engine)
├── 02_audit_reproducibility/  Leakage audit, hashes, env freeze, preprocessing config
├── 04_probe_results/        EDA figures/tables + DINOv2 component-relevance probe
├── 05_baselines/            EfficientAD (proxy) + PatchCore — scores, maps, configs
├── 06_method_results/       DINOv2 detectors, Fusion, Final_Evaluation (incl. feature selection)
├── 07_paper_draft/          Report (.docx), slides (.pptx), figures + builders
├── 09_dashboard/            dashboard.html + build scripts (build_dashboard / generate_html / feature_selection)
├── Run_DINOv2_Colab.ipynb   GPU notebook that produces the real DINOv2 results
├── requirements.txt
└── README.md
```
*(Folder numbering 03 and 08 are intentionally unused — raw/cleaned image data is external and read-only.)*

## 🚀 How to run

**View the dashboard (no install):** double-click `09_dashboard/dashboard.html` — opens offline in any browser.

**Set up the environment:**
```bash
pip install -r requirements.txt
```

**Regenerate all deliverables** (run in this order — dependencies matter):
```bash
cd 09_dashboard
python feature_selection.py     # Criterion-4 feature-selection study
python build_dashboard.py       # corrected metrics + dashboard_data.json
python generate_html.py         # dashboard.html
cd ../07_paper_draft
python build_product_report.py  # Project_A_LOCO_Report_Product.docx
python build_slides.py          # Project_A_LOCO_Presentation.pptx
```

**Produce real DINOv2 results (GPU):** open `Run_DINOv2_Colab.ipynb` in Google Colab (T4 GPU), Run all.
It exports `loco_dinov2_results.zip`; unzip into `05_baselines/` + `06_method_results/` and rerun the
regenerate chain above.

## 📦 Dataset

**MVTec LOCO AD** — 5 categories (`breakfast_box`, `juice_bottle`, `pushpins`, `screw_bag`,
`splicing_connectors`). Each provides defect-free **train** and **validation** images plus a **test**
set mixing good / logical / structural images with pixel ground-truth masks. We fit on `train/good`
only, set the decision threshold on `validation/good`, and hold out `test`. **Raw images are external
and treated as read-only** — this repository contains the pipeline, results, and deliverables, not the
raw dataset.

## 🧪 Methods (4 detectors + fusion)

| Detector | Idea |
|---|---|
| DINOv2 Patch Memory (NN) | PatchCore-style memory of normal DINOv2 tokens; cosine NN distance |
| DINOv2 Region-Aware Memory | Memory conditioned on image region — positional awareness (strongest single) |
| DINOv2 Composition Histogram | Visual-word histogram scored by Mahalanobis distance (logical-leaning) |
| Global Image-Stat (proxy) | Single global descriptor vs. normal mean (fast baseline, non-DINOv2) |
| **Fusion** | z-normalise each on `validation/good`, then mean / max / rank-average |

## 📈 Reproducibility

Fixed seeds; deterministic letterbox preprocessing with saved resize metadata; MD5 + perceptual-hash
leakage audit across splits (none found); per-method JSON configs; environment freeze. See
`02_audit_reproducibility/` and `00_project_planning/CONTEXT.md`.

---
*Project history and the full development context live in `00_project_planning/` (`CONTEXT.md`,
`ROADMAP_*.md`, `PEER_REVIEW_*.md`, `SUBMISSION_GUIDE.md`). The previous README is preserved as
`README_old.md`.*
