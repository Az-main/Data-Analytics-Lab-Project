# Critical Peer Review — Project A: MVTec LOCO Logical Anomaly Detection

**Reviewer role:** Data Science / Computer-vision AD researcher
**Artifact reviewed:** `Project_A_LOCO_AD/` (12 notebooks + `loco_project_utils.py`, audit CSVs, baseline/method result tables, paper figures, brief docx)
**Date:** 2026-06-01
**Verdict (one line):** Excellent reproducibility engineering wrapped around results that **do not actually evaluate the methods they are named after**. Two of the three submission criteria (dashboard, written report) are missing. Not submittable in current state; the fixes are mostly mechanical, not conceptual.

---

## 0. The two findings that override everything else

Before the focus-area breakdown, two issues are severe enough that nothing downstream (leaderboards, ablations, fusion, figures) can be trusted until they are fixed. I verified both directly in your output files, not just the code.

### 0.1 Every reported number was produced by a *fallback proxy*, not the real method
`extract_patch_features()` (`loco_project_utils.py:868`) tries DINOv2 and silently drops to `simple_patch_features()` — a 7-dimensional hand-crafted vector (RGB mean ×3, RGB std ×3, edge density ×1) on a 24×24 grid — whenever `transformers`/`torch`/the model weights are unavailable (`backend="auto"`, lines 875–892). Your `efficiency_table.csv` shows the actual backend used for the **submitted** run:

| Method (as labelled) | `feature_backend` actually used |
|---|---|
| EfficientAD | `fallback_global_feature_teacher_student_proxy` (global z-score RMS, line 1313) |
| PatchCore | `fallback_patch_stats` |
| DINOv2 PatchMemory | `fallback_patch_stats` |
| GridAware DINOv2 | `fallback_patch_stats` |
| CompositionHistogram | `fallback_patch_stats` |

So none of the rows in `main_results_table.csv` are EfficientAD, PatchCore, or DINOv2. They are all variations of a 7-D colour/edge descriptor. Your own code is honest about this — `efficientad_logs.txt` literally says *"Do not report these rows as official EfficientAD unless rerun with Anomalib"* and the EfficientAD config carries a `strict_note` to install Anomalib. The brief explicitly intends the real run to happen in Colab with DINOv2 + Anomalib. **The submitted artifact is the local placeholder, not the experiment.** This is the single thing to fix first.

### 0.2 "PatchCore" and "DINOv2 PatchMemory" are byte-for-byte the same result
`run_stage05_patchcore` and `run_stage06_dinov2_patchmemory` both call `run_patch_memory_family(...)` with identical arguments (`grid=24, max_patches=50000, include_xy=False, aggregate_mode="top5"`) and the same fallback backend. I merged the two score CSVs on `image_id`: **1873/1873 rows have identical scores (`np.allclose == True`)**. They are not two methods; they are one computation printed twice. Reporting them as separate baselines in a results table is, in a peer-review setting, a fabricated comparison — even if unintentional.

A related duplication: `Best Fusion`, `Fusion WeightedAvg`, and the plain average are the same thing. `inv_sd_weights` is initialised to all-ones then normalised (lines 1743–1745), i.e. uniform weights = mean. The table confirms `Best Fusion` and `Fusion WeightedAvg` are identical to 16 decimal places. The "weighted" fusion is not weighted.

---

## 1. Submission-criteria audit (your 4 stated requirements)

| # | Required | Status | Evidence |
|---|---|---|---|
| 1 | **Dashboard** | ❌ **Missing** | No `.html`/Streamlit/Dash/Gradio/Voila app anywhere in the tree. Only static matplotlib PNGs in `04_probe_results`, `06_method_results/Qualitative`, `07_paper_draft/figures`. |
| 2 | **ML/DL model OR explainable analysis OR bucket creation** | ⚠️ **Partially met** | Patch-memory NN, IsolationForest, MiniBatchKMeans visual-words, fusion = legitimate modelling. But all on proxy features (see §0). Explainability = anomaly heatmaps only; no SHAP/attribution/component buckets surfaced to a user. |
| 3 | **Only relevant EDA in dashboard** | ❌ **N/A** | EDA exists (`run_stage02_eda`) and is genuinely relevant (layout variation, mask-area, spatial heatmap, edge density), but there is no dashboard to put it in. |
| 4 | **Short report, 3–5 pages** | ❌ **Missing** | `07_paper_draft/` contains a `figures/` folder only — **no prose report**. The brief describes the contribution but no 3–5 page document was written. |

