# CONTEXT — Project A (MVTec LOCO Anomaly Detection) — Handoff for Claude Code

> **Purpose of this file:** a complete handoff so a fresh Claude Code session on another laptop can continue this project with full context. Read this top-to-bottom first. It summarizes the whole planning conversation, the current state, what was fixed, what's left, and exactly how to continue.

---

## 0. TL;DR — where things stand

- **Project:** Unsupervised logical + structural anomaly detection on **MVTec LOCO AD** (5 categories: breakfast_box, juice_bottle, pushpins, screw_bag, splicing_connectors). Train on normal images only; detect both local defects (structural) and global rule violations (logical).
- **Submission criteria (faculty lab):** (1) Dashboard, (2) ML/DL model or explainable analysis or bucket creation, (3) only relevant EDA in dashboard, (4) short report 3–5 pages.
- **Status: SUBMISSION-READY on the "safe path."** Dashboard, 4-page report, and submission guide are built and saved. All 4 criteria met.
- **Biggest caveat (must understand):** the current numerical results were produced by a **handcrafted fallback feature pipeline**, NOT real DINOv2/PatchCore/EfficientAD. This was discovered, made honest (truthful method names, duplicate removed, leakage fixed), and documented. The real-DINOv2 upgrade is the main remaining work.

---

## 1. Files to transfer / key deliverables

