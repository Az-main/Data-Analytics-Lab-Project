# LOCO Anomaly Inspector

Interactive, reproducible anomaly detection system for **logical and structural anomaly detection** on the **MVTec LOCO AD** benchmark.

Live dashboard: https://az-main.github.io/Data-Analytics-Lab-Project/

Repository: https://github.com/Az-main/Data-Analytics-Lab-Project

---

## Updated v2 Results

| Result | Value |
|---|---:|
| Best observed v2 method | Fusion Max |
| Best observed overall AUROC | 82.7% |
| Pre-specified main fusion | Best Fusion / mean fusion |
| Pre-specified fusion overall AUROC | 81.1% |
| Logical AUROC | 76.9% |
| Structural AUROC | 90.3% |
| Backbone | Frozen DINOv2-small-v2crop336 |
| Training required | None |
| Compute | Free-tier Colab T4 |
| Evaluation | 3 seeds, mean ± std reported |

---

## Main Contribution

We audited our original v1 anomaly detection pipeline, found four design flaws, fixed them in v2, and improved the system from **76.1% overall AUROC** to **82.7% overall AUROC** while keeping the method lightweight, explainable, and reproducible.

The project does not claim to beat state-of-the-art methods such as SALAD or CSAD. Instead, the contribution is an honest engineering improvement story:

> v1 pipeline → flaw audit → v2 fixes → measurable improvement → interactive explainability dashboard.

---

## Problem

Industrial anomaly detection is difficult because models are usually trained only on defect-free images. At test time, the system must detect both:

- **Structural anomalies:** scratches, dents, contamination, cracks, deformations.
- **Logical anomalies:** missing, extra, swapped, or misplaced components, where every local region may still look visually normal.

This project uses the **MVTec LOCO AD** dataset, which contains five industrial object categories:

- `breakfast_box`
- `juice_bottle`
- `pushpins`
- `screw_bag`
- `splicing_connectors`

---

## v1 → v2: The Four Flaws We Fixed

| # | v1 problem | v2 fix |
|---|---|---|
| 1 | Letterbox padding was fed into DINOv2, so many patch tokens represented blank padding instead of product content. | Crop the content box before feature extraction using saved resize metadata. |
| 2 | One global memory bank, vocabulary, histogram statistics, and fusion normalization were shared across all categories. | Fit memory banks, vocabularies, histogram statistics, and fusion normalization per category. |
| 3 | Features were re-extracted multiple times and nearest-neighbour search ran on CPU. | Use single-pass feature caching and GPU nearest-neighbour search. |
| 4 | PatchCore and DINOv2 PatchMemory were effectively duplicate branches. | Differentiate them: PatchCore-style uses k=1/top-1%; PatchMemory uses k=3/top-5%. |

These changes improved both score and stability. Structural anomaly detection became especially strong, reaching **90.3% AUROC**.

---

## Method Overview

The system uses a frozen **DINOv2-small Vision Transformer** as a feature extractor. No task-specific neural network training is performed. The model only uses normal training images to build reference statistics and memory banks.

Pipeline:

1. Load MVTec LOCO AD images.
2. Apply deterministic preprocessing.
3. Crop content region to remove letterbox padding.
4. Extract frozen DINOv2 patch tokens.
5. Score anomalies using multiple lightweight branches.
6. Normalize scores using validation/good only.
7. Fuse scores and produce image-level AUROC and anomaly heatmaps.

---

## Detection Branches

| Branch | Purpose |
|---|---|
| PatchCore-style | k=1 nearest-neighbour distance with top-1% aggregation; strong for structural anomalies. |
| DINOv2 PatchMemory | k=3 mean neighbour distance with top-5% aggregation; broader patch-level coverage. |
| GridAware DINOv2 | Region-aware patch comparison; preserves spatial layout sensitivity. |
| Composition Histogram | Bag-of-visual-words composition statistics; helps logical anomaly detection. |
| EfficientAD-inspired proxy | Lightweight global image-stat baseline; included as a non-DINOv2 reference branch. |
| Fusion Max | Best observed v2 fusion result. |
| Best Fusion / Mean Fusion | Pre-specified main fusion result. |

---

## Dashboard

The interactive dashboard is the main presentation artifact.

Live dashboard:

https://az-main.github.io/Data-Analytics-Lab-Project/

Local dashboard file:

