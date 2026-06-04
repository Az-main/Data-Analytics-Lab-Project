# Project A — Full A-to-Z Roadmap to a Standout MVTec LOCO Logical Anomaly Detection Project

**Goal:** Take the current artifact (strong reproducibility scaffold, but all results from a 7-D fallback proxy, no dashboard, no report) to a **best-in-class, workshop-paper-grade, fully reproducible** logical anomaly detection project that genuinely challenges other student/lab projects.
**Assumptions used (change if wrong):** Colab-first compute (DINOv2-S/B, batched; CPU fallback noted); ambition = workshop-paper / portfolio grade; modular ~3–4 week timeline you can compress or extend.
**Date:** 2026-06-02

---

## Part I — The standout strategy (read this first)

You **will not** beat SALAD (96.1% AUROC, ICCV 2025) or CSAD (95.3%, BMVC 2024) on raw accuracy with a lightweight method, and you shouldn't try — those use foundation-model component segmentation (HQ-SAM, Grounding-DINO) and heavy three-branch training. Trying to out-accuracy them is the losing move every project makes.

**What actually makes a project stand out** (and what 95% of submissions lack):

1. **Methodological honesty + real methods.** Real DINOv2 / PatchCore / EfficientAD runs, not proxies. Most projects report one model's accuracy; you report a *controlled comparison* with the same backbone held constant.
2. **The official benchmark metric.** Report **sPRO / AUPRO** (pixel localization) alongside image-level AUROC. Almost no student project does this — it instantly signals you read the actual LOCO paper.
3. **A two-branch design with a defensible lightweight novelty.** GCAD, SALAD, CSAD all converge on the same insight: *logical anomalies need a global/composition branch; structural anomalies need a local branch.* Your "GridAware" + "CompositionHistogram" are already the seeds of this. Frame your contribution as **a lightweight, training-free, two-branch (local patch-memory + global composition-histogram) detector on frozen DINOv2, with validation-only fusion** — and prove with ablations where it beats/loses vanilla PatchCore.
4. **An interactive, explainable dashboard.** Not static PNGs — a live app that shows the anomaly score, the localization heatmap, AND the component/composition view, with per-category drill-down. This is the single most visible differentiator in a demo.
5. **A reproducibility package that's better than the papers'.** You already have hashing, leakage detection, letterbox metadata, env capture. Make it a named contribution.

**Your one-sentence positioning:** *"A lightweight, training-free, two-branch logical anomaly detector on frozen DINOv2 for MVTec LOCO — fully reproducible, benchmarked with the official sPRO metric against EfficientAD/PatchCore/AnomalyDINO, with an interactive explainability dashboard and an honest gap analysis to component-segmentation SOTA (CSAD/SALAD)."*

### Competitive landscape (what you're benchmarking against)
| Method | Venue | Image AUROC (LOCO) | Approach | Code | Your relation |
|---|---|---|---|---|---|
| **SALAD** | ICCV 2025 | **96.1%** | 3-branch (local/composition/global), object composition maps | MaticFuc/SALAD | Aspirational ceiling; cite as SOTA, don't chase |
| **CSAD** | BMVC 2024 | 95.3% | Unsupervised component seg (HQ-SAM+G-DINO) + patch histogram + LGST | Tokichan/CSAD | Your "stretch novelty" template (component-aware head) |
| **Few-shot Part Seg** | 2024 | 98.1% (logical) | Part segmentation reveals compositional logic | — | Confirms composition direction |
| **LA-EAD** | 2025 | 94.2% | EfficientAD + logical enhancements | — | Realistic upper-mid target if you go heavy |
| **SPACE** | WACV 2025 | high sPRO | Spatial consistency regularization | — | Best to cite for sPRO/localization |
| **EfficientAD** | WACV 2024 | ~90% | Student–teacher + AE, millisecond latency | anomalib / nelson1425 | **Your real structural-branch baseline** |
| **AnomalyDINO** | WACV 2025 | SOTA few-shot | Training-free DINOv2 cosine patch NN | dammsi/AnomalyDINO | **Your real DINOv2 backbone recipe** |
| **GCAD** | IJCV 2022 | ~83% | Global+local autoencoder; defines LOCO + sPRO | — | The origin baseline + metric source |
| **Your project (target)** | — | realistic 0.85–0.92 with real DINOv2 two-branch | Lightweight training-free two-branch + fusion | (this repo) | Challenger on rigor/reproducibility/explainability |

