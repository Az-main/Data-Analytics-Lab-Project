# Project A — MVTec LOCO Logical & Structural Anomaly Detection

Unsupervised industrial anomaly detection on **MVTec LOCO AD** (5 categories). Models train on defect-free images only and detect both **structural** defects (scratches/dents) and **logical** anomalies (missing/extra/misplaced parts). Includes a reproducible preprocessing+audit pipeline, four anomaly scorers + fusion, an interactive dashboard, and a 4-page report.

> **New here / continuing the project? Read [`CONTEXT.md`](CONTEXT.md) first** — it's the full handoff (plan, current state, results, remaining work).

## Quick links
- **Dashboard:** `09_dashboard/dashboard.html` — self-contained, double-click to open in any browser (offline, no install).
- **Report:** `07_paper_draft/Project_A_LOCO_Report.pdf` (and `.docx`).
- **Plan:** [`ROADMAP_Project_A_LOCO_AD.md`](ROADMAP_Project_A_LOCO_AD.md) · **Review:** [`PEER_REVIEW_Project_A_LOCO_AD.md`](PEER_REVIEW_Project_A_LOCO_AD.md) · **Submission:** [`SUBMISSION_GUIDE.md`](SUBMISSION_GUIDE.md)
- **Results:** `09_dashboard/corrected_main_results.csv`

## ⚠️ Data is NOT in this repo
The raw **MVTec LOCO AD** dataset and the cleaned/resized copy are intentionally excluded (size + license). To run the pipeline:
1. Download MVTec LOCO AD from the [official MVTec page](https://www.mvtec.com/company/research/datasets/mvtec-loco) into a sibling `Phase 1/` folder (read-only).
2. Regenerate the cleaned data: run `01_notebooks/01_preprocessing_reproducibility.ipynb` (calls `run_stage01_preprocessing`).
3. The dashboard and report work **without** the data (results are precomputed and embedded).

## Note on current results
Numbers were produced with a **reproducible handcrafted feature pipeline**, not pretrained backbones; method names reflect what each model actually computes. The DINOv2 upgrade path (the main next step) is documented in the report (§5) and `CONTEXT.md` (§8–§9).

## Regenerate deliverables
```bash
cd 09_dashboard
python build_dashboard.py && python generate_html.py   # dashboard
cd /tmp && npm install docx && cd -                     # one-time
node 09_dashboard/build_report.js                        # report
```
