1. Project title
2. One-line project summary
3. Live dashboard link
4. Short highlights
5. Dashboard screenshot

# LOCO Anomaly Inspector

Unsupervised logical and structural anomaly detection on the **MVTec LOCO AD** benchmark using frozen **DINOv2-small** patch features, memory-based scoring, feature selection, and an interactive dashboard.



Interactive, reproducible anomaly detection system for **logical and structural anomaly detection** on the **MVTec LOCO AD** benchmark.

Live dashboard: https://az-main.github.io/Data-Analytics-Lab-Project/

Repository: https://github.com/Az-main/Data-Analytics-Lab-Project

---

## Highlights

- Detects both **structural anomalies** and harder **logical anomalies**.
- Uses frozen **DINOv2-small** patch features with no task-specific neural-network training.
- Evaluates patch-memory, region-aware memory, composition-histogram, global-stat, and fusion-based anomaly scores.
- Includes leakage-aware preprocessing, EDA, feature selection, per-category evaluation, and explainability visuals.
- Provides a self-contained dashboard for exploring results and model behavior.

---

![Dashboard preview](assets/dashboard_preview.png)

## Problem

Industrial anomaly detection is challenging because models are usually trained only on normal, defect-free images. At test time, the system must detect both visible physical defects and harder logical mistakes.

This project focuses on two anomaly types:

- **Structural anomalies:** visible local defects such as scratches, dents, contamination, deformation, or damaged parts.
- **Logical anomalies:** missing, extra, misplaced, or wrongly arranged components where each individual part may still look visually normal.

## What This Project Does

This project builds a complete anomaly-inspection pipeline:

1. Audits and preprocesses the MVTec LOCO AD dataset.
2. Performs EDA to understand defect size, location, category variation, and visual complexity.
3. Extracts frozen DINOv2-small patch features.
4. Builds multiple anomaly-scoring branches.
5. Combines detector scores through fusion.
6. Performs branch-level feature selection.
7. Evaluates results by category and anomaly type.
8. Presents the results in an interactive dashboard.


## Dataset

This project uses the **MVTec LOCO AD** dataset, which is designed for logical and structural anomaly detection.

The five evaluated categories are:

- `breakfast_box`
- `juice_bottle`
- `pushpins`
- `screw_bag`
- `splicing_connectors`

The raw dataset is not included in this repository. It must be downloaded separately from the official MVTec source.


## Method Overview

The project compares several lightweight anomaly-scoring branches.

| Method | Main Idea |
|---|---|
| Global Image-Stat Proxy | Uses whole-image statistics such as intensity, color, and edge information. |
| DINOv2 Patch Memory | Stores normal patch embeddings and scores test patches by nearest-neighbor distance. |
| DINOv2 Region-Aware Memory | Compares patches with normal patches from corresponding spatial regions. |
| DINOv2 Composition Histogram | Represents images using distributions of DINOv2 visual words. |
| Fusion | Combines normalized detector scores into one anomaly score. |

The strongest results come from fusion and region-aware DINOv2 patch memory.


## Key Results

The dashboard compares individual detectors and fusion configurations using image-level AUROC.

| Finding | Interpretation |
|---|---|
| Fusion is strongest overall | Combining complementary detector scores performs better than relying on one branch. |
| Region-Aware Memory is the strongest individual detector | Spatial constraints improve DINOv2 patch-memory scoring. |
| Patch Memory is useful for local defects | Nearest-neighbor patch scoring captures structural abnormality. |
| Global Image-Stat is weak alone but useful in fusion | Simple global statistics provide complementary information. |
| Composition Histogram underperforms | Global visual-word histograms lose important spatial details. |

## Repository Structure

```text
Data-Analytics-Lab-Project/
|
|-- 00_project_planning/
|   Project planning, roadmap, review notes, and submission guides
|
|-- 01_notebooks/
|   Staged experimental notebooks and reusable project utilities
|
|-- 02_audit_reproducibility/
|   Dataset audits, preprocessing metadata, environment checks, and reproducibility files
|
|-- 04_probe_results/
|   EDA figures, statistical summaries, and component-probe outputs
|
|-- 05_baselines/
|   Baseline detector scores, runtime logs, and anomaly maps
|
|-- 06_method_results/
|   DINOv2 method outputs, fusion results, final evaluation tables, and qualitative analysis
|
|-- 07_paper_draft/
|   Report, presentation, exported figures, and document-generation scripts
|
|-- 09_dashboard/
|   Dashboard source files, result tables, dashboard data, and build scripts
|
|-- docs/
|   GitHub Pages deployment for the live dashboard
|
|-- Run_DINOv2_Colab.ipynb
|   GPU notebook for running the real DINOv2 pipeline
|
|-- requirements.txt
|   Python dependencies
|
`-- README.md


Small note: because this block contains a code fence inside a code fence, when you paste into GitHub, paste it normally into README. It will render correctly.

After this, the next section should be **Important Files**.
