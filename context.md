# Project Context and Continuation Manual

> **UPDATE 2026-06-11:** the project was selected for the department
> competition (Sunday 2026-06-14). Read **`context_competition.md`** first —
> it covers the competition sprint, the new v2 pipeline
> (`01_notebooks/loco_v2_improvements.py`), and the current next steps.
> Where the two files disagree, `context_competition.md` is newer and wins.

## 1. Purpose of This File

This file is the authoritative handoff document for the **LOCO Anomaly Inspector** project. It consolidates the project objective, repository structure, dataset protocol, notebooks, methods, results, dashboard, reports, presentation material, previous explanations, limitations, and recommended next actions.

Use this file when continuing the project from another computer or in a new assistant session. The assistant should read this file first, then inspect the actual repository files before making changes.

The repository is available at:

`https://github.com/Az-main/Data-Analytics-Lab-Project`

## 2. Current Project Identity

**Project title:** LOCO Anomaly Inspector: Logical and Structural Anomaly Detection on MVTec LOCO AD

**Core task:** Train anomaly detectors using normal industrial images only, then identify abnormal test images and, where supported, localize suspicious regions.

The project distinguishes two anomaly families:

- **Structural anomalies:** visible local defects such as damage, deformation, contamination, or an incorrect physical structure.
- **Logical anomalies:** semantically incorrect arrangements such as missing, extra, misplaced, or incorrectly counted components, even when every individual component looks locally normal.

The project uses the five MVTec LOCO AD categories:

1. `breakfast_box`
2. `juice_bottle`
3. `pushpins`
4. `screw_bag`
5. `splicing_connectors`

The current reported DINOv2 branches use **real frozen DINOv2-small patch features**. An older development stage used lightweight handcrafted fallback features when the DINOv2 runtime was unavailable. That historical fallback must not be confused with the current corrected DINOv2 results.

## 3. Research Motivation

Traditional visual anomaly detection often performs well when a defect changes local texture. Logical anomalies are harder because a component may look visually normal while appearing in the wrong position or quantity.

The project therefore studies several complementary representations:

- Local patch appearance using nearest-neighbor patch memory.
- Spatially constrained patch comparison using region-aware memory.
- Global composition using a bag-of-visual-words histogram.
- Global image statistics using a lightweight proxy detector.
- Score-level fusion to combine complementary anomaly evidence.

The main research question is:

> Can frozen self-supervised DINOv2 patch representations support a lightweight and explainable anomaly-detection system that handles both structural and logical anomalies without training a large task-specific neural network?

## 4. Academic Criteria Mapping

Ignoring the original dataset-size criterion, the project addresses the remaining course requirements as follows.

| Requirement | Project evidence |
|---|---|
| Cleaning and preprocessing | Dataset audit, corruption checks, duplicate/hash checks, deterministic 384x384 letterbox preprocessing, mask verification, and saved configuration files. |
| Exploratory data analysis | Sample grids, mask overlays, mean and variance images, anomaly-frequency maps, mask-area distributions, edge-density analysis, intensity histograms, and category counts. |
| Feature selection | Leave-one-feature-out importance, comparison of all branches against selected branches, duplicate removal, and a reduced three-branch configuration. |
| Summarized insights | Final evaluation tables, dashboard insights, report discussion, failure analysis, and category-level conclusions. |
| Multiple ML/DL methods | Global image-stat proxy, DINOv2 patch memory, DINOv2 region-aware memory, DINOv2 composition histogram, and three fusion rules. |
| Interactive dashboard | A self-contained offline HTML dashboard combining results, EDA, feature selection, category analysis, and explainability assets. |
| Final submission | Twelve notebooks, report files, presentation slides, figures, reproducibility artifacts, and dashboard files. |

The strongest defense is to describe the system as a **multi-configuration anomaly-detection benchmark** rather than claiming that every named notebook is a complete reproduction of an official research implementation.

## 5. Repository Structure