You are 2/4 on the hard deliverables. The good news: the modelling and EDA substance exists, so the dashboard and report are assembly work, not new research.

---

## 2. Focus-area review

For each area: **(a) done well / (b) gaps / (c) fix.**

### 2.1 Methodology & algorithm choices
**(a)** The research framing is sound and self-aware. The brief correctly rejects naive component-counting after the DINOv2 probe (`component_probe_conclusion.txt`) and pivots to patch-composition modelling — a defensible, literature-grounded direction. Using a frozen backbone + memory bank (PatchCore family) and a bag-of-visual-words composition histogram are both reasonable for *logical* anomalies, which need global layout sensitivity that pixel-local methods miss.
**(b)** (i) The methods reduce to the same NN-on-patches engine with minor wrappers; the "grid-aware" variant is the only genuine methodological contribution over PatchCore (region-conditioned memory, `region_id`, line 1444). (ii) The composition histogram uses Mahalanobis as the live score (`score = mahal`, line 1618) but computes cosine and IsolationForest and never uses them — dead scoring paths. (iii) EfficientAD proxy is a *global* image descriptor; it structurally cannot localise logical anomalies, so calling it EfficientAD is doubly misleading.
**(c)** Run the real backbones (§0). Then keep exactly one shared patch-memory core and present GridAware + CompositionHistogram as the two *novel* heads on top of it. Either use the multi-score composition (combine Mahalanobis/cosine/IF via the validation set) or delete the unused scorers.

### 2.2 Evaluation metrics & results
**(a)** AUROC is threshold-free and computed correctly (`roc_auc_score`, line 933). Logical and structural anomalies are reported separately — exactly what the LOCO benchmark demands, and a common mistake to average them; you didn't. Per-category breakdown is thorough.
**(b)** **(i) Test-set threshold leakage in F1.** `f1_max` (line 901) sweeps 200 thresholds and picks the one maximising F1 *on the evaluation set, which includes test* (`per_category_metrics`, line 951–965). Every `f1_max`/`precision_at_f1`/`recall_at_f1` you report is an optimistic upper bound, contradicting your own protocol ("validation/good reserved for thresholding"). **(ii) Wrong primary metric.** The official MVTec LOCO metric is **sPRO** (saturated per-region overlap) plus image-level AUROC. You report only image-level AUROC, so you cannot compare to any published LOCO number. **(iii) No variance.** Single seed, no confidence intervals, no significance test between methods separated by <0.02 AUROC. **(iv)** Several cells are below chance — `splicing_connectors` logical AUROC = 0.35–0.49 across methods — which is a systematic feature failure, not noise, and is unremarked.
**(c)** Fit the F1 threshold on `validation/good` + a held-out anomaly proxy, never on test. Implement sPRO using the masks you already cleaned (you have pixel GT!). Add 3–5 seeds and report mean ± std; use a Wilcoxon signed-rank test across the 5 categories for method pairs.