When moving to your laptop, bring the whole `Project_A_LOCO_AD/` folder. The files below are the important ones. **The .docx and .pdf you will transfer manually to Claude Code** (they're binary; just hand them over or keep them in the folder).

| File | What it is | Transfer note |
|---|---|---|
| `CONTEXT.md` | **This handoff file** | primary context for Claude Code |
| `09_dashboard/dashboard.html` | Self-contained interactive dashboard (double-click to open) | the "Dashboard" deliverable |
| `07_paper_draft/Project_A_LOCO_Report.docx` | 4-page report (editable) | **give to Claude Code manually** |
| `07_paper_draft/Project_A_LOCO_Report.pdf` | 4-page report (print-ready) | **give to Claude Code manually** |
| `SUBMISSION_GUIDE.md` | Demo script + criteria mapping + Colab swap steps | reference |
| `ROADMAP_Project_A_LOCO_AD.md` | Full A-to-Z roadmap (10 phases + stretch) | the master plan |
| `PEER_REVIEW_Project_A_LOCO_AD.md` | Critical peer review (findings, lit/GitHub comparison) | rationale for every fix |
| `09_dashboard/corrected_main_results.csv` | Honest leaderboard numbers | results source |
| `09_dashboard/corrected_per_category.csv` | Per-category honest numbers | results source |
| `09_dashboard/build_dashboard.py` | Recomputes corrected metrics + builds `dashboard_data.json` | re-run after new results |
| `09_dashboard/generate_html.py` | Builds `dashboard.html` from `dashboard_data.json` | re-run after build_dashboard |
| `09_dashboard/build_report.js` | Builds the report .docx (Node + `docx`) | re-run after build_dashboard |
| `01_notebooks/loco_project_utils.py` | All pipeline logic (preprocessing, methods, fusion, eval) | the core code |
| `Project_A_LOCO_AD_Full_Implementation_Brief.docx` | Original project brief (intent, Colab plan) | background |

---

## 2. Project folder structure

```
Project_A_LOCO_AD/
├── 01_notebooks/              # 12 notebooks (01–12) + loco_project_utils.py (the engine)
├── 02_audit_reproducibility/  # audit CSVs, hashes, leakage check, env freeze, preprocessing config
├── 03_cleaned_data/           # loco_cleaned_letterbox_384/<cat>/<split>/<defect>/*.png  (+ ground_truth masks)
├── 04_probe_results/          # EDA figures + DINOv2 component-probe (probe rejected component-counting)
├── 05_baselines/              # EfficientAD/, PatchCore/  (scores, per-category, runtime CSVs)
├── 06_method_results/         # GridAware_DINOv2/, CompositionHistogram/, DINOv2_PatchMemory/, Fusion/, Final_Evaluation/, Qualitative/
├── 07_paper_draft/            # figures/ + Project_A_LOCO_Report.docx/.pdf
├── 08_exports/                # manifest + zip
├── 09_dashboard/              # dashboard.html, build scripts, corrected_*.csv, dashboard_data.json
├── CONTEXT.md   ROADMAP_*.md   PEER_REVIEW_*.md   SUBMISSION_GUIDE.md
```
Raw data is one level up in `Phase 1/` and is treated as **read-only**.

---

## 3. What the pipeline actually does (methods)

Each image → grid of patches → compact handcrafted descriptor per patch (RGB mean+std + edge density). Methods:
- **Patch-Stat Memory (NN)** — PatchCore-style memory bank of normal patches; score = nearest-neighbour distance. (structural-leaning)
- **Region-Aware Patch Memory** — memory conditioned on coarse spatial region (weak global awareness). Best structural AUROC.
- **Composition Histogram (BoVW)** — k-means visual words → image word-histogram → Mahalanobis distance to normal. (logical-leaning)
- **Global Image-Stat Detector** — single global descriptor vs normal mean (fast baseline). [was mislabeled "EfficientAD"]
- **Fusion** — z-normalize each scorer on **validation/good only**, then mean / max / rank-average.

Splits: **train/good** = fit; **validation/good** = threshold + normalization; **test** = evaluation only. Masks never used for fitting.

---

## 4. Corrected, honest results (current)

Image-level AUROC, averaged over 5 categories. F1 at a fixed validation-derived threshold (90th percentile of validation/good scores — **no test-label tuning**).

| Method | Logical | Structural | Overall | F1 (overall) |
|---|---|---|---|---|
| **Fusion (max)** | 0.706 | 0.780 | **0.737** | 0.593 |
| Fusion (mean) | 0.687 | 0.797 | 0.734 | 0.567 |
| Region-Aware Patch Memory | 0.659 | **0.814** | 0.726 | 0.576 |
| Fusion (rank-avg) | 0.672 | 0.787 | 0.721 | 0.508 |
| Composition Histogram (BoVW) | 0.666 | 0.659 | 0.660 | 0.448 |
| Global Image-Stat Detector | 0.634 | 0.683 | 0.655 | 0.474 |
| Patch-Stat Memory (NN) | 0.580 | 0.744 | 0.654 | 0.443 |

Numbers are modest because features are handcrafted, not learned. AUROC is threshold-free; only F1 changed after the leakage fix (it dropped to honest values).

---

## 5. Critical findings from the peer review (the "why" behind fixes)

1. **All results used a fallback proxy, not the named methods.** `extract_patch_features(backend="auto")` silently falls back to `simple_patch_features` (7-D handcrafted) when DINOv2/torch unavailable. The submitted run used `fallback_patch_stats` / `fallback_global_feature_teacher_student_proxy` everywhere. → Fixed by **honest renaming** + documenting the DINOv2 path.
2. **"PatchCore" ≡ "DINOv2 PatchMemory"** — byte-identical (same code path `run_patch_memory_family`, verified 1873/1873 matching scores). → **Duplicate dropped**; kept one method.
3. **"Best Fusion" ≡ "Fusion WeightedAvg"** — weights were all-ones (uniform), so "weighted" = plain mean. → Dropped the duplicate.
4. **Test-set F1 threshold leakage** — `f1_max` swept thresholds on the test set. → **Fixed**: threshold now from validation/good only.
5. **No dashboard, no written report** (2 of 4 criteria missing). → **Built both.**
6. Reports only image-AUROC; the official LOCO metric is **sPRO/AUPRO** (pixel localization) — still missing (future work).

---

## 6. Competitive / literature context (for report + positioning)

Honest target after real DINOv2: ~0.85–0.92 image AUROC (GCAD/EfficientAD territory). **Do not** report a number beating SOTA — graders will assume leakage.

| Method | Venue | LOCO image AUROC | Code |
|---|---|---|---|
| SALAD | ICCV 2025 | 96.1% | github.com/MaticFuc/SALAD |
| CSAD | BMVC 2024 | 95.3% | github.com/Tokichan/CSAD |
| LA-EAD | 2025 | 94.2% | — |
| EfficientAD | WACV 2024 | ~90% | openvinotoolkit/anomalib · nelson1425/EfficientAD |
| AnomalyDINO | WACV 2025 | SOTA few-shot | github.com/dammsi/AnomalyDINO |
| GCAD (orig. LOCO paper) | IJCV 2022 | ~83% | defines sPRO metric |

Standout strategy = rigor + reproducibility + real methods + sPRO + an explainable dashboard + an honest SOTA-gap analysis (NOT chasing SALAD's accuracy). Resource: github.com/m-3lab/awesome-industrial-anomaly-detection.

---

## 7. How to regenerate the deliverables (commands)

From `Project_A_LOCO_AD/09_dashboard/`:
```bash
pip install scikit-learn pillow pandas numpy           # if needed
python build_dashboard.py        # recompute corrected metrics + dashboard_data.json
python generate_html.py          # rebuild dashboard.html (self-contained)
# report (needs Node + docx):
cd /tmp && npm install docx && cd -   # local docx install
node build_report.js             # rebuild Project_A_LOCO_Report.docx
```
The build scripts read the method score CSVs in `05_baselines/` and `06_method_results/`. **If those CSVs are regenerated with real DINOv2, just re-run the three scripts and everything updates automatically.**

Method-name honesty map lives at the top of `build_dashboard.py` (`SRC` dict + `FUSION_MAP`). If you switch to real backbones, update these names (e.g. "Patch-Stat Memory (NN)" → "DINOv2 Patch Memory") and remove the "handcrafted features" banner line in `generate_html.py`.

---

## 8. Remaining work (prioritized — from the roadmap)

**P0 — makes results real (do first):**
1. Run **real DINOv2** features: in `loco_project_utils.py`, call stage functions with `backend="dinov2"` (downloads `facebook/dinov2-small`); **remove the silent fallback** for the real run so it errors loudly if torch/transformers missing. Verify `feature_backend == dinov2-small` in the runtime CSVs.
2. **Cache features to disk** (extract once, reuse across all methods); **batch** the DINOv2 forward pass; **mask out letterbox padding** patches; **z-score / cosine** distance.
3. Differentiate PatchCore (run via **anomalib**, WideResNet50) from DINOv2 PatchMemory so they're no longer identical. Add **real EfficientAD** + **AnomalyDINO** baselines.

**P1 — comparability & rigor:**
4. Implement **sPRO/AUPRO** (anomalib AUPRO or official LOCO script) using the cleaned masks. Consider AUPIMO.
5. **Multi-seed** (3–5) → mean±std; Wilcoxon across categories.
6. **Ablations** (hold all else fixed): backbone (handcrafted vs WideResNet vs DINOv2-S/B), distance (euclid vs cosine), padding mask on/off, branch (local/global/fusion), k visual words, top-k aggregation.
7. Fix the sub-chance `splicing_connectors` logical result (likely padding/feature-scale artifact; should improve with real features).

**P2 — stretch (challenger novelty):**
8. **Component-aware head (CSAD-lite):** unsupervised component pseudo-labels (SAM/Grounding-DINO or DINOv2 KMeans) → component-count/composition features as a 3rd branch. Targets logical anomalies directly.
9. Cross-dataset generalization: MVTec AD, VisA, MPDD.

**Deliverable polish (optional, the user was deciding among these):**
- Polish dashboard (methods-explainer tab, sortable tables, speed-accuracy chart).
- Expand report to 5 pages (ablation section + per-category table + clearer SOTA gap).
- Build a faculty slide deck (pptx).

---

## 9. Real-DINOv2 Colab swap (condensed)

1. Colab GPU (T4). `pip install torch torchvision transformers scikit-learn pillow scipy pandas`.
2. Mount Drive; set `LAB_ROOT` to the project's parent (containing `Phase 1/` and `Project_A_LOCO_AD/`).
3. Run with real features:
```python
import loco_project_utils as L
L.run_stage05_patchcore(LAB_ROOT, backend="dinov2")
L.run_stage06_dinov2_patchmemory(LAB_ROOT, backend="dinov2")
L.run_stage07_gridaware(LAB_ROOT, backend="dinov2")
L.run_stage08_composition_histogram(LAB_ROOT, backend="dinov2")
L.run_stage09_fusion(LAB_ROOT)
L.run_stage10_final_tables(LAB_ROOT)
```
4. Confirm `feature_backend == dinov2-small` (NOT `fallback_*`) in any `*_runtime_memory.csv`.
5. Re-run the three build scripts in §7 to refresh dashboard + report with real numbers.

---

## 10. Conventions & gotchas
- Raw `Phase 1/` is read-only; all outputs go under `Project_A_LOCO_AD/`.
- Seeds fixed (Python/NumPy/Torch). Deterministic preprocessing; per-image resize metadata saved.
- CSV reads drop leading zeros from `sample_id` — use the `relative_path` column to locate image files (see `build_dashboard.py`).
- Only `breakfast_box` has saved anomaly heatmaps (first 250 scored images were that category); the dashboard gallery uses image+mask overlays for all 5 categories.
- The dashboard is fully self-contained (images base64-embedded); opens offline by double-click.

---

*Generated as a session handoff. Start by reading `ROADMAP_Project_A_LOCO_AD.md` and `PEER_REVIEW_Project_A_LOCO_AD.md` for full detail, then proceed with §8 P0 items.*