```text
Data-Analytics-Lab-Project/
|
|-- 00_project_planning/
|   |-- CONTEXT.md
|   |-- ROADMAP_Project_A_LOCO_AD.md
|   |-- PEER_REVIEW_Project_A_LOCO_AD.md
|   |-- SUBMISSION_GUIDE.md
|   |-- DEMO_SCRIPT_Friday.md
|   |-- GITHUB_SETUP.md
|   `-- Project_A_LOCO_AD_Full_Implementation_Brief.docx
|
|-- 01_notebooks/
|   |-- 01_preprocessing_reproducibility.ipynb
|   |-- 02_eda_cleaned_letterbox.ipynb
|   |-- 03_dinov2_component_probe_archive.ipynb
|   |-- 04_baseline_efficientad.ipynb
|   |-- 05_baseline_patchcore.ipynb
|   |-- 06_dinov2_patch_memory_baseline.ipynb
|   |-- 07_grid_aware_patch_composition.ipynb
|   |-- 08_composition_histogram_method.ipynb
|   |-- 09_fusion_experiments.ipynb
|   |-- 10_full_evaluation_tables.ipynb
|   |-- 11_qualitative_failure_analysis.ipynb
|   |-- 12_paper_figures_export.ipynb
|   `-- loco_project_utils.py
|
|-- 02_audit_reproducibility/
|   |-- dataset_audit_full.csv
|   |-- dataset_masks_only.csv
|   |-- dataset_product_images_only.csv
|   |-- duplicate_leakage_candidates.csv
|   |-- environment_versions.csv
|   |-- image_hashes.csv
|   |-- mask_count_summary.csv
|   |-- product_image_count_summary.csv
|   |-- resize_letterbox_metadata.csv
|   |-- cleaned_letterbox_verify.csv
|   |-- config_preprocessing.json
|   |-- preprocessing_protocol.txt
|   `-- requirements_freeze.txt
|
|-- 04_probe_results/
|   |-- EDA figures and tables
|   `-- DINOv2 component-probe outputs
|
|-- 05_baselines/
|   `-- baseline scores, tables, runtime logs, and maps
|
|-- 06_method_results/
|   |-- DINOv2 method outputs
|   |-- fusion results
|   |-- final evaluation tables
|   `-- qualitative failure-analysis outputs
|
|-- 07_paper_draft/
|   |-- Project_A_LOCO_Presentation.pptx
|   |-- Project_A_LOCO_Report.docx
|   |-- Project_A_LOCO_Report.pdf
|   |-- Project_A_LOCO_Report_Product.docx
|   |-- build_product_report.py
|   |-- build_slides.py
|   `-- figures and exported assets
|
|-- 09_dashboard/
|   |-- dashboard.html
|   |-- dashboard_data.json
|   |-- corrected_main_results.csv
|   |-- corrected_per_category.csv
|   |-- feature_selection.json
|   |-- feature_selection.py
|   |-- build_dashboard.py
|   `-- generate_html.py
|
|-- Run_DINOv2_Colab.ipynb
|-- README.md
|-- README_old.md
|-- requirements.txt
`-- context.md
```

The absent `03` and `08` tracked folders are intentional. Raw and cleaned image datasets are stored externally because image collections are large and should not be duplicated unnecessarily in Git.

The older `00_project_planning/CONTEXT.md` records an earlier development stage and may contain outdated fallback-feature statements. This root `context.md`, together with the current `README.md`, corrected result files, and runtime logs, should be treated as the current source of truth.

## 6. Dataset and Split Protocol

### 6.1 Dataset Counts

The preprocessing audit recorded:

- Product images: **3,651**
- Ground-truth mask files: **1,246**
- Total PNG files including masks: **4,897**
- Corrupted images: **0**
- Cleaned images with incorrect dimensions: **0**
- Non-binary cleaned masks: **0**

### 6.2 Category Counts

| Category | Train good | Validation good | Test good | Logical | Structural |
|---|---:|---:|---:|---:|---:|
| breakfast_box | 351 | 62 | 102 | 83 | 90 |
| juice_bottle | 335 | 54 | 94 | 142 | 94 |
| pushpins | 372 | 69 | 138 | 91 | 81 |
| screw_bag | 360 | 60 | 122 | 137 | 82 |
| splicing_connectors | 360 | 60 | 119 | 108 | 85 |

### 6.3 Leakage-Safe Usage

- `train/good` is used to fit the normal reference models.
- `validation/good` is used for score normalization, threshold estimation, and hyperparameter choices.
- `test` is reserved for final evaluation.
- Ground-truth anomaly masks are not used to fit the normal feature models.
- Test anomaly labels must not be used to select the winning model or tune its threshold.

This split policy is important because anomaly detection can appear artificially strong if test anomalies influence model selection.

## 7. Preprocessing Protocol

### 7.1 Determinism

The fixed random seed is:

```text
42
```

The seed controls repeatable sampling, clustering initialization where applicable, and other stochastic operations.

### 7.2 Image Size

All cleaned images use a **384x384-pixel canvas**.

`384x384` means:

- Width: 384 pixels
- Height: 384 pixels

This creates a consistent tensor size for batch processing and feature extraction.

### 7.3 Letterbox Resize

Letterboxing resizes the original image while preserving its aspect ratio. Any unused area in the 384x384 canvas is filled with padding.

If an original image has width \(W\) and height \(H\), the scale factor is:

```text
s = min(384 / W, 384 / H)
```

The resized dimensions are:

```text
W' = round(W * s)
H' = round(H * s)
```

The resized image is centered in the 384x384 canvas. This avoids geometric distortion that would occur if width and height were stretched independently.

### 7.4 Interpolation

- Product images use **bilinear interpolation** for smoother visual resizing.
- Masks use **nearest-neighbor interpolation** to preserve discrete class boundaries.
- Every nonzero mask pixel is converted to `255`, keeping masks binary.

### 7.5 Known Padding Limitation

Letterbox padding is currently not fully masked out during feature modeling. A model may therefore learn or score padded regions. This is a documented limitation and a strong future improvement is to propagate a valid-content mask into patch extraction and anomaly-map evaluation.

## 8. End-to-End System Architecture

```text
Raw MVTec LOCO AD images and masks
                 |
                 v
Dataset audit and reproducibility checks
  - file inventory
  - corruption checks
  - image hashes
  - duplicate/leakage candidates
  - split verification
                 |
                 v
384x384 aspect-ratio-preserving letterbox cleaning
  - bilinear product resize
  - nearest-neighbor mask resize
  - binary mask verification
                 |
                 v
Exploratory data analysis
  - category and split counts
  - samples and mask overlays
  - normal mean and variance
  - anomaly location frequency
  - mask area, edges, and intensity
                 |
                 v
Frozen DINOv2-small feature extraction
  - image divided into ViT patches
  - each patch converted to an embedding token
                 |
                 +-----------------------------+
                 |                             |
                 v                             v
Local patch memory                     Global image-stat proxy
                 |
                 +-----------------------------+
                 |                             |
                 v                             v
Region-aware patch memory             Composition histogram
                 |
                 v
Per-method continuous anomaly scores
  - image-level scores
  - patch or spatial maps where available
                 |
                 v
Validation-only score normalization and thresholding
                 |
                 v
Fusion
  - mean
  - maximum
  - rank average
                 |
                 v
Evaluation
  - overall AUROC
  - logical AUROC
  - structural AUROC
  - F1, precision, recall
  - per-category analysis
  - runtime and memory considerations
                 |
                 v