```text
09_dashboard/dashboard.html
```

GitHub Pages dashboard file:

```text
docs/index.html
```

The dashboard includes:

- Hero KPI summary
- Full pipeline explanation
- Four v1 flaws and v2 fixes
- v1 vs v2 comparison
- Results leaderboard
- Per-category analysis
- Feature selection analysis
- EDA figures
- Anomaly heatmaps
- Honest comparison with published methods
- Limitations and future work

---

## Repository Structure

```text
.
├── 00_project_planning/
│   └── Planning notes, roadmap, peer review, context, and submission guide
│
├── 01_notebooks/
│   ├── loco_project_utils.py
│   └── loco_v2_improvements.py
│
├── 02_audit_reproducibility/
│   └── Resize metadata, leakage audit, hashes, preprocessing records
│
├── 04_probe_results/
│   └── EDA figures, probe results, and analysis outputs
│
├── 05_baselines/
│   └── Baseline scores, maps, and configs
│
├── 06_method_results/
│   ├── CompositionHistogram/
│   ├── DINOv2_PatchMemory/
│   ├── Fusion/
│   ├── GridAware_DINOv2/
│   ├── Qualitative/
│   └── Final_Evaluation/
│       ├── main_results_table.csv
│       ├── per_category_results_table.csv
│       ├── multiseed_summary.csv
│       └── v2_run_config.json
│
├── 07_paper_draft/
│   └── Report, slides, figures, and document builders
│
├── 09_dashboard/
│   ├── dashboard.html
│   ├── build_competition_dashboard.py
│   └── LOCO_Anomaly_Inspector_PowerBI/
│
├── docs/
│   └── index.html
│
├── Run_DINOv2_Colab.ipynb
├── requirements.txt
└── README.md
```

---

## Reproducibility

The v2 pipeline records key provenance in:

```text
06_method_results/Final_Evaluation/v2_run_config.json
```

The multi-seed summary is stored in:

```text
06_method_results/Final_Evaluation/multiseed_summary.csv
```

Important reproducibility choices:

- Frozen DINOv2-small backbone
- Content crop before feature extraction
- Per-category memory banks and vocabularies
- Per-category fusion normalization
- GPU nearest-neighbour search
- Three seeds: 42, 7, 2026
- Validation/good-only normalization and thresholding
- No test-label tuning

---

## How to Run the Colab Pipeline

Open:

```text
Run_DINOv2_Colab.ipynb
```

In Google Colab:

1. Set runtime to **T4 GPU**.
2. Mount Google Drive.
3. Make sure the `Phase 1` dataset folder is visible to Colab.
4. Run the smoke test first.
5. If the smoke test passes, run the full v2 pipeline.
6. The notebook exports result files into `05_baselines/` and `06_method_results/`.

The raw dataset is not stored in this repository.

---

## How to Regenerate the Dashboard

From the repo root:

```bash
cd 09_dashboard
python build_competition_dashboard.py
```

This regenerates:

```text
09_dashboard/dashboard.html
```

For GitHub Pages, copy the dashboard to:

```text
docs/index.html
```

---

## Dataset

This project uses **MVTec LOCO AD**.

The raw images are external and read-only. They are not committed to GitHub.

The repository contains:

- Code
- Results
- Evaluation tables
- Visualizations
- Dashboard
- Report and slide materials

The repository does not contain:

- Raw dataset images
- Feature cache
- Large result zip files

---

## Honest Limitations

- Logical anomalies remain harder than structural anomalies.
- Pushpins logical anomalies are especially challenging because patch-level nearest-neighbour scoring does not directly count object components.
- The method is lightweight and training-free, but methods above 90% overall AUROC usually use task-specific training, component segmentation, or stronger supervision.
- Fusion Max is reported as the best observed v2 method; the safer pre-specified main fusion result is Best Fusion / mean fusion.

---

## Method References

This project is inspired by:

- MVTec LOCO AD dataset
- DINOv2 self-supervised visual features
- PatchCore-style memory-bank anomaly detection
- EfficientAD-style lightweight anomaly detection
- Component-aware logical anomaly detection research such as CSAD and SALAD

---

## Notes

Start with the live dashboard for the clearest overview of the project. The main reproducibility files are `Run_DINOv2_Colab.ipynb`, `v2_run_config.json`, and `multiseed_summary.csv`.