> Reality check on targets: with real DINOv2 features + proper two-branch fusion + sPRO, a realistic, honest result is **~0.85–0.92 image AUROC** — competitive with GCAD/EfficientAD, below CSAD/SALAD. That is an excellent, defensible outcome. Do **not** report a number that beats SALAD; reviewers and graders will assume leakage.

---

## Part II — Target system architecture

```
                          ┌─────────────────────────────────────────┐
                          │      Cleaned LOCO (letterbox 384²)        │
                          │   train/good · validation/good · test     │
                          └───────────────────┬───────────────────────┘
                                              │  frozen DINOv2-S/B patch tokens (cached)
                ┌──────────────────────────────┼──────────────────────────────┐
                ▼                              ▼                              ▼
   ┌────────────────────┐        ┌────────────────────────┐      ┌────────────────────────┐
   │  LOCAL branch       │        │  GLOBAL / COMPOSITION    │      │  (stretch) COMPONENT    │
   │  patch-memory NN    │        │  branch                  │      │  branch                 │
   │  (PatchCore-style,  │        │  visual-word histogram + │      │  pseudo-label component │
   │   coreset, cosine)  │        │  Mahalanobis / IsoForest │      │  seg (SAM/G-DINO-lite)  │
   │  → structural score │        │  → logical score         │      │  → component-count score│
   └─────────┬──────────┘        └────────────┬─────────────┘      └────────────┬───────────┘
             └──────────────────────┬──────────┴───────────────────────────────┘
                                    ▼  z-normalize on validation/good ONLY
                        ┌────────────────────────────┐
                        │  FUSION (validation-tuned)   │  → final image score + heatmap
                        └────────────┬─────────────────┘
                                     ▼
        ┌──────────────────────────────────────────────────────────────────┐
        │  EVALUATION: image AUROC + sPRO/AUPRO + AUPIMO, logical/structural  │
        │  split, multi-seed mean±std, Wilcoxon vs baselines                  │
        └──────────────────────────────────────────────────────────────────┘
                                     ▼
        ┌────────────────────┐   ┌────────────────────┐   ┌────────────────────┐
        │  Gradio dashboard   │   │  3–5 page report    │   │  Reproducibility pkg │
        │  (explainable demo) │   │  + paper figures    │   │  (README, env, zip)  │
        └────────────────────┘   └────────────────────┘   └────────────────────┘
```

---

## Part III — Phase-by-phase plan (A → Z)

Each phase: **Goal · Steps · Tools · Deliverables · Acceptance criteria · Est. effort.** Phases are ordered by dependency. P0/P1/P2 tags map to the priority from the peer review.

### PHASE 0 — Environment, repo hygiene & ground truth (P0) · ~0.5 day
**Goal:** A clean, version-pinned, GPU-ready base so every later number is reproducible and real.
**Steps:**
1. Create root `README.md` (run order, env setup, how to switch `backend="dinov2"`), `requirements.txt` (pinned), `.gitignore`, and a `LICENSE`/`CITATION.cff` referencing MVTec LOCO terms.
2. Initialize git; commit the existing audit/preprocessing outputs as the verified baseline.
3. On Colab: verify GPU (`nvidia-smi`), install `torch`, `transformers`, `anomalib>=1.0`, `scikit-learn`, `scipy`, `gradio`, `timm`. Re-run `pip freeze` from the **real** GPU env and commit it (the current freeze captured a torch-less env).
4. Confirm all **5 categories** are present in `03_cleaned_data` and re-run the leakage/hash audit once.
**Tools:** git, Colab, anomalib, transformers.
**Deliverables:** `README.md`, pinned `requirements.txt`, real `requirements_freeze.txt`, git history.
**Acceptance:** `python -c "import torch; print(torch.cuda.is_available())"` → `True`; all 5 categories audited, 0 leakage candidates.