Feature selection and explainability
  - leave-one-branch-out importance
  - reduced branch combinations
  - qualitative success/failure cases
                 |
                 v
Offline HTML dashboard, report, figures, and presentation
```

## 9. Notebook-by-Notebook Breakdown

### 9.1 `01_preprocessing_reproducibility.ipynb`

**Objective:** Establish a deterministic, leakage-aware, and auditable dataset pipeline.

**Main call:**

```python
run_stage01_preprocessing(lab_root=LAB_ROOT, target_size=384)
```

**Major operations:**

- Locate raw dataset folders.
- Inventory images and masks.
- Validate file readability.
- Compute hashes and inspect possible duplicates.
- Resize images and masks using the letterbox protocol.
- Verify output dimensions and binary masks.
- Save metadata, environment versions, and preprocessing configuration.

**Outputs:** CSV audits, preprocessing metadata, verification tables, configuration JSON, protocol text, and dependency freeze.

### 9.2 `02_eda_cleaned_letterbox.ipynb`

**Objective:** Describe the cleaned dataset and identify visual properties relevant to anomaly modeling.

**Main call:**

```python
run_stage02_eda(...)
```

**Outputs include:**

- Cleaned sample grids.
- Ground-truth mask overlays.
- Normal mean and variance images.
- Spatial anomaly-frequency heatmaps.
- Mask-area distributions.
- Edge-density comparisons.
- Intensity histograms.
- Category and split summaries.

Test anomalies are used here only for descriptive EDA, not model tuning.

### 9.3 `03_dinov2_component_probe_archive.ipynb`

**Objective:** Test whether DINOv2 patch features can be converted into stable object components for explicit counting or graph-based reasoning.

**Main call:**

```python
run_stage03_component_probe(..., backend=FEATURE_BACKEND)
```

The probe applies tools such as PCA, K-means clustering, foreground grouping, and connected-component analysis.

**Conclusion:** DINOv2 features are semantically useful, but the clusters did not consistently correspond to stable physical component instances. Component counts were therefore not reliable enough to become the main method.

This negative result is scientifically useful: it explains why the final system uses patch-composition scoring rather than claiming explicit component counting.

### 9.4 `04_baseline_efficientad.ipynb`

**Objective:** Produce a lightweight global anomaly baseline inspired by teacher-student or image-level discrepancy ideas.

**Defense wording:** This notebook should be described as a **lightweight proxy baseline**, not a full official EfficientAD reproduction, unless the code is later replaced with the complete official architecture and training procedure.

Its role is to provide global evidence that can complement local DINOv2 patch detectors.

### 9.5 `05_baseline_patchcore.ipynb`

**Objective:** Establish a PatchCore-style nearest-neighbor patch-memory baseline.

**Main call:**

```python
run_stage05_patchcore(..., backend=FEATURE_BACKEND)
```

**Defense wording:** Describe this as a **lightweight PatchCore-style baseline** if it does not reproduce all official PatchCore details such as the exact multi-layer backbone aggregation, coreset implementation, and official reweighting.

The core idea is still valid: normal patch embeddings form a memory bank and test patches are scored by distance to their nearest normal neighbors.

### 9.6 `06_dinov2_patch_memory_baseline.ipynb`

**Objective:** Use frozen DINOv2-small patch tokens as the normal memory representation.

**Main call:**

```python
run_stage06_dinov2_patchmemory(..., backend=FEATURE_BACKEND)
```

**Flow:**

1. Extract normal training patch tokens.
2. Normalize embeddings for cosine comparison.
3. Store or sample a normal memory bank.
4. Extract test patch tokens.
5. Find the nearest normal memory vector for every test patch.
6. Convert nearest-neighbor distance into patch anomaly scores.
7. Aggregate patch scores into an image-level score.
8. Resize the patch score grid into a spatial anomaly map.

### 9.7 `07_grid_aware_patch_composition.ipynb`

**Objective:** Make patch comparison sensitive to approximate location.

**Main call:**

```python
run_stage07_gridaware(..., backend=FEATURE_BACKEND, region_size=6)
```

The image patch grid is divided into coarse spatial regions. A test patch is compared mainly with normal patches from the matching region instead of the entire image.

This reduces a common nearest-neighbor failure: a visually similar patch in the wrong location should not always be accepted as normal.

This method is the strongest individual detector in the corrected results.

### 9.8 `08_composition_histogram_method.ipynb`

**Objective:** Represent each image by the distribution of DINOv2 visual words.

**Main call:**

```python
run_stage08_composition_histogram(..., backend=FEATURE_BACKEND, k_selected=32)
```

Normal patch tokens are clustered into a vocabulary. Each image becomes a histogram describing how often each visual word occurs.

Possible score mechanisms include distance from the normal histogram distribution, Mahalanobis distance, cosine distance, or an isolation-based outlier score.

The idea is intended to identify global composition changes, but the current implementation performs poorly, especially on structural anomalies. Feature-selection analysis correctly identifies it as harmful to the final fusion.

### 9.9 `09_fusion_experiments.ipynb`

**Objective:** Combine complementary detector scores.

**Main call:**

```python
run_stage09_fusion(...)
```

Scores from different branches have different numeric scales. Each branch is normalized using statistics derived from validation-normal images. The normalized scores are then combined using:

- Mean fusion
- Maximum fusion
- Rank-average fusion

Mean fusion is the strongest pre-specified overall configuration.

### 9.10 `10_full_evaluation_tables.ipynb`

**Objective:** Aggregate final metrics into overall, anomaly-type, and category-level tables.

**Main call:**

```python
run_stage10_final_tables(...)
```

It collects AUROC, F1, precision, recall, thresholds, runtime information, and ablation results.

### 9.11 `11_qualitative_failure_analysis.ipynb`

**Objective:** Move beyond aggregate metrics and inspect specific success and failure cases.

**Main call:**

```python
run_stage11_qualitative(...)
```

The notebook exports representative anomaly maps and comparison cases. These examples are important for explaining whether a score is caused by the real defect, padding, object boundaries, background variation, or incorrect spatial reasoning.

### 9.12 `12_paper_figures_export.ipynb`

**Objective:** Export final figures and package project artifacts for the report, dashboard, and presentation.

**Main call:**

```python
run_stage12_paper_exports(...)
```

## 10. Core Implementation File

The main reusable implementation is:

`01_notebooks/loco_project_utils.py`

It centralizes:

- Repository and dataset paths.
- Random-seed setup.
- Dataset auditing and hashing.
- Letterbox resizing.
- Cleaned-data verification.
- EDA generation.
- Lightweight fallback descriptors.
- DINOv2-small patch feature extraction.
- Nearest-neighbor distance computation.
- Patch-memory scoring.
- Region-aware scoring.
- Composition-histogram construction.
- Fusion and normalization.
- Metric calculation.
- Final table generation.
- Qualitative case export.
- Paper and dashboard asset export.

The DINOv2 backend behavior must be understood:

- An automatic mode may attempt DINOv2 and use fallback features if the runtime cannot load the model.
- An explicit DINOv2 mode should fail loudly if extraction cannot be completed.
- Successful current runtime logs identify the backend as `dinov2-small`.

For defense, always verify the saved runtime log associated with the reported result file.

## 11. Methodological Deep Dive

### 11.1 What DINOv2 Means

**DINOv2** is a self-supervised Vision Transformer representation model. It learns visual features from large image collections without requiring ordinary class labels for every training image.

The name is associated with self-distillation: a student network learns to match stable representations produced by a teacher network under different augmented views. The result is a feature extractor whose embeddings capture shapes, parts, textures, and semantic similarity.

In this project, DINOv2 is **frozen**:

- Its pretrained weights are not fine-tuned on the anomaly dataset.
- It acts as a feature extractor.
- The anomaly detector is built on top of its embeddings.

This is valuable when anomaly labels are scarce or unavailable.

### 11.2 ViT Patches and Patch Tokens

A Vision Transformer divides an image into small rectangular regions called **patches**.

Each patch is projected into a numeric embedding vector. Positional information is added so the transformer knows where the patch came from.

A **patch token** represents local image content. A **global token or pooled embedding** summarizes the image as a whole.

Patch tokens are preferred for localization because they retain a spatial grid:

```text
image region -> patch token -> anomaly score -> heatmap location
```

A global embedding is useful for image classification but may hide a small defect because all local information is compressed into one vector.

### 11.3 Patch Memory

Let the normal memory bank be:

```text
M = {m_1, m_2, ..., m_N}
```

where each \(m_i\) is a normal patch embedding.

For a test patch embedding \(q_j\), the anomaly score is its distance from the nearest normal memory vector:

```text
s_j = min over m in M of d(q_j, m)
```

For normalized vectors, cosine distance can be written as:

```text
d_cos(q, m) = 1 - q^T m
```

Interpretation:

- Small \(s_j\): the test patch resembles at least one normal patch.
- Large \(s_j\): no normal patch adequately explains it.

An image-level score can use the maximum patch score or a robust aggregation of the highest patch scores:

```text
S_image = aggregate({s_1, s_2, ..., s_P})
```

The patch scores are arranged back into their grid and upsampled to create an anomaly heatmap.

### 11.4 PatchCore Principle

The real PatchCore framework stores locally aware normal features from a pretrained backbone. It usually combines intermediate network layers to preserve both semantic and spatial information.

Its core stages are:

1. Extract local normal features.
2. Aggregate or align multi-scale features.
3. Store a representative normal memory bank.
4. Compress the bank using a coreset.
5. Compare test patches with nearest normal features.
6. Aggregate local distances into an image score.
7. Convert local distances into an anomaly map.

The project implements the central memory-bank and nearest-neighbor idea. It should not claim every official PatchCore detail unless the exact components are present in the code.

### 11.5 Coreset Sampling

A complete memory bank can become very large. If there are \(N\) normal patches, \(P\) test patches, and embedding dimension \(D\), brute-force comparison can approach:

```text
O(P * N * D)
```

A coreset selects a smaller subset that still covers the normal feature space.

Greedy farthest-first selection works conceptually as follows:

1. Select an initial normal vector.
2. For every unselected vector, compute its distance to the nearest selected vector.
3. Add the vector with the largest such distance.
4. Repeat until the desired coreset size is reached.

The selected set attempts to preserve diverse normal appearances while reducing memory and inference time.

Tradeoff:

- A larger coreset preserves more normal variation but costs more memory and latency.
- A smaller coreset is faster but may discard rare normal patterns and create false positives.

### 11.6 Region-Aware Memory

Ordinary patch memory ignores where a normal patch was found. A patch from the left side of an object may explain a visually similar patch on the right side even if that placement is logically wrong.

Region-aware memory adds a coarse positional condition:

```text
s_j = min over m in M(region(q_j)) of d(q_j, m)
```

The comparison set is limited to the corresponding region or a controlled neighboring region.

This gives the detector a lightweight form of layout awareness without requiring explicit object detection, component segmentation, or graph construction.

### 11.7 Composition Histogram

Normal DINOv2 patch embeddings are clustered into \(K\) visual words:

```text
C = {c_1, c_2, ..., c_K}
```

Each patch is assigned to its nearest centroid. An image is represented by a normalized histogram:

```text
h = [h_1, h_2, ..., h_K]
```

where \(h_k\) is the proportion of image patches assigned to visual word \(k\).

The anomaly score measures how far the image histogram is from the normal histogram distribution.

This representation discards exact patch locations. It can potentially detect changed component proportions, but it may also:

- Lose spatial arrangement.
- Mix object and background patches.
- Be sensitive to cluster quality.
- Miss small local defects.
- Treat harmless appearance variation as a composition change.

These limitations help explain its weak corrected performance.

### 11.8 Global Image-Stat Proxy

The global proxy summarizes each image using compact statistics such as intensity distribution, color statistics, edge density, or related whole-image descriptors.

It is useful because:

- It is fast.
- It requires little memory.
- It can detect broad image-level changes.
- Its errors may differ from local patch-memory errors.

It is limited because:

- It cannot precisely localize defects.
- A small defect may have little effect on global statistics.
- Background or illumination changes may affect the score.

### 11.9 Fusion

Fusion combines evidence from multiple detectors.

Because detector scores have different scales, each score is first standardized using validation-normal statistics:

```text
z_k(x) = (s_k(x) - mu_k) / sigma_k
```

where \(mu_k\) and \(sigma_k\) come only from validation-normal scores for branch \(k\).

Mean fusion:

```text
S_mean(x) = (1 / K) * sum over k of z_k(x)
```

Maximum fusion:

```text
S_max(x) = max over k of z_k(x)
```

Rank-average fusion replaces raw score magnitude with each detector's relative rank before averaging.

Fusion can improve robustness when branches capture complementary anomaly types. It can also hurt when a weak branch contributes noise, which is why feature selection is necessary.

## 12. Why These Methods Instead of Alternatives

| Method | Strength | Weakness | Reason for project decision |
|---|---|---|---|
| DINOv2 patch memory | Strong pretrained semantic local features; no anomaly-label training | Memory and nearest-neighbor cost | Selected as a transparent lightweight baseline |
| Region-aware memory | Adds approximate layout sensitivity | Sensitive to region granularity and alignment | Selected as strongest individual method |
| Composition histogram | Compact global composition representation | Loses spatial structure; depends on clustering | Evaluated but later identified as harmful |
| Global image-stat proxy | Very fast and complementary | Weak localization and limited semantic understanding | Retained as a lightweight global branch |
| Autoencoder | Learns normal reconstruction | Can reconstruct anomalies too well; blurry residuals | Not selected as primary method |
| GAN reconstruction | Potentially realistic normal modeling | Difficult and unstable training; costly inversion | Rejected for project scope and reproducibility |
| Normalizing flow | Exact density-related objective and localization potential | More training and architectural complexity | Not selected for lightweight implementation |
| Fully supervised classifier | Strong when labels are abundant | Requires representative anomaly labels and may not generalize | Inappropriate for normal-only industrial setup |
| Standard supervised ResNet | Good generic visual features | Features are shaped by labeled source classes | DINOv2 preferred for self-supervised transfer |
| Explicit component counting | Intuitive for logical anomalies | Component extraction was unstable in the probe | Archived as an investigated negative result |

## 13. Corrected Main Results

The current source-of-truth leaderboard is:

`09_dashboard/corrected_main_results.csv`

| Method | Logical AUROC | Overall AUROC | Structural AUROC | Overall F1 |
|---|---:|---:|---:|---:|
| Fusion (mean) | 0.7314 | 0.7609 | 0.8038 | 0.6258 |
| DINOv2 Region-Aware Memory | 0.7301 | 0.7503 | 0.7836 | 0.6259 |
| DINOv2 Patch Memory (NN) | 0.6975 | 0.7244 | 0.7652 | 0.6117 |
| Fusion (rank-avg) | 0.7269 | 0.7201 | 0.7197 | 0.5735 |
| Fusion (max) | 0.6917 | 0.7137 | 0.7414 | 0.5513 |
| Global Image-Stat Detector (proxy) | 0.6341 | 0.6548 | 0.6832 | 0.4740 |
| DINOv2 Composition Histogram (BoVW) | 0.6436 | 0.5757 | 0.4981 | 0.3956 |

### 13.1 Main Interpretation

- **Fusion (mean)** is the strongest pre-specified overall configuration.
- **Region-Aware Memory** is the strongest single detector.
- Structural anomaly detection is generally easier than logical anomaly detection.
- The composition-histogram branch is weak and particularly poor for structural anomalies.
- Rank and maximum fusion do not outperform mean fusion.

These results support the conclusion that local semantic patch evidence and approximate spatial constraints are more reliable than global composition clustering in the current implementation.

## 14. Feature Selection Results

The feature-selection artifact is:

`09_dashboard/feature_selection.json`

Important configurations:

| Configuration | Branch count | Overall AUROC | Logical AUROC | Structural AUROC |
|---|---:|---:|---:|---:|
| All branches including duplicate | 5 | 0.7609 | 0.7314 | 0.8038 |
| Four unique branches | 4 | 0.7472 | Noted in artifact | Noted in artifact |
| Selected global + patch + region-aware | 3 | 0.7638 | 0.7181 | 0.8261 |
| Strong DINOv2 memories only | 2 | 0.7413 | Noted in artifact | Noted in artifact |
| Best single region-aware | 1 | 0.7503 | 0.7301 | 0.7836 |

Leave-one-branch-out importance:

- Removing global proxy reduces overall AUROC by about **0.0431**.
- Removing region-aware memory reduces it by about **0.0197**.
- Removing patch memory reduces it by about **0.0137**.
- Removing the duplicate patch-memory entry has the same duplicated contribution issue.
- Removing composition histogram improves AUROC by about **0.0129**, showing that it is harmful in the all-branch fusion.

The best reduced configuration is:

```text
Global proxy + DINOv2 Patch Memory + DINOv2 Region-Aware Memory
```

It is leaner and slightly improves overall and structural AUROC, although logical AUROC decreases. This is an excellent defense example of why feature selection is not simply "keep every available score."

## 15. Result Files and Their Meanings

### 15.1 `corrected_main_results.csv`

This file is the clean leaderboard used for headline comparisons.

Each row is one detector or fusion configuration. Its columns summarize:

- Overall image-level AUROC.
- Logical anomaly AUROC.
- Structural anomaly AUROC.
- Overall threshold-based F1.

The word **corrected** means the table was rebuilt to fix stale, duplicated, or incorrectly labeled method entries. It is the source that should be used for the dashboard and presentation headline values.

### 15.2 `corrected_per_category.csv`

This file contains the detailed breakdown:

```text
7 methods x 5 categories x 3 anomaly groupings = 105 rows
```

Columns include:

- `method`
- `category`
- `anomaly_type`
- `n_good`
- `n_anomaly`
- `auroc`
- `f1`
- `precision`
- `recall`
- `val_threshold`

It answers questions that the main leaderboard cannot, such as:

- Which method is best for `screw_bag` logical anomalies?
- Does a method perform differently on structural and logical defects?
- Is a high recall accompanied by poor precision?
- What threshold was applied for a specific method and category?

### 15.3 `dashboard_data.json`

This is the structured data package used to build the HTML dashboard. It can contain:

- Main corrected results.
- Per-category results.
- Category names and counts.
- Feature-selection outputs.
- EDA image data.
- Category-specific spatial heatmaps.
- Qualitative examples.
- Explanatory insights.

It separates data preparation from visual rendering. The dashboard generator reads this structured file instead of manually typing values into each chart.

## 16. Thresholds and Metrics

### 16.1 Threshold

Every detector first produces a continuous anomaly score. A threshold converts it into a binary prediction:

```text
score >= threshold -> anomaly
score < threshold  -> normal
```

The exact threshold is not one universal number. It can vary by method and category and is stored in the `val_threshold` column of `corrected_per_category.csv`.

Thresholds should be derived from validation-normal data or a clearly documented validation protocol, not tuned on the final test labels.

### 16.2 AUROC

The Receiver Operating Characteristic curve plots:

```text
True Positive Rate versus False Positive Rate
```

across all possible thresholds.

AUROC is the area under that curve.

Interpretation:

- `1.0`: perfect ranking.
- `0.5`: random ranking.
- Below `0.5`: the ranking is systematically reversed.

AUROC can also be interpreted as the probability that a randomly selected anomaly receives a higher score than a randomly selected normal image.

### 16.3 Image-Level AUROC

Each image receives one anomaly score. The metric measures how well anomalous images are ranked above normal images.

It does not prove that the detector localized the correct defect.

### 16.4 Pixel-Level AUROC

Each image pixel receives an anomaly score from the anomaly map. Scores are compared with binary ground-truth mask pixels.

This measures pixel ranking, but a very large background can dominate the count. It should be interpreted alongside region-aware localization metrics and visual examples.

### 16.5 PRO and AUPRO

**Per-Region Overlap** evaluates how well predicted anomaly regions cover each connected ground-truth defect region as the threshold changes.

It gives small and large defects more balanced treatment than simply counting all pixels together.

If the final result tables do not report pixel AUROC or AUPRO, that should be stated as a current evaluation limitation rather than implied to be complete.

### 16.6 Precision, Recall, and F1

```text
Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
F1        = 2 * Precision * Recall / (Precision + Recall)
```

- Precision asks: among images predicted anomalous, how many truly are anomalous?
- Recall asks: among true anomalies, how many were detected?
- F1 balances both at one chosen threshold.

Unlike AUROC, F1 depends directly on the selected threshold.

## 17. EDA Visual Interpretation

### 17.1 Normal Mean Image

The normal mean image is computed pixel by pixel across normal images:

```text
mu(x, y) = average of normal pixel values at location (x, y)
```

It shows the average normal layout after preprocessing.

Purpose:

- Reveal whether normal objects are spatially aligned.
- Identify stable object regions.
- Expose padding and background patterns.
- Provide an intuitive reference for the expected normal appearance.

### 17.2 Normal Variance Image

The variance image measures how much normal pixels change at each position:

```text
var(x, y) = average[(I(x, y) - mu(x, y))^2]
```

Interpretation:

- Low variance: location is normally stable.
- High variance: location naturally changes across normal examples.

A deviation in a low-variance region may be more suspicious than an equally large deviation in a naturally variable region.

This analysis helps explain why spatially aware anomaly modeling can be useful, but the mean and variance images themselves are descriptive EDA, not the final DINOv2 detector.

### 17.3 Ground-Truth Mask Overlay

Red overlay areas indicate pixels annotated by the dataset as the true anomalous region.

They are:

- Human-provided ground truth.
- Used for evaluation and visual interpretation.
- Not the model's predicted anomaly map.

The viewer should compare the red area with the model heatmap. A good localization result places high model scores over or near the red annotation while avoiding unrelated regions.

### 17.4 Spatial Anomaly-Frequency Heatmap

This EDA image combines ground-truth anomaly masks from many test images:

```text
frequency(x, y) = number or proportion of masks containing an anomaly at (x, y)
```

Bright areas mean defects appear frequently at that normalized location. Dark areas mean defects are rare there.

It is an aggregate dataset statistic, not a prediction for one image.

A single heatmap combining all categories can look like a mixed or blurred object because the categories have different shapes and layouts. The HTML dashboard was therefore updated to display five separate category heatmaps:

1. `breakfast_box`
2. `juice_bottle`
3. `pushpins`
4. `screw_bag`
5. `splicing_connectors`

This category-specific view is easier to interpret and avoids mixing incompatible object geometries.

## 18. HTML Dashboard

The main dashboard file is:

`09_dashboard/dashboard.html`

It is designed as a self-contained offline HTML document with embedded assets.

### 18.1 Dashboard Sections

The dashboard integrates:

- Executive result summary.
- Method leaderboard.
- Logical versus structural comparison.
- Per-category analysis.
- Threshold-based classification metrics.
- Feature-selection results.
- Relevant EDA.
- Category-specific anomaly-frequency heatmaps.
- Explainability and qualitative examples.
- Method-transparency notes and limitations.

### 18.2 Supporting Files

| File | Role |
|---|---|
| `build_dashboard.py` | Assembles data and generates dashboard content. |
| `generate_html.py` | Produces or updates the final HTML structure. |
| `feature_selection.py` | Computes branch comparisons and importance analysis. |
| `dashboard_data.json` | Structured dashboard payload. |
| `corrected_main_results.csv` | Correct headline leaderboard. |
| `corrected_per_category.csv` | Detailed category and anomaly-type metrics. |
| `feature_selection.json` | Feature-selection configurations and importance values. |

### 18.3 Meaning of "Generated Reproducibly"

The dashboard is generated reproducibly when:

1. Saved result files are read by scripts.
2. Metrics and chart data are assembled using repeatable code.
3. The HTML is generated from those structured inputs.
4. The same inputs and code produce the same dashboard values.

This is stronger than manually typing or visually editing every displayed result because it creates a traceable connection between experimental outputs and the final presentation.

### 18.4 Transparency Statement

The dashboard's technical message should remain honest:

- The DINOv2 detectors use real frozen DINOv2-small patch features.
- The reported comparison contains four detector configurations and three fusion rules.
- The global image-stat detector is the lightweight non-DINOv2 proxy.
- Letterbox padding is not yet fully excluded from modeling.
- The current result set is single-seed.

## 19. Reports, Slides, and Figures

Verified project deliverables include:

- `07_paper_draft/Project_A_LOCO_Presentation.pptx`
- `07_paper_draft/Project_A_LOCO_Report.docx`
- `07_paper_draft/Project_A_LOCO_Report.pdf`
- `07_paper_draft/Project_A_LOCO_Report_Product.docx`
- `00_project_planning/Project_A_LOCO_AD_Full_Implementation_Brief.docx`

Build scripts include:

- `07_paper_draft/build_product_report.py`
- `07_paper_draft/build_slides.py`

Important figures include:

- `figure_1_pipeline_overview.png`
- `figure_2_dataset_examples.png`
- `figure_3_component_probe_failure.png`
- `figure_4_method_comparison.png`
- `figure_5_failure_cases.png`
- `figure_6_speed_accuracy_tradeoff.png`
- `figure_feature_selection.png`

The presentation is intended for approximately **10 minutes**, so the spoken explanation should emphasize:

1. Problem and anomaly types.
2. Leakage-safe preprocessing.
3. Why DINOv2 patch features were used.
4. Patch-memory and region-aware methods.
5. Main results and feature selection.
6. Dashboard demonstration.
7. Limitations and conclusion.

The short written report should cover:

- Introduction.
- Product objective.
- Feature descriptions with relevant screenshots.
- User guidelines.
- Implementation details.
- Conclusion.

## 20. Explanations Already Covered in Conversation

The following concepts have already been discussed and should remain consistent in future answers:

- DINOv2 and self-supervised patch embeddings.
- Fusion and its mean, maximum, and rank-average forms.
- AUROC and its ranking interpretation.
- DINOv2 Patch Memory score.
- DINOv2 Region-Aware score.
- Composition Histogram score.
- Global Image-Stat score.
- Historical handcrafted fallback features.
- The meaning of 384x384 pixels.
- Letterbox resizing.
- Normal mean and variance images.
- Ground-truth mask overlays.
- Spatial anomaly-frequency heatmaps.
- Why category-specific heatmaps are preferable.
- The role of `dashboard_data.json`.
- The role of `corrected_main_results.csv`.
- The role of `corrected_per_category.csv`.
- Validation-derived thresholds.
- The difference between an aggregate EDA heatmap and a model prediction heatmap.
- The difference between full official research methods and lightweight proxy or inspired baselines.

## 21. Honest Limitations and Defense Strategy

### 21.1 Single Seed

Current headline results use one seed. A stronger study would repeat stochastic stages across multiple seeds and report mean and standard deviation.

### 21.2 Padding

Letterbox padding is not fully masked during modeling. Future work should exclude padded patch tokens from memory construction, scoring, and localization metrics.

### 21.3 Method Naming

The notebooks named after EfficientAD and PatchCore should not be presented as exact official reproductions unless every defining architectural and training detail is verified.

Safe wording:

- "EfficientAD-inspired lightweight proxy baseline."
- "PatchCore-style patch-memory baseline."
- "DINOv2 nearest-neighbor patch-memory implementation."

### 21.4 Logical Anomalies Remain Difficult

Logical AUROC is lower than structural AUROC for the best overall method. This is expected because local visual similarity alone cannot always detect incorrect counts or long-range relationships.

### 21.5 Composition Histogram Weakness

The composition branch is not hidden. Its poor performance is used as evidence for feature selection and as a documented negative result.

### 21.6 Localization Evaluation

Anomaly maps are available for spatial methods, but the final defense should verify whether pixel-level AUROC and AUPRO were computed in the current final tables. Missing metrics should be acknowledged.

### 21.7 Memory Scaling

Patch-memory methods can become expensive as the number of normal patches grows. Coreset sampling, approximate nearest-neighbor search, half-precision storage, or category-specific indexing are natural future improvements.

### 21.8 Alignment Sensitivity

Region-aware scoring assumes approximate spatial consistency. Object translation, rotation, or framing changes can incorrectly increase anomaly scores.

## 22. Likely Viva Questions and Compact Answers

### Q1. Why use DINOv2 instead of training a CNN from scratch?

The dataset has normal training images but limited anomaly supervision. DINOv2 supplies strong pretrained visual representations without requiring task-specific labels, reducing training cost and overfitting risk.

### Q2. Why use patch tokens instead of only a global image embedding?

Patch tokens preserve local and spatial information. A global embedding can hide a small defect, while patch scores can identify which image region does not match normal memory.

### Q3. How is an anomaly score calculated?

For each test patch, the system finds the nearest normal patch embedding and uses the distance as its anomaly score. Large nearest-neighbor distance indicates poor similarity to normal data.

### Q4. Why is region-aware memory better than unrestricted patch memory?

It restricts matching by coarse location. This prevents a visually normal patch from one object region from incorrectly explaining a similar patch in a logically wrong position.

### Q5. What is the main result?

Mean fusion achieves approximately 0.761 overall AUROC, while region-aware memory is the strongest single detector at approximately 0.750 overall AUROC.

### Q6. Why is structural AUROC higher than logical AUROC?

Structural defects often create direct local visual changes. Logical defects can contain visually normal components arranged incorrectly, requiring broader relational understanding.

### Q7. Why did the composition histogram perform poorly?

It discards precise location, depends on cluster quality, and can mix background and object patches. These losses are especially damaging for local structural defects.

### Q8. Why keep a weak global proxy?

Its global errors are partially complementary to local patch detectors. Feature-selection results show that removing it causes the largest reduction in overall fusion AUROC.

### Q9. What is fusion?

Fusion normalizes scores from multiple detectors and combines them into one score. It integrates different anomaly evidence rather than relying on a single representation.

### Q10. Why is AUROC used?

AUROC evaluates ranking over all possible thresholds, which is useful when the operational threshold is not fixed. It measures how consistently anomalies receive higher scores than normal images.

### Q11. Why also report F1?

F1 measures precision-recall balance at one chosen threshold. It reflects practical binary decisions, while AUROC is threshold independent.

### Q12. How was data leakage prevented?

Normal training images fit the models, validation-normal images control normalization and thresholding, and test anomalies are reserved for final evaluation.

### Q13. Is this the official PatchCore implementation?

It is a lightweight PatchCore-style implementation centered on normal patch memory and nearest-neighbor scoring. The defense should not claim full official equivalence unless all official components are verified.

### Q14. What happens when the memory bank grows?

RAM use and nearest-neighbor latency increase. A representative coreset or approximate search index can reduce that cost while attempting to preserve normal feature coverage.

### Q15. What would you improve first?

Mask padded regions, repeat experiments across seeds, compute complete pixel-level metrics, add principled coreset sampling, and investigate stronger relational modeling for logical anomalies.

## 23. Reproduction Guidance

Install dependencies from:

```text
requirements.txt
```

Key packages include:

- NumPy
- pandas
- scikit-learn
- SciPy
- Pillow
- Matplotlib
- python-docx
- python-pptx
- nbformat
- PyTorch
- torchvision
- transformers
- huggingface_hub

Recommended execution order:

```text
01_preprocessing_reproducibility.ipynb
02_eda_cleaned_letterbox.ipynb
03_dinov2_component_probe_archive.ipynb
04_baseline_efficientad.ipynb
05_baseline_patchcore.ipynb
06_dinov2_patch_memory_baseline.ipynb
07_grid_aware_patch_composition.ipynb
08_composition_histogram_method.ipynb
09_fusion_experiments.ipynb
10_full_evaluation_tables.ipynb
11_qualitative_failure_analysis.ipynb
12_paper_figures_export.ipynb
```

Before rerunning:

1. Verify dataset paths in the configuration.
2. Confirm raw data remains read-only.
3. Verify DINOv2 is actually loaded.
4. Record the runtime backend.
5. Preserve test isolation.
6. Rebuild corrected result tables before regenerating presentation assets.

## 24. Current Priorities

Recommended priorities for future work:

1. Verify every dashboard value against the corrected CSV and JSON files.
2. Preserve the five category-specific anomaly-frequency heatmaps.
3. Audit the final report and slides for outdated fallback-feature statements.
4. Use honest proxy and style-baseline wording.
5. Add valid-content masking for letterbox padding.
6. Compute and report pixel-level AUROC and AUPRO if not already present.
7. Repeat stochastic experiments using multiple seeds.
8. Add a documented coreset experiment for the patch memory.
9. Improve logical anomaly reasoning with relational or positional modeling.
10. Rehearse the presentation to fit the 10-minute limit.

## 25. Rules for Future Changes

- Read the current file before modifying any artifact.
- Do not overwrite user changes without inspection.
- Do not revert the category-specific heatmap update in `09_dashboard/dashboard.html`.
- Treat corrected CSV files as the headline result source.
- Verify backend logs before claiming DINOv2 results.
- Do not describe proxy baselines as full official reproductions.
- Do not tune on test anomaly labels.
- Keep raw data read-only.
- Keep generated artifacts traceable to scripts and saved data.
- Preserve the distinction between ground-truth masks, EDA frequency maps, and model anomaly maps.
- Avoid claiming pixel-level evaluation unless the metric files verify it.

## 26. Starter Prompt for a New Session

```text
Read context.md, README.md, the current git status, and the relevant repository files before making changes. This is the LOCO Anomaly Inspector project using MVTec LOCO AD and real frozen DINOv2-small patch features for the current DINOv2 branches. Preserve the five-category spatial heatmap update in 09_dashboard/dashboard.html. Treat corrected_main_results.csv, corrected_per_category.csv, feature_selection.json, runtime logs, and the current source code as the factual basis. Clearly distinguish lightweight proxy or style baselines from full official method reproductions. Continue the requested task without reverting unrelated user work.
```

