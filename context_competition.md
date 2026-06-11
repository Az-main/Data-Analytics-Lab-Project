# Competition Sprint Context — written 2026-06-11 (Thursday)

This file captures the planning session of 2026-06-11 so work can continue on a
different machine. Read this **together with `context.md`** (the full project
continuation manual — repository layout, methods, metrics, defense Q&A).
This file is about the **department competition sprint**; `context.md` is about
the project as a whole. Where they disagree, this file is newer and wins.

---

## 1. Situation

- Faculty selected the project for the **department competition on Sunday 2026-06-14**.
- **Judges will review the GitHub repository and the dashboard.** There is no
  long live talk — repo polish and dashboard quality decide the outcome.
- Compute: **free-tier Colab T4** only. The new v2 pipeline was explicitly
  designed to fit free-tier sessions (GPU NN search + feature caching).
- Repo: `https://github.com/Az-main/Data-Analytics-Lab-Project`, branch `main`.
- Best v1 (current published) result: **Fusion (mean) 0.761 overall AUROC**
  (0.731 logical / 0.804 structural), real frozen DINOv2-small, single seed.

## 2. Strategy agreed in the session

1. **Do not compete on raw AUROC vs SOTA** (SALAD 96.1% / CSAD 95.3% — never
   claim to beat them). Compete on: honest engineering, a found-and-fixed-flaws
   story (v1 → v2), efficiency (frozen backbone, no task training, lightweight),
   and explainability (dashboard, per-branch evidence, failure analysis).
2. The **v1 → v2 before/after comparison is the centerpiece narrative**:
   "we code-reviewed our own pipeline, found 4 design flaws, fixed them,
   measured the gain with multiple seeds."
3. Keep every honesty rule from the peer review (see `context.md` §21/§25):
   no test-label tuning, validation-only thresholds/normalization, no claiming
   official PatchCore/EfficientAD reproductions, verify `feature_backend` in
   runtime logs before claiming DINOv2 results.

## 3. What was built on 2026-06-11 (already pushed, commit `1326be3`)

### `01_notebooks/loco_v2_improvements.py` — the v2 pipeline module

Fixes four v1 design flaws found by reading `loco_project_utils.py`:

| # | v1 flaw | v2 fix |
|---|---------|--------|
| 1 | Letterbox padding (20–50% of patch tokens; 50% for juice_bottle/splicing_connectors, 41% pushpins) was fed to DINOv2 | Content box cropped before extraction (boxes from `02_audit_reproducibility/resize_letterbox_metadata.csv`) |
| 2 | ONE memory bank (50k cap) shared by all 5 categories; ONE k-means vocabulary; composition histograms compared to a GLOBAL cross-category mean/covariance; fusion z-normalized with GLOBAL validation stats | Everything fitted **per category** (memory banks, vocabularies, histogram stats, fusion normalization). Evidence this matters: GridAware was the only per-category v1 branch and was the best single method |
| 3 | Features re-extracted 4× (once per stage); NN search on CPU while the GPU idled | Single-pass extraction into an on-disk cache; GPU (torch) nearest-neighbour search; makes **multi-seed** affordable on free Colab |
| 4 | "PatchCore" and "DINOv2 PatchMemory" were byte-identical duplicates | Differentiated: PatchCore-style = k=1 neighbour + top-1% aggregation; PatchMemory = k=3 mean distance + top-5% aggregation |

Key facts about the module:

- **Writes v1-compatible outputs** — same CSV paths, schemas and method-name
  strings (`PatchCore`, `DINOv2 PatchMemory`, `GridAware DINOv2`,
  `CompositionHistogram`, `Best Fusion`, `Fusion Max`, `Fusion RankAvg`), so
  `09_dashboard/feature_selection.py`, `build_dashboard.py`, `generate_html.py`
  and the report/slide builders work unchanged.
- Writes only 3 fusion variants (WeightedAvg dropped — it duplicated the mean,
  a peer-review finding).
- New artifacts: `06_method_results/Final_Evaluation/multiseed_summary.csv`
  (mean ± std per method × anomaly type) and `v2_run_config.json` (provenance:
  backbone, crop, seeds, per-category flags).