### PHASE 1 — Real DINOv2 feature backbone + caching (P0) · ~1–1.5 days
**Goal:** Replace the 7-D fallback with real DINOv2 patch tokens, computed once and cached. *This is the fix that makes the whole project real.*
**Steps:**
1. Force `backend="dinov2"` in `extract_patch_features`; load `facebook/dinov2-base` (or `-small` if VRAM-limited) with `local_files_only=False` so weights download. **Remove the silent fallback** for the real run (raise loudly if DINOv2 fails).
2. **Batch** the forward pass (currently 1 image at a time, util line ~854) — process N images/batch on GPU.
3. **Mask out letterbox padding** patches (the zero borders) from both memory construction and scoring — they currently pollute every patch-distance computation.
4. **Cache features to disk** keyed by `image_hash + backbone_name` (e.g. `.npy` per image or a single memmap). All five methods then reuse one extraction pass instead of recomputing 5×.
5. Add **feature standardization** (per-dim z-score) and switch NN distance to **cosine** (AnomalyDINO's recipe), with Euclidean kept as an ablation.
**Tools:** transformers (DINOv2), numpy memmap / `torch.save`, sklearn.
**Deliverables:** `features/` cache, updated `loco_project_utils.py`, a `feature_extraction.ipynb` that reports `feature_backend == "dinov2-base"`.
**Acceptance:** every `*_scores.csv` shows `feature_backend = dinov2-*` (NOT `fallback_*`); extraction runs once and is reused; padding patches excluded (unit-checked).

### PHASE 2 — Real baselines via Anomalib (P0/P1) · ~2 days
**Goal:** Honest, citable baselines — fix the duplicate-method problem.
**Steps:**
1. Run **real PatchCore** and **real EfficientAD** through **anomalib** on all 5 categories (WideResNet50 backbone for PatchCore, PDN for EfficientAD). Export image AUROC + pixel AUPRO.
2. Run **AnomalyDINO** (dammsi/AnomalyDINO) as the training-free DINOv2 baseline.
3. Differentiate your in-house methods: "DINOv2 PatchMemory" must use **DINOv2 features**, "PatchCore" the **WideResNet** features — so they are no longer identical. (Current code makes them byte-identical; the peer review confirmed 1873/1873 matching scores.)
4. Add **coreset subsampling** (PatchCore-style greedy) instead of random 50k.
**Tools:** anomalib, AnomalyDINO repo, sklearn NearestNeighbors.
**Deliverables:** `05_baselines/` refreshed with real Anomalib outputs + AnomalyDINO; a baseline comparison CSV.
**Acceptance:** PatchCore ≠ DINOv2 PatchMemory (distinct score distributions); EfficientAD row backed by Anomalib logs, not the proxy; numbers within sane range of published values.

### PHASE 3 — The two-branch method + correct fusion (P1) · ~2 days
**Goal:** Your actual contribution — a lightweight two-branch detector.
**Steps:**
1. **Local branch** = region-conditioned patch memory (your existing `GridAware`, now on real DINOv2 + cosine + coreset) → structural-sensitive score.
2. **Global/composition branch** = visual-word histogram (MiniBatchKMeans on DINOv2 patches) + Mahalanobis, *actually combining* the cosine and IsolationForest scores you currently compute but discard (util line ~1616–1618) — select the combination on validation/good.
3. **Fusion** = z-normalize each branch on **validation/good only**, then average. **Fix the uniform-weight bug** (current "WeightedAvg" == plain average because weights are all-ones, line ~1743). Either learn weights on validation or drop the variant.
4. Produce a combined heatmap (local distance map + composition contribution) for the dashboard.
**Tools:** sklearn (KMeans, IsolationForest, covariance), numpy.
**Deliverables:** `06_method_results/TwoBranch/` with scores, config, heatmaps.
**Acceptance:** two-branch beats each single branch on validation; fusion variants are genuinely distinct; no test labels touched in any tuning.

### PHASE 4 — Correct evaluation: sPRO/AUPRO + leakage-free F1 + significance (P1) · ~1.5 days
**Goal:** Metrics that are comparable to the literature and free of the test-set threshold leak.
**Steps:**
1. **Implement sPRO / AUPRO** (pixel localization) using your cleaned masks — use `anomalib`'s AUPRO (TorchMetrics-based) or the official LOCO sPRO script. Consider **AUPIMO** (2024) as a modern fast localization metric for bonus rigor.
2. **Fix F1 threshold leakage:** select the threshold on `validation/good` (+ synthetic/validation anomalies), never on the test set (current `f1_max` sweeps thresholds on test, util line ~901/951).
3. **Multi-seed** (3–5 seeds) → report **mean ± std**; run **Wilcoxon signed-rank** across the 5 categories for method pairs.
4. Keep logical vs structural **reported separately** (you already do this — keep it).
5. Investigate the **sub-chance `splicing_connectors` logical** result (0.35–0.49) — likely a padding/feature-scale artifact that Phase 1–2 should fix.
**Tools:** anomalib metrics, scipy.stats (wilcoxon), sklearn.
**Deliverables:** `Final_Evaluation/` with image-AUROC + sPRO/AUPRO + AUPIMO tables, ±std, significance annotations.
**Acceptance:** sPRO reported for all categories; no metric is fit on test; splicing_connectors logical ≥ 0.5.

### PHASE 5 — Ablations & analysis (P1) · ~1.5 days
**Goal:** The controlled study that proves your design choices — the heart of a standout report.
**Required ablations (hold everything else fixed):**
- **Backbone:** handcrafted-7D (your old fallback!) vs WideResNet50 vs DINOv2-S vs DINOv2-B. *Your fallback becomes a legitimate ablation row, not the headline.*
- **Distance:** Euclidean vs cosine; raw vs standardized features.
- **Padding:** with vs without letterbox-border masking.
- **Branch:** local-only vs global-only vs two-branch fusion.
- **Aggregation:** top-1/top-5/top-10/mean/max (extend your existing one to real features).
- **k (visual words):** 16/32/64/128 (you have the scaffold).
**Deliverables:** `ablation_table.csv` + plots; a paragraph per ablation explaining the takeaway.
**Acceptance:** each design choice is justified by an ablation number, not asserted.

### PHASE 6 — Explainability & qualitative analysis (P1) · ~1 day
**Goal:** Make the model's reasoning visible — feeds both dashboard and report.
**Steps:**
1. Per-image: anomaly heatmap overlay (you have `save_patch_map`), composition-histogram bar vs normal mean, and (stretch) component map.
2. Curate true/false positive/negative cases per category (fix `selected_cases` to use the validation threshold, not test).
3. Write real failure analysis (the current `failure_case_notes.txt` is a placeholder telling the reader to "inspect" — replace with actual findings).
**Deliverables:** qualitative grids, per-category failure narrative.
**Acceptance:** at least one concrete, evidenced failure mode per category.

### PHASE 7 — Interactive dashboard (P0 deliverable) · ~2 days
**Goal:** The headline demo artifact — criterion #1.
**Spec (Gradio or Streamlit):**
- **Tab 1 — Detect:** upload/select image → anomaly score, predicted label at validation threshold, localization heatmap, composition view. Toggle method (PatchCore / EfficientAD / AnomalyDINO / Two-Branch).
- **Tab 2 — Relevant EDA (criterion #3):** per-category counts, mask-area distribution, spatial anomaly heatmap, edge-density boxplots — reuse `run_stage02_eda` figures; **drop EDA that doesn't inform the model** (e.g. raw intensity histograms if uninformative).
- **Tab 3 — Leaderboard:** corrected results table (image AUROC + sPRO, logical/structural), backbone clearly labeled, speed–accuracy plot.
- Persist fitted memory bank / KMeans / threshold so the app loads instantly (don't refit on launch).
**Tools:** gradio (simplest for ML demos) or streamlit.
**Deliverables:** `app.py` + a 60-sec screen-recording demo.
**Acceptance:** runs locally end-to-end on a fresh image in <2 s (cached models); all three tabs functional.

### PHASE 8 — The 3–5 page report + paper figures (P0 deliverable) · ~1.5 days
**Goal:** Criterion #4, written to peer-review standard.
**Outline (target 4 pages):**
1. Intro & problem (½ p) — logical vs structural; why LOCO is hard.
2. Data & preprocessing (½ p) — your audit/letterbox/leakage pipeline (your strongest material).
3. Methods (1 p) — two-branch design + fusion; one pipeline figure.
4. Results (1–1.5 p) — main table (AUROC + sPRO, logical/structural, ±std), speed–accuracy, one ablation, 2–3 qualitative cases.
5. Discussion & limitations (½ p) — honest gap to CSAD/SALAD, failure modes, compute.
6. Reproducibility (¼ p) — seeds, env, splits, sPRO.
**Tools:** the `docx` or `pdf` skill (I can generate this for you), matplotlib for figures.
**Deliverables:** `07_paper_draft/report.pdf` (or .docx) + finalized figures.
**Acceptance:** 3–5 pages, every claim backed by a table/figure, SOTA gap stated honestly.

### PHASE 9 — Packaging, polish & submission (P0) · ~0.5 day
**Goal:** A submission that looks like a research artifact.
**Steps:** refresh the manifest + zip export; final `README` with results table + dashboard GIF; tag a git release; checklist pass against the 4 criteria + the missing-baselines checklist from the peer review.
**Deliverables:** `08_exports/` zip, polished repo, demo video.
**Acceptance:** all 4 criteria ✅; a stranger can reproduce headline numbers from the README.

---

## Part IV — Stretch novelty (only if Phase 0–9 are done and time remains) · +1 week
**Component-aware head (CSAD-lite).** This is the path from "excellent course project" to "genuine challenger."
- Generate **unsupervised component pseudo-labels** from normal images using a foundation segmenter (HQ-SAM / Grounding-DINO as CSAD does, or a lighter DINOv2-feature KMeans over the *whole* object) → train a tiny segmentation head → build **component-count / component-composition** features.
- Add this as a third branch. This directly targets logical anomalies (missing/extra/swapped components) — the failure mode pure patch-distance misses.
- Honest expectation: this is what separates 0.88 from 0.93 on logical anomalies. High effort (foundation-model setup, GPU), so it's explicitly optional.
**Cross-dataset generalization** (cheaper stretch): run your two-branch detector on **MVTec AD** (structural sanity) and **VisA** or **MPDD** (multi-instance/layout) to show it generalizes — a table few projects include.

---

## Part V — Timeline (modular; compress for 1–2 wks, extend for 5+)

| Week | Phases | Outcome |
|---|---|---|
| **Week 1** | 0, 1, 2 | Real DINOv2 backbone + real Anomalib baselines (the P0 validity fix) |
| **Week 2** | 3, 4, 5 | Two-branch method + sPRO/leakage-free metrics + ablations |
| **Week 3** | 6, 7 | Explainability + interactive dashboard |
| **Week 4** | 8, 9 | Report + figures + packaging + demo video |
| **(+1 wk)** | Stretch | Component-aware head and/or cross-dataset |

**1–2 week crunch path:** Phase 0→1 (real backbone) → Phase 2 (just PatchCore+EfficientAD via Anomalib) → Phase 4 (sPRO + fix F1 leak) → Phase 7 (dashboard) → Phase 8 (report). Skip the two-branch novelty and most ablations; you still clear all 4 criteria with real methods.

---

## Part VI — Definition of "standout" (the grading-day checklist)
- [ ] Every result uses a **real** backbone (`feature_backend = dinov2-*` / Anomalib), zero `fallback_*` rows
- [ ] PatchCore ≠ DINOv2 PatchMemory; fusion variants genuinely distinct
- [ ] **sPRO/AUPRO** reported for all 5 categories, logical vs structural split
- [ ] No metric (F1/threshold) fit on the test set
- [ ] Multi-seed mean ± std + significance test
- [ ] Ablation table justifying backbone, distance, branches, padding
- [ ] **Interactive dashboard** with detect + EDA + leaderboard tabs (+ demo video)
- [ ] **3–5 page report** with honest SOTA gap to CSAD/SALAD
- [ ] Reproducibility package (README, pinned env, hashes, leakage audit, zip)
- [ ] (Stretch) component-aware branch and/or cross-dataset table

---

## Part VII — Tooling cheat-sheet
- **Backbone:** `transformers` DINOv2 (`facebook/dinov2-base`/`-small`); `timm` for WideResNet50.
- **Baselines/metrics:** `anomalib>=1.0` (PatchCore, EfficientAD, AUROC, AUPRO); official LOCO sPRO script; `AUPIMO`.
- **Modeling:** `scikit-learn` (NearestNeighbors, MiniBatchKMeans, IsolationForest, covariance), `scipy.stats` (wilcoxon).
- **Component stretch:** HQ-SAM, Grounding-DINO (per CSAD repo).
- **Dashboard:** `gradio` (fastest) or `streamlit`.
- **Report:** `docx`/`pdf` generation + `matplotlib`.
- **Resource:** the **awesome-industrial-anomaly-detection** list (M-3LAB) for the full method/paper/dataset index.

---

## Sources
- [SALAD — Semantics-Aware Logical AD, ICCV 2025 (96.1% AUROC)](https://arxiv.org/abs/2509.02101) · [code: MaticFuc/SALAD](https://github.com/MaticFuc/SALAD)
- [CSAD — Unsupervised Component Segmentation, BMVC 2024 (95.3%)](https://arxiv.org/abs/2408.15628) · [code: Tokichan/CSAD](https://github.com/Tokichan/CSAD)
- [EfficientAD, WACV 2024](https://openaccess.thecvf.com/content/WACV2024/papers/Batzner_EfficientAD_Accurate_Visual_Anomaly_Detection_at_Millisecond-Level_Latencies_WACV_2024_paper.pdf)
- [AnomalyDINO, WACV 2025](https://github.com/dammsi/AnomalyDINO)
- [SPACE — Spatial-aware Consistency, WACV 2025](https://openaccess.thecvf.com/content/WACV2025/papers/Kim_SPACE_SPAtial-Aware_Consistency_rEgularization_for_Anomaly_Detection_in_Industrial_Applications_WACV_2025_paper.pdf)
- [LA-EAD, 2025](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12389957/) · [Few-Shot Part Segmentation](https://arxiv.org/pdf/2312.13783)
- [GCAD / "Beyond Dents and Scratches", IJCV 2022](https://link.springer.com/article/10.1007/s11263-022-01578-9) · [MVTec LOCO dataset](https://www.mvtec.com/company/research/datasets/mvtec-loco)
- [anomalib (PatchCore/EfficientAD/AUPRO)](https://github.com/openvinotoolkit/anomalib) · [AUPIMO metric](https://arxiv.org/html/2401.01984v5)
- [awesome-industrial-anomaly-detection (paper/dataset index)](https://github.com/m-3lab/awesome-industrial-anomaly-detection)