### 2.3 Dataset preprocessing & feature engineering
**(a)** This is the strongest part of the project and is genuinely publication-grade. Read-only raw-data policy; aspect-preserving letterbox at 384² with bilinear (image) / nearest (mask) interpolation and re-binarisation (`letterbox_resize_pil`, line 343); MD5 + average-hash duplicate-leakage detection across splits (`save_hashes`, line 287); full count reconciliation against expected (3651 products / 1246 masks / 4897 PNG, 0 corrupted); environment + `pip freeze` capture. The `validation/good` split is correctly carved out and reserved.
**(b)** The *features* are the weakness: 7-D colour+edge stats per patch carry almost no semantic/relational information, which is precisely what logical anomalies require. Letterbox padding injects large zero-borders that the patch grid will see as "normal black" regions — a confound for any patch-distance method. No normalisation of features before NN (Euclidean on raw mean/std/edge mixes scales).
**(c)** Replace with DINOv2 patch tokens (the intended path). Mask out / exclude padded patches from both memory and scoring. Standardise features (z-score per dimension) or use cosine distance, as AnomalyDINO does, before the NN step.

### 2.4 Model architecture & design choices
**(a)** Modular stage functions (`run_stage01..12`) with a single shared utils file; consistent output contracts; deterministic seeding incl. cudnn flags (line 118). Memory subsampling cap (50k) bounds cost. Region-conditioned memory is a thoughtful design for layout-sensitive AD.
**(b)** No backbone abstraction beyond the DINOv2/fallback fork; no caching of extracted features to disk (every stage re-extracts, so the 5 methods recompute identical features 5×). `IsolationForest(contamination="auto")` fit on histograms is unused. No GPU batching in the DINOv2 path (one image at a time, line 854).
**(c)** Add a `features/` cache keyed by image hash + backbone; extract once, reuse across all five methods. Batch the DINOv2 forward pass. Make the backbone a config field so a backbone ablation (handcrafted vs WideResNet50 vs DINOv2-S/B) is a one-line change.

### 2.5 Reproducibility & documentation
**(a)** Best-in-class for a student project: seeds, env freeze, hashes, per-file resize metadata, leakage candidates CSV, manifest + zip export, JSON configs per method, and honest logs about proxies. Someone could re-run this.
**(b)** No `README.md` at project root, no `requirements.txt` pin with versions actually resolved (the freeze captured the *local* env that had no torch/transformers — so reproducing the fallback, not the experiment). No notebook execution-order doc outside the brief. No license/citation file for the dataset in the project folder.
**(c)** Add root `README.md` (run order, env setup, how to switch `backend="dinov2"`), a pinned `requirements.txt` from a *real* GPU run, and the MVTec LOCO citation/license. Commit the actual `pip freeze` from the Colab DINOv2 run.

### 2.6 Scalability & deployment readiness
**(a)** Inference times are logged per method; CompositionHistogram (~62 ms/img, 1778-vector bank) and GridAware (~107 ms/img) are deployment-plausible. Memory caps prevent unbounded banks.
**(b)** No serving layer, no ONNX/TorchScript export, no batch/stream API, no model persistence (memory bank is rebuilt every run, not saved). Per-image Python loops won't scale to a line camera. The reported times are for the *7-D proxy*, not DINOv2 — real latency will be far higher and is unmeasured.
**(c)** Persist the fitted memory bank / KMeans / threshold to disk; add a `predict(image)->score,heatmap` entry point; benchmark real-backbone latency on CPU and GPU; wrap as a FastAPI or Gradio endpoint (which doubles as your dashboard, §3).

### 2.7 Research novelty & originality
**(a)** The brief's positioning is mature: it explicitly disclaims novelty against AnomalyDINO, ComAD, CSAD, SALAD, ViGLAD/SLSG and targets "lightweight, reproducible, evidence-driven, carefully benchmarked" — the right, honest framing. Region-conditioned patch memory + composition histogram + validation-normalised fusion is a modest but legitimate combination.
**(b)** As actually executed, novelty ≈ 0: the proxy features make it a colour-histogram baseline, and the one novel idea (grid-aware memory) is not isolated by an ablation that holds features constant against vanilla PatchCore. The fusion "contribution" collapses because three of four fusion variants are identical/uniform.
**(c)** To have a defensible contribution, frame it as: *"region-conditioned memory + composition histogram as a lightweight, training-free LOCO baseline on frozen DINOv2, with a controlled study of where it beats/loses to PatchCore and EfficientAD."* That requires the real backbone + sPRO + the ablation in §6.