- Anomaly maps are saved per category (up to 25/category/method) and
  re-projected onto the full letterbox canvas so overlays align.
- `python loco_v2_improvements.py --selftest` — verifies NN math, crop
  geometry, per-category fusion and CSV schema with synthetic data, **no
  torch/GPU/dataset needed** (passed on the laptop 2026-06-11; note the
  laptop's local torch install is broken — DLL error — so the selftest used the
  numpy fallback; that's expected and fine).
- Entry point: `run_v2_pipeline(lab_root, model_size="small"|"base",
  img_size=336, seeds=[42,7,2026], cache_dir=..., limit_per_split=None)`.
  `seeds[0]` writes the canonical CSVs; all seeds feed the multiseed table.
  `limit_per_split=3` = smoke-test mode.

### `Run_DINOv2_Colab.ipynb` — reworked to drive v2

Cell flow: GPU check → deps → Drive mount → locate `Phase 1` → copy to local
disk → clone repo (falls back to asking for upload of BOTH
`loco_project_utils.py` + `loco_v2_improvements.py`) → **v2 config cell**
(`MODEL_SIZE`, `IMG_SIZE=336`, `SEEDS=[42,7,2026]`) → stage01 preprocessing →
stage04 EfficientAD proxy (kept as the global fusion branch) → **smoke test**
(`limit_per_split=3`, ~2–4 min, must pass before the full run) → **full v2 run**
(~25–50 min for small/3 seeds) → backend verification cell → optional 15b
PCA feature-dimension study → zip + Drive save + download.

## 4. The Colab run (the immediate next step)

1. Open `Run_DINOv2_Colab.ipynb` in Colab, Runtime → **T4 GPU**, **Run all**.
2. If the **smoke test** cell errors, stop and bring the error back to Claude.
3. The run produces **`loco_dinov2_results.zip`** (auto-saved to
   `MyDrive/loco_dinov2_results.zip` and downloaded). It contains
   `05_baselines/` + `06_method_results/` trees: score CSVs, per-category
   tables, runtime logs, anomaly maps, `multiseed_summary.csv`,
   `v2_run_config.json`.
4. **If the session survives**, set `MODEL_SIZE = "base"` in the config cell
   and re-run smoke → full run → packaging for the stronger backbone (~2–3×
   slower extraction). Whichever backbone wins becomes the headline.
   Rename/keep both zips if both complete (e.g. `loco_dinov2_results_base.zip`).
5. Honest target from these fixes: roughly **0.80–0.90 overall AUROC**
   (was 0.761). The sub-chance splicing_connectors-logical result will likely
   also normalize (suspected padding artifact). If numbers come back lower
   than v1 for some branch, report honestly and investigate — do not hide it.

## 5. After the results land (Friday plan)

Tell Claude: *"read context_competition.md — the v2 results are downloaded"*
and give the zip path. The steps Claude will run:

1. Unzip into the repo, overwriting `05_baselines/` and `06_method_results/`
   (keep a copy of the v1 CSVs first — e.g. `_v1_results_backup/` — they are
   needed for the v1-vs-v2 comparison table).
2. Regenerate deliverables **in this order** (deps matter):
   ```
   cd 09_dashboard
   python feature_selection.py
   python build_dashboard.py
   python generate_html.py
   cd ../07_paper_draft
   python build_product_report.py
   python slide_assets_build.py
   python build_presentation_v2.py
   python qa_presentation_v2.py     # 0 issues = pass
   ```
3. Add the **v1 → v2 comparison** (table + short narrative of the 4 flaws) to
   dashboard + report + README. Use mean ± std from `multiseed_summary.csv`.
4. **README overhaul** into a competition landing page: headline numbers,
   pipeline figure, v1→v2 story, how to reproduce, links to dashboard/report.
5. **GitHub Pages** so judges open the dashboard from a link
   (`dashboard.html` is self-contained offline HTML — serve it via Pages,
   e.g. `/docs` folder or a `gh-pages` branch).
6. Saturday: repo cleanup (commit/curate the uncommitted material below,
   remove `_trash/`, `README_old.md`), final commit, freeze, QA pass.

## 6. MACHINE-SHIFT WARNING — what is NOT on GitHub yet

A `git clone`/`pull` on the PC will **NOT** bring these (status as of
2026-06-11 on the laptop). Either commit+push them from the laptop first, or
copy the whole project folder (USB/Drive):

- Modified, uncommitted: `07_paper_draft/Project_A_LOCO_Presentation.pptx`,
  `07_paper_draft/build_product_report.py` (+ two report .docx files deleted
  locally but still in git).
- Untracked: `Project_A_LOCO_Presentation_v2.pptx` (the 22-slide deck),
  `Project_A_LOCO_Final_Academic_Report.docx`, `Project_A_LOCO_Report_Revised.docx`,
  `build_academic_report.py`, `build_presentation_v2.py`, `qa_presentation_v2.py`,
  `slide_assets_build.py`, `slide_assets/`, `academic_report_qa.json`,
  `figures/` additions, `overleaf/` + `LOCO_Overleaf_Report/` (+ .zip),
  `EDA_Questions_and_ML_DL_Relevance.docx`,
  `09_dashboard/LOCO_Anomaly_Inspector_PowerBI/`, `09_dashboard/Project Dashboard.pbix`,
  `LOCO_Anomaly_Inspector_Defense_Manual_with_Dashboard.docx`.
- `context.md` + this file are committed as of this session, so they DO transfer.
- The **dataset** (`Phase 1`, raw images) is not in git at all — it lives in
  Google Drive; Colab pulls it from there. The PC does not need it locally
  unless you want to re-run preprocessing locally.
- Claude's session memory lives on the laptop
  (`C:\Users\saman\.claude\...\memory\`) and will NOT follow to the PC —
  that is exactly why this file exists. On the PC, paste the starter prompt
  below into a fresh Claude Code session.

Also note: a teammate uploaded `09_dashboard/dashboard.html` via the GitHub web
UI on 2026-06-06 (commit `77d4d98`); it matched the local 2026-06-10 regen
except line endings, so nothing was lost. **Ask teammates not to upload via the
GitHub web UI until after the competition** — coordinate through commits.

## 7. Honesty rules (do not regress these)

- Thresholds and fusion normalization come from **validation/good only**.
- Never select the headline configuration using test labels. The pre-specified
  headline is **Fusion (mean)**; feature-selected variants are reported as
  analysis, not the headline.
- Call methods "PatchCore-style", "EfficientAD-inspired proxy" — not official
  reproductions.
- Verify `feature_backend` in the runtime CSVs starts with `dinov2` before
  claiming DINOv2 results (the notebook's verification cell does this).
- Never claim to beat SALAD (96.1%) or CSAD (95.3%).
- Multi-seed numbers are reported as mean ± std; single-seed results are
  labeled as such.

## 8. Deferred / stretch ideas (only if time remains before Sunday)

- **Component-counting head** (DINOv2 features → foreground clustering →
  per-category count statistics as an extra fusion branch) — targets the
  pushpins-logical near-chance failure; strongest novelty story, but risky
  this close to the deadline.
- **sPRO/AUPRO** — the official LOCO localization metric, still unreported
  (open peer-review finding #6). Mention as future work if not implemented.
- Live Streamlit/Gradio "upload → heatmap" demo — judges review repo +
  dashboard, so this is lower priority than originally planned.

## 9. Starter prompt for a fresh Claude session on the PC

```text
Read context_competition.md first, then context.md, README.md and git status.
This is the LOCO Anomaly Inspector project (MVTec LOCO AD, frozen DINOv2).
We are in a department-competition sprint: judges review the GitHub repo and
the dashboard on Sunday 2026-06-14. The v2 pipeline (loco_v2_improvements.py,
commit 1326be3) has been run on Colab; the results zip is at <PATH>.
Continue with section 5 of context_competition.md: back up v1 CSVs, unzip the
v2 results, regenerate feature selection -> dashboard -> report -> slides, add
the v1-vs-v2 comparison, overhaul README, set up GitHub Pages for the
dashboard. Keep every honesty rule in section 7. Do not revert teammate or
user work without inspection.
```
