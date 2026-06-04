# Submission Guide — Project A (read this first)

You are submission-ready **right now** on the safe path. This guide covers (1) what to show your faculty, (2) how the 4 required criteria are met, (3) the optional parallel DINOv2 run, and (4) the one-command swap if it finishes.

---

## 1. What to hand in / demo

| Deliverable | File | How to use |
|---|---|---|
| **Dashboard** | `09_dashboard/dashboard.html` | **Double-click → opens in any browser.** No install, no internet, no server. This is your live demo. |
| **Report (3–5 pg)** | `07_paper_draft/Project_A_LOCO_Report.docx` (and `.pdf`) | 4-page technical report. PDF is print-ready. |
| **Corrected results** | `09_dashboard/corrected_main_results.csv`, `corrected_per_category.csv` | Honest numbers behind the dashboard/report. |
| Code & reproducibility | `01_notebooks/`, `02_audit_reproducibility/` | Show the audit/leakage/letterbox pipeline — your strongest material. |

**Demo script (2 minutes):** open `dashboard.html` → Overview (dataset + best score) → EDA tab (only decision-relevant plots) → Leaderboard (fusion beats single models) → Explainability (per-image red-mask decisions, ✓/✗) → Per-category drill-down. Then open the report PDF.

---

## 2. How the 4 criteria are met

1. **Dashboard** ✅ — `dashboard.html`, interactive, 5 tabs (Overview, EDA, Leaderboard, Explainability, Per-category).
2. **ML/DL model OR explainable analysis OR bucket creation** ✅ — four anomaly scorers (patch-memory NN, region-aware memory, k-means visual-words composition histogram, global detector) + validation-normalised fusion; explainability via per-image heatmaps and mask-overlay decisions.
3. **Only relevant EDA in dashboard** ✅ — EDA tab shows only model-relevant views (sample grid, mask overlays, normal mean/variance, spatial anomaly heatmap, mask-area, edge density). Raw/uninformative plots were left out.
4. **Short report, 3–5 pages** ✅ — 4-page report with abstract, data, methods, results table, limitations, references.

> **Honesty note (important for your defense):** the dashboard banner and report state plainly that results use **reproducible handcrafted features, not pretrained backbones**, and methods are named for what they actually do. If a faculty member asks "is this really PatchCore/DINOv2?", your answer is: *"No — these are honest handcrafted baselines; the DINOv2 upgrade path is documented in §5 of the report."* This transparency is a strength, not a weakness.

---

## 3. Optional: run REAL DINOv2 in parallel (Colab)

Only attempt this if you have spare time; the safe path already meets every requirement. If it works, your numbers jump toward GCAD/EfficientAD territory.

**Step 1 — open Colab with GPU.** Runtime → Change runtime type → T4 GPU.

**Step 2 — mount Drive & install.**
```python
from google.colab import drive; drive.mount('/content/drive')
!pip -q install torch torchvision transformers scikit-learn pillow scipy pandas
```

**Step 3 — point to your project & force the real backbone.** In each method notebook (04–10), set the global `LAB_ROOT` to your Drive path, then call the stage functions with `backend="dinov2"` instead of `"auto"`. In `loco_project_utils.py`, the function `extract_patch_features(..., backend="dinov2")` will download `facebook/dinov2-small` and use real patch tokens; if it raises, your GPU/transformers setup needs fixing (don't let it silently fall back).
```python
import loco_project_utils as L
# re-run the methods that feed the tables, with real features:
L.run_stage05_patchcore(LAB_ROOT, backend="dinov2")
L.run_stage06_dinov2_patchmemory(LAB_ROOT, backend="dinov2")
L.run_stage07_gridaware(LAB_ROOT, backend="dinov2")
L.run_stage08_composition_histogram(LAB_ROOT, backend="dinov2")
L.run_stage09_fusion(LAB_ROOT)
L.run_stage10_final_tables(LAB_ROOT)
```
**Step 4 — confirm it's real.** Open any `*_runtime_memory.csv` and check `feature_backend == dinov2-small` (NOT `fallback_*`). If it still says fallback, transformers/torch didn't load — fix that before trusting numbers.

> Tip: `run_stage05` (PatchCore) and `run_stage06` (DINOv2 PatchMemory) currently share one code path and give identical numbers. With real features they're still identical unless you give PatchCore a different backbone. For an honest two-method comparison, either run PatchCore via **anomalib** (WideResNet50) or present them as one method.

---

## 4. The one-command swap (if DINOv2 finishes)

The dashboard and report read straight from the method score CSVs. After the real run overwrites those CSVs, just regenerate both deliverables:

```bash
cd Project_A_LOCO_AD/09_dashboard
python build_dashboard.py      # recomputes corrected tables + rebuilds dashboard_data.json
python generate_html.py        # rebuilds dashboard.html with real numbers
node  build_report.js          # rebuilds the report with real numbers
```
Then (optional, 1-minute honesty edit) update the method-name map at the top of `build_dashboard.py` (e.g. `"Patch-Stat Memory (NN)" → "DINOv2 Patch Memory"`) and remove the "handcrafted features" banner line in `generate_html.py`, since results are now backbone-based.

Nothing else changes — same tables, same dashboard layout, same report structure, real numbers.

---

## 5. If anything breaks during the demo
- Dashboard won't open → it's a normal `.html`; right-click → Open with → your browser.
- Images missing in dashboard → they're embedded (base64); re-run `python build_dashboard.py && python generate_html.py`.
- Need the report as PDF → already provided: `07_paper_draft/Project_A_LOCO_Report.pdf`.