---

## 3. Missing deliverable 1 — the Dashboard (concrete plan)

Build a single **Gradio** or **Streamlit** app (also satisfies §2.6 deployment). Minimum viable:
- **Upload / pick image →** show anomaly score, predicted label at the validation-chosen threshold, and the patch-distance heatmap overlay (you already generate these in `save_patch_map`).
- **Relevant EDA tab only** (criterion #3): per-category counts, mask-area distribution, spatial anomaly heatmap, edge-density boxplots — reuse the figures from `run_stage02_eda`. Drop intensity histograms if they don't inform the model story.
- **Leaderboard tab:** the corrected `main_results_table.csv` (logical vs structural AUROC + sPRO), with the proxy-vs-real backbone clearly labelled.
A live-data version could be saved as a persistent artifact, but for a lab submission a local Gradio app is sufficient and fastest.

## 4. Missing deliverable 2 — the 3–5 page report (outline)
1. **Intro & problem** (½ p): logical vs structural anomalies; why LOCO is hard.
2. **Data & preprocessing** (½ p): your audit/letterbox/leakage pipeline — this is your strongest material, feature it.
3. **Methods** (1 p): shared patch-memory core; GridAware region memory; composition histogram; validation-normalised fusion. One pipeline figure (you have `figure_1`).
4. **Results** (1–1.5 p): main table (logical/structural AUROC + sPRO), speed–accuracy plot, one ablation table, 2–3 qualitative cases incl. the `splicing_connectors` failure.
5. **Discussion & limitations** (½ p): honest proxy-vs-real note, gap to SOTA, failure modes.
6. **Reproducibility** (¼ p): seeds, env, splits.

---

## 5. Literature comparison

| # | Paper | Venue / Year | Method | How your work compares |
|---|---|---|---|---|
| 1 | **Bergmann et al., "Beyond Dents and Scratches: Logical Constraints in Unsupervised AD"** (GCAD) | IJCV 2022 | Global+local autoencoder, two branches; introduces MVTec LOCO + sPRO metric | This is your benchmark's origin. You must report **sPRO** to compare. GCAD's two-branch (global=logical, local=structural) idea is exactly what your single patch-distance score lacks; your GridAware region memory is a poor-man's "global" branch. |
| 2 | **Batzner et al., "EfficientAD"** | WACV 2024 | Student–teacher + autoencoder, millisecond latency, ~90% LOCO image AUROC | You *name* EfficientAD but run a global z-score proxy. Their real numbers (~0.90 mean image AUROC) are ~16 pts above your best proxy fusion (0.74). Adopt their PDN distillation, or run it via Anomalib and cite honestly. |
| 3 | **Hsieh et al., "CSAD: Unsupervised Component Segmentation for Logical AD"** | 2024 (arXiv 2408.15628) | Foundation-model component segmentation + patch histogram; **95.3% avg AUROC (96.7 logical / 94.0 structural)** | Closest in spirit to your composition histogram, but uses *learned component segmentation* instead of KMeans visual words. Your logical AUROC (~0.69 proxy) is ~28 pts behind. Their component approach is what your probe rejected — worth revisiting with SAM-style segmentation. |
| 4 | **Damm et al., "AnomalyDINO: Patch-based Few-shot AD with DINOv2"** | WACV 2025 | Training-free DINOv2 patch similarity (cosine), memory bank | This is *literally your intended method*. They show DINOv2 + cosine patch NN reaches SOTA few-shot. Use their cosine + masking + augmentation-free recipe as your real backbone; your fallback is the ablation "without DINOv2". |
| 5 | **"Separating Novel Features for Logical AD (SLSG/SNF)"** & **masked-image-modeling LOCO (arXiv 2410.10234)** | 2024 | Feature separation / MIM reconstruction for logical anomalies | Demonstrate that logical AD benefits from explicit normal-feature modelling beyond NN distance — a direction your composition histogram gestures at but under-develops. |

**Where you stand vs SOTA:** best submitted mean AUROC ≈ **0.74** (and it's on proxy features). Published LOCO image-AUROC: GCAD ~0.83, EfficientAD ~0.90, CSAD ~0.95. You are **15–25 points behind**, and not yet measuring the official sPRO metric, so you are currently not on the leaderboard at all. With the real DINOv2 backbone you should expect a large jump (AnomalyDINO-class features), which is the entire point of fixing §0.

## 6. GitHub repository comparison

| # | Repo | What it does | Does better than you | You do better |
|---|---|---|---|---|
| 1 | **openvinotoolkit/anomalib** | Reference impls of PatchCore, EfficientAD, FastFlow, etc. + standardised LOCO/MVTec benchmarking | Real, validated method implementations; metric suite incl. AUPRO; configs/logging | Your data-audit + leakage-hashing + letterbox-metadata pipeline is more rigorous than their default datamodule |
| 2 | **amazon-science/patchcore-inspection** (official PatchCore) | Coreset-subsampled WideResNet patch memory | Greedy **coreset** selection (you use random 50k subsample); proper feature locality (adaptive avg-pool neighbourhoods) | You add region-conditioning, which vanilla PatchCore lacks |
| 3 | **dammsi/AnomalyDINO** | Training-free DINOv2 patch AD (your target method) | The actual DINOv2 pipeline you stubbed: preprocessing, masking, cosine NN, few-shot protocol | Your reproducibility/audit scaffolding and explicit fusion experiments |
| 4 | **nelson1425/EfficientAD** (popular unofficial) | EfficientAD reproduction in PyTorch | A trainable student–teacher you can actually run for the EfficientAD row | You have a cleaner multi-method evaluation harness |
| 5 | **CSAD / component-aware repos** (e.g. authors' release for arXiv 2408.15628) | Component segmentation + histogram for logical AD | Learned components beat your KMeans visual words on logical anomalies | Your validation-normalised fusion across heterogeneous scores |

**Patterns worth adopting:** (i) coreset subsampling from PatchCore; (ii) cosine distance + DINOv2 from AnomalyDINO; (iii) Anomalib's metric/logging harness so your numbers are directly comparable; (iv) feature caching to disk (all four mature repos do this).

---

## 7. Prioritised improvement roadmap

### P0 — Critical (block submission / make results valid)
1. **Run the real backbone.** Set `backend="dinov2"` with `transformers`+`torch` on Colab GPU so `feature_backend == "dinov2-small"` (or larger). Re-generate every table. *Why:* without this, no result is attributable to its named method (§0.1).
2. **Collapse the duplicate methods.** Stop reporting PatchCore and DINOv2 PatchMemory as two rows (identical, §0.2); differentiate them honestly (e.g. PatchCore = WideResNet features, DINOv2 = DINOv2 features) or merge. Remove/repair the uniform "WeightedAvg" fusion.
3. **Fix F1 threshold leakage.** Select the threshold on `validation/good` (+ proxy anomalies), not on test (`f1_max` over test, line 901/951). *Why:* current F1/precision/recall are optimistic and contradict your own protocol.
4. **Write the 3–5 page report** (§4) and **build the dashboard** (§3). *Why:* two of four graded criteria are currently absent.

### P1 — Important (quality / comparability)
5. **Implement sPRO** using your cleaned masks. *Why:* it is *the* LOCO metric; without it you can't cite or be cited against the benchmark.
6. **Backbone ablation holding everything else fixed** (handcrafted-7D vs WideResNet50 vs DINOv2-S/B) — this turns your fallback into a legitimate ablation row and isolates the value of GridAware vs vanilla memory.
7. **Mask out letterbox padding** from memory/scoring; **z-score or cosine** the features before NN.
8. **Multi-seed + significance** (mean±std over 3–5 seeds, Wilcoxon across categories). Investigate the sub-chance `splicing_connectors` logical result.
9. **Feature caching** to disk (extract once, reuse across 5 methods) and **persist fitted models** for deployment.

### P2 — Optional (publishability / polish)
10. **Coreset subsampling** (PatchCore-style) instead of random 50k.
11. **Add AnomalyDINO and a real EfficientAD (Anomalib) as external baselines** for an honest SOTA gap table.
12. **Component-aware head** (SAM/CSAD-style segmentation feeding the composition histogram) — revisits the idea your probe rejected, now with a stronger segmenter.
13. **Serving:** ONNX export + FastAPI/Gradio endpoint with latency benchmark on real backbone.

---

## 8. Path to a publishable paper
As-is: **not publishable** (proxy results, missing sPRO, duplicate methods). Realistic target after P0+P1: a **reproducibility / benchmark workshop paper** (e.g. a CVPR/ICCV VAND-style workshop, or a venue like VISAPP), framed exactly as the brief suggests — *"a lightweight, training-free, fully reproducible patch-composition baseline for MVTec LOCO, with a controlled backbone ablation and honest failure analysis."* The contribution is **rigor + reproducibility + a clean GridAware-vs-PatchCore ablation**, not a new SOTA number. Your audit/leakage/letterbox pipeline is genuinely above the norm and should be a named contribution. To push toward a main-track paper you would need the component-aware head (#12) to actually close part of the gap to CSAD on logical anomalies.

## 9. Missing baselines & ablations (checklist)
- [ ] Real PatchCore (WideResNet50 + coreset) — *named but not run*
- [ ] Real EfficientAD (Anomalib/nelson1425) — *named but not run*
- [ ] AnomalyDINO (cosine, training-free) — direct competitor
- [ ] GCAD or any two-branch global/local method — the LOCO origin baseline
- [ ] Backbone ablation: handcrafted vs WideResNet vs DINOv2-S/B (features held against method)
- [ ] Distance-metric ablation: Euclidean vs cosine; raw vs standardised features
- [ ] Padding-masking ablation (with/without letterbox borders)
- [ ] Aggregation ablation already exists (top-k) — extend to real features
- [ ] Pixel-level sPRO in addition to image-level AUROC

## 10. Related datasets for benchmarking
- **MVTec AD** — structural-only sanity check; almost every paper reports it, gives comparability.
- **VisA** — larger, multi-instance; tests generalisation of the patch-memory + composition idea.
- **MPDD** — metal parts, orientation/position variation; stresses logical/layout sensitivity.
- **Real-IAD** — large-scale multi-view industrial; tests scalability of your memory bank.
- **BTAD, MTD** — small classic sets for quick cross-dataset tables.
- Within LOCO itself: confirm all **5 categories** are run (the cleaned tree has them); report each separately as you already do.

---

### Sources
- [Beyond Dents and Scratches (GCAD / MVTec LOCO), IJCV 2022](https://link.springer.com/article/10.1007/s11263-022-01578-9)
- [MVTec LOCO AD dataset](https://www.mvtec.com/company/research/datasets/mvtec-loco)
- [EfficientAD, WACV 2024](https://openaccess.thecvf.com/content/WACV2024/papers/Batzner_EfficientAD_Accurate_Visual_Anomaly_Detection_at_Millisecond-Level_Latencies_WACV_2024_paper.pdf)
- [CSAD: Unsupervised Component Segmentation for Logical AD](https://arxiv.org/html/2408.15628)
- [AnomalyDINO, WACV 2025](https://openaccess.thecvf.com/content/WACV2025/papers/Damm_AnomalyDINO_Boosting_Patch-Based_Few-Shot_Anomaly_Detection_with_DINOv2_WACV_2025_paper.pdf) · [code: dammsi/AnomalyDINO](https://github.com/dammsi/AnomalyDINO)
- [Separating Novel Features for Logical AD](https://arxiv.org/pdf/2407.17909) · [Logical AD with Masked Image Modeling](https://arxiv.org/html/2410.10234v2)
- [anomalib (PatchCore/EfficientAD reference impls)](https://github.com/openvinotoolkit/anomalib) · [amazon-science/patchcore-inspection](https://github.com/amazon-science/patchcore-inspection)
