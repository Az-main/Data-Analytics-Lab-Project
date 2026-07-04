#!/usr/bin/env python3
"""Build the competition-grade interactive HTML dashboard.

Reads v2 results + v1 backup + EDA images + anomaly maps, embeds everything
into a single self-contained offline HTML file with Chart.js visualizations.

Usage:
    python build_competition_dashboard.py
"""
import base64, io, json, glob, os, sys
from pathlib import Path
import numpy as np, pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
OUT  = ROOT / "09_dashboard"
V1   = ROOT / "_v1_results_backup"

CATS = ["breakfast_box","juice_bottle","pushpins","screw_bag","splicing_connectors"]
CAT_LABELS = {"breakfast_box":"Breakfast Box","juice_bottle":"Juice Bottle",
              "pushpins":"Pushpins","screw_bag":"Screw Bag",
              "splicing_connectors":"Splicing Connectors"}

def b64(path, max_w=820, q=82):
    try:
        im = Image.open(path).convert("RGB")
        if im.width > max_w:
            im = im.resize((max_w, int(im.height * max_w / im.width)))
        b = io.BytesIO(); im.save(b, "JPEG", quality=q)
        return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
    except Exception:
        return ""

def b64_png(path, max_w=400):
    try:
        im = Image.open(path).convert("RGBA")
        if im.width > max_w:
            im = im.resize((max_w, int(im.height * max_w / im.width)), Image.LANCZOS)
        b = io.BytesIO(); im.save(b, "PNG")
        return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()
    except Exception:
        return ""

# ── Load v2 results ──────────────────────────────────────────────────────────
v2_main = pd.read_csv(ROOT / "06_method_results/Final_Evaluation/main_results_table.csv")
v2_per  = pd.read_csv(ROOT / "06_method_results/Final_Evaluation/per_category_results_table.csv")
v2_ms   = pd.read_csv(ROOT / "06_method_results/Final_Evaluation/multiseed_summary.csv")
v2_cfg  = json.loads((ROOT / "06_method_results/Final_Evaluation/v2_run_config.json").read_text())
v2_eff  = pd.read_csv(ROOT / "06_method_results/Final_Evaluation/efficiency_table.csv")

# Feature dim study
v2_fdim = pd.read_csv(ROOT / "06_method_results/Final_Evaluation/feature_dim_selection_table.csv")

# Feature selection (branch-level)
fs_table = pd.read_csv(ROOT / "06_method_results/Final_Evaluation/feature_selection_table.csv") if \
    (ROOT / "06_method_results/Final_Evaluation/feature_selection_table.csv").exists() else None
fs_loo = pd.read_csv(ROOT / "06_method_results/Final_Evaluation/feature_importance_leave_one_out.csv") if \
    (ROOT / "06_method_results/Final_Evaluation/feature_importance_leave_one_out.csv").exists() else None

# ── Load v1 results ──────────────────────────────────────────────────────────
v1_main = pd.read_csv(V1 / "v1_corrected_main_results.csv") if (V1 / "v1_corrected_main_results.csv").exists() else None

# ── Build v1→v2 comparison ───────────────────────────────────────────────────
v1v2 = []
if v1_main is not None:
    v1_map = {
        "Fusion (mean)": "Best Fusion", "Fusion (max)": "Fusion Max",
        "Fusion (rank-avg)": "Fusion RankAvg",
        "DINOv2 Patch Memory (NN)": "PatchCore",
        "DINOv2 Region-Aware Memory": "GridAware DINOv2",
        "DINOv2 Composition Histogram (BoVW)": "CompositionHistogram",
        "Global Image-Stat Detector (proxy)": "EfficientAD",
    }
    for _, r1 in v1_main.iterrows():
        v2name = v1_map.get(r1["method"])
        if v2name:
            r2 = v2_main[v2_main.method == v2name]
            if len(r2):
                r2 = r2.iloc[0]
                v1v2.append({
                    "method": r1["method"], "v2name": v2name,
                    "v1_overall": round(float(r1["overall"]), 4),
                    "v2_overall": round(float(r2["overall"]), 4),
                    "v1_logical": round(float(r1["logical"]), 4),
                    "v2_logical": round(float(r2["logical"]), 4),
                    "v1_structural": round(float(r1["structural"]), 4),
                    "v2_structural": round(float(r2["structural"]), 4),
                    "gain_overall": round(float(r2["overall"]) - float(r1["overall"]), 4),
                    "gain_logical": round(float(r2["logical"]) - float(r1["logical"]), 4),
                    "gain_structural": round(float(r2["structural"]) - float(r1["structural"]), 4),
                })

# ── Load EDA images ──────────────────────────────────────────────────────────
eda_dir = ROOT / "04_probe_results"
if not eda_dir.exists():
    eda_dir = PARENT / "04_probe_results"
eda_imgs = {}
for name, fname in {
    "Dataset samples": "eda_sample_grid_cleaned.png",
    "Ground-truth mask overlays": "eda_mask_overlay_cleaned.png",
    "Normal mean & variance": "eda_mean_variance_cleaned.png",
    "Anomaly frequency heatmap": "eda_spatial_heatmap_cleaned.png",
    "Mask area distribution": "eda_mask_area_distribution.png",
    "Edge density": "eda_edge_density_cleaned.png",
}.items():
    p = eda_dir / fname
    if p.exists():
        eda_imgs[name] = b64(p, max_w=900)

# ── Load sample anomaly maps ─────────────────────────────────────────────────
map_dir = ROOT / "06_method_results/GridAware_DINOv2/gridaware_anomaly_maps"
anom_maps = {}
for cat in CATS:
    anom_maps[cat] = {}
    for defect, lbl in [("good","normal"),("logical_anomalies","logical"),("structural_anomalies","structural")]:
        cands = sorted(glob.glob(str(map_dir / f"{cat}_{defect}_*.png")))
        if not cands:
            cands = sorted(glob.glob(str(map_dir / f"{cat}_test_{defect}_*.png")))
        if cands:
            sel = cands[min(2, len(cands)-1)]
            anom_maps[cat][lbl] = b64_png(sel, max_w=300)

# ── Load pipeline figure ─────────────────────────────────────────────────────
pipe_fig = ""
pf = ROOT / "07_paper_draft/figures/figure_1_pipeline_overview.png"
if pf.exists():
    pipe_fig = b64(pf, max_w=900)

# ── Load dataset audit for counts ────────────────────────────────────────────
audit_csv = ROOT / "02_audit_reproducibility/product_image_count_summary.csv"
counts = []
if audit_csv.exists():
    audit = pd.read_csv(audit_csv)
    ct = audit.pivot_table(index="category", columns="split", values="count",
                           aggfunc="sum", fill_value=0).reset_index()
    counts = ct.to_dict(orient="records")

# ── Qualitative images ───────────────────────────────────────────────────────
qual_imgs = {}
qual_dir = ROOT / "06_method_results/Qualitative"
for name, fname in {
    "Success cases": "qualitative_success_cases.png",
    "Failure cases": "qualitative_failure_cases.png",
}.items():
    p = qual_dir / fname
    if p.exists():
        qual_imgs[name] = b64(p, max_w=900)

# ── Per-category for the v2 results (for radar charts) ───────────────────────
per_cat_v2 = []
for _, r in v2_per.iterrows():
    per_cat_v2.append({
        "method": r["method"], "category": r["category"],
        "anomaly_type": r["anomaly_type"],
        "auroc": round(float(r["auroc"]), 4),
        "f1_max": round(float(r["f1_max"]), 4) if "f1_max" in r and not pd.isna(r.get("f1_max")) else None,
    })

# ── Multiseed data ───────────────────────────────────────────────────────────
ms_data = []
for _, r in v2_ms.iterrows():
    ms_data.append({
        "method": r["method"], "anomaly_type": r["anomaly_type"],
        "mean": round(float(r["mean_auroc"]), 4),
        "std": round(float(r["std_auroc"]), 4),
    })

# ── Assemble DATA payload ────────────────────────────────────────────────────
DATA = {
    "v2_main": v2_main.round(4).to_dict(orient="records"),
    "v2_per": per_cat_v2,
    "v1v2": v1v2,
    "multiseed": ms_data,
    "v2_config": v2_cfg,
    "eda": eda_imgs,
    "anomaly_maps": anom_maps,
    "pipeline_fig": pipe_fig,
    "counts": counts,
    "cats": CATS,
    "cat_labels": CAT_LABELS,
    "qualitative": qual_imgs,
    "feature_dim": v2_fdim.round(4).to_dict(orient="records") if v2_fdim is not None else [],
    "feature_sel": fs_table.round(4).to_dict(orient="records") if fs_table is not None else [],
    "feature_loo": fs_loo.round(4).to_dict(orient="records") if fs_loo is not None else [],
    "efficiency": v2_eff.round(4).to_dict(orient="records") if v2_eff is not None else [],
}

DATA_JSON = json.dumps(DATA)
print(f"DATA payload: {len(DATA_JSON)/1e6:.2f} MB")
print(f"  EDA images: {len(eda_imgs)}")
print(f"  Anomaly maps: {sum(len(v) for v in anom_maps.values())}")
print(f"  Pipeline figure: {'yes' if pipe_fig else 'no'}")
print(f"  Qualitative: {len(qual_imgs)}")
print(f"  v1v2 comparisons: {len(v1v2)}")

# ── HTML Template ─────────────────────────────────────────────────────────────
HTML = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LOCO Anomaly Inspector — Competition Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#0a0e1a;--bg2:#111628;--card:#161c35;--card2:#1c2340;--card3:#222a4a;
  --ink:#e4e8f7;--ink2:#c0c8e0;--muted:#7e89b0;--border:#2a3155;
  --accent:#6c8cff;--accent2:#4a6aff;--good:#34d399;--good2:#10b981;
  --bad:#f87171;--warn:#fbbf24;--purple:#a78bfa;--pink:#f472b6;
  --teal:#2dd4bf;--orange:#fb923c;
  --glass:rgba(22,28,53,0.85);--glow:rgba(108,140,255,0.15);
  --radius:12px;--radius-lg:16px;
}}
html{{scroll-behavior:smooth}}
body{{font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  background:var(--bg);color:var(--ink);line-height:1.6;overflow-x:hidden}}
a{{color:var(--accent);text-decoration:none}}

/* ── Scroll reveal animations ─────────────────────────────────────────── */
.reveal{{opacity:0;transform:translateY(30px);transition:opacity 0.7s ease,transform 0.7s ease}}
.reveal.visible{{opacity:1;transform:translateY(0)}}
.reveal-left{{opacity:0;transform:translateX(-40px);transition:opacity 0.6s ease,transform 0.6s ease}}
.reveal-left.visible{{opacity:1;transform:translateX(0)}}
.reveal-right{{opacity:0;transform:translateX(40px);transition:opacity 0.6s ease,transform 0.6s ease}}
.reveal-right.visible{{opacity:1;transform:translateX(0)}}
.reveal-scale{{opacity:0;transform:scale(0.92);transition:opacity 0.5s ease,transform 0.5s ease}}
.reveal-scale.visible{{opacity:1;transform:scale(1)}}

/* ── Hero ──────────────────────────────────────────────────────────────── */
.hero{{position:relative;padding:80px 40px 60px;text-align:center;
  background:linear-gradient(135deg,#0f1631 0%,#1a1f4a 40%,#2a1a4a 100%);
  border-bottom:1px solid var(--border);overflow:hidden}}
.hero::before{{content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;
  background:radial-gradient(circle at 60% 40%,rgba(108,140,255,0.1) 0%,transparent 50%);
  animation:heroPulse 8s ease-in-out infinite alternate}}
@keyframes heroPulse{{0%{{opacity:.6;transform:scale(1)}}100%{{opacity:1;transform:scale(1.05)}}}}
.hero-particles{{position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none}}
.hero h1{{font-size:clamp(28px,5vw,42px);font-weight:800;letter-spacing:-0.5px;
  background:linear-gradient(135deg,#e4e8f7 30%,#6c8cff 70%);-webkit-background-clip:text;
  -webkit-text-fill-color:transparent;position:relative;margin-bottom:4px}}
.hero .tagline{{font-size:16px;color:var(--accent);font-weight:600;position:relative;
  margin-bottom:4px;letter-spacing:0.5px}}
.hero .sub{{color:var(--muted);font-size:14px;margin:4px 0 32px;position:relative}}
.kpis{{display:flex;gap:16px;justify-content:center;flex-wrap:wrap;position:relative}}
.kpi-card{{background:var(--glass);backdrop-filter:blur(12px);border:1px solid var(--border);
  border-radius:var(--radius);padding:20px 28px;min-width:150px;text-align:center;
  transition:transform .3s cubic-bezier(.4,0,.2,1),border-color .3s,box-shadow .3s}}
.kpi-card:hover{{transform:translateY(-5px);border-color:var(--accent);
  box-shadow:0 8px 30px rgba(108,140,255,0.15)}}
.kpi-label{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:1.2px;font-weight:600}}
.kpi-value{{font-size:34px;font-weight:800;margin:6px 0;
  background:linear-gradient(135deg,var(--ink),var(--accent));-webkit-background-clip:text;
  -webkit-text-fill-color:transparent}}
.kpi-delta{{font-size:12px;font-weight:600}}
.kpi-delta.up{{color:var(--good)}}

/* ── Sidebar ──────────────────────────────────────────────────────────── */
nav.sidebar{{position:fixed;left:0;top:0;width:220px;height:100vh;background:var(--bg2);
  border-right:1px solid var(--border);padding:20px 0;z-index:100;overflow-y:auto;
  transition:transform .3s}}
nav.sidebar .logo{{padding:16px 20px;font-size:15px;font-weight:800;
  background:linear-gradient(135deg,var(--accent),var(--teal));-webkit-background-clip:text;
  -webkit-text-fill-color:transparent;border-bottom:1px solid var(--border);margin-bottom:12px}}
nav.sidebar .scroll-progress{{height:2px;background:var(--accent);width:0%;
  transition:width 0.15s;margin:0 20px 8px}}
nav.sidebar a{{display:flex;align-items:center;gap:10px;padding:10px 20px;font-size:13px;
  color:var(--muted);transition:all .25s;border-left:3px solid transparent}}
nav.sidebar a:hover,nav.sidebar a.active{{color:var(--ink);background:rgba(108,140,255,0.08);
  border-left-color:var(--accent)}}
nav.sidebar a.active .num{{background:var(--accent);color:#fff}}
nav.sidebar a .num{{font-size:11px;background:var(--card3);padding:2px 6px;border-radius:4px;
  min-width:20px;text-align:center;transition:all .25s;font-weight:600}}

/* ── Main ─────────────────────────────────────────────────────────────── */
.main{{margin-left:220px}}
section{{padding:60px 48px;border-bottom:1px solid var(--border)}}
section:last-child{{border-bottom:none}}
h2{{font-size:26px;font-weight:800;margin-bottom:8px;letter-spacing:-0.3px}}
h2 .badge{{font-size:11px;background:linear-gradient(135deg,var(--accent),var(--purple));
  color:#fff;padding:4px 12px;border-radius:20px;vertical-align:middle;margin-left:10px;
  font-weight:700;letter-spacing:0.5px;text-transform:uppercase}}
.section-sub{{color:var(--muted);font-size:14px;margin-bottom:32px;max-width:720px}}
h3{{font-size:16px;font-weight:700;margin-bottom:12px;color:var(--ink2)}}

/* ── Cards ─────────────────────────────────────────────────────────────── */
.card{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius-lg);
  padding:24px;transition:border-color .3s,box-shadow .3s}}
.card:hover{{border-color:rgba(108,140,255,0.3);box-shadow:0 4px 20px rgba(0,0,0,0.2)}}
.card-glow{{position:relative;overflow:hidden}}
.card-glow::after{{content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;
  background:radial-gradient(circle at var(--mouse-x,50%) var(--mouse-y,50%),
  rgba(108,140,255,0.06) 0%,transparent 50%);pointer-events:none;opacity:0;
  transition:opacity .3s}}
.card-glow:hover::after{{opacity:1}}
.grid{{display:grid;gap:20px}}
.g2{{grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}}
.g3{{grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}}
.g4{{grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}}

/* ── Tables ────────────────────────────────────────────────────────────── */
table{{width:100%;border-collapse:collapse;font-size:13px}}
thead th{{color:var(--muted);font-weight:700;text-transform:uppercase;font-size:11px;
  letter-spacing:0.6px;padding:10px 12px;border-bottom:2px solid var(--border);
  text-align:right;cursor:pointer;user-select:none;white-space:nowrap}}
thead th:first-child{{text-align:left}}
tbody td{{padding:10px 12px;border-bottom:1px solid rgba(42,49,85,0.5);text-align:right}}
tbody td:first-child{{text-align:left;font-weight:600}}
tbody tr{{transition:background .15s}}
tbody tr:hover{{background:rgba(108,140,255,0.06)}}
.highlight-row{{background:rgba(52,211,153,0.08) !important}}
.highlight-row td:first-child{{color:var(--good)}}

.pill{{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700}}
.pill-good{{background:rgba(52,211,153,0.15);color:var(--good)}}
.pill-bad{{background:rgba(248,113,113,0.15);color:var(--bad)}}

/* ── Flaw cards ────────────────────────────────────────────────────────── */
.flaw-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}}
.flaw-card{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius-lg);
  padding:24px 20px;position:relative;overflow:hidden;
  transition:transform .3s,box-shadow .3s}}
.flaw-card:hover{{transform:translateY(-3px);box-shadow:0 8px 24px rgba(0,0,0,0.3)}}
.flaw-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;
  background:linear-gradient(90deg,var(--bad),var(--warn),var(--good))}}
.flaw-num{{font-size:36px;font-weight:900;
  background:linear-gradient(135deg,rgba(108,140,255,0.15),rgba(167,139,250,0.15));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  position:absolute;top:8px;right:16px}}
.flaw-card h4{{font-size:14px;margin-bottom:12px;color:var(--ink);font-weight:700;padding-right:30px}}
.flaw-v1{{font-size:12px;color:var(--bad);margin-bottom:6px;padding:6px 10px;
  background:rgba(248,113,113,0.06);border-radius:6px;line-height:1.5}}
.flaw-v2{{font-size:12px;color:var(--good);padding:6px 10px;
  background:rgba(52,211,153,0.06);border-radius:6px;line-height:1.5}}

/* ── Toggle buttons ───────────────────────────────────────────────────── */
.toggle-group{{display:flex;gap:4px;background:var(--card);border:1px solid var(--border);
  border-radius:10px;padding:3px;margin-bottom:20px;width:fit-content}}
.toggle-btn{{padding:8px 18px;border-radius:8px;border:none;background:transparent;
  color:var(--muted);cursor:pointer;font-size:13px;font-weight:600;
  transition:all .25s cubic-bezier(.4,0,.2,1)}}
.toggle-btn.active{{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;
  box-shadow:0 2px 10px rgba(108,140,255,0.3)}}

.chart-box{{position:relative;height:320px;margin-top:16px}}
.chart-box.tall{{height:420px}}

img.eda{{max-width:100%;border-radius:var(--radius);display:block;transition:transform .3s}}
img.eda:hover{{transform:scale(1.02)}}

/* ── Category pills ───────────────────────────────────────────────────── */
.cat-pills{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px}}
.cat-pill{{padding:8px 18px;border-radius:10px;border:1px solid var(--border);
  background:var(--card);color:var(--muted);cursor:pointer;font-size:13px;
  font-weight:600;transition:all .25s}}
.cat-pill:hover{{border-color:var(--accent);color:var(--ink)}}
.cat-pill.active{{background:linear-gradient(135deg,var(--accent),var(--accent2));
  border-color:var(--accent);color:#fff;box-shadow:0 2px 10px rgba(108,140,255,0.3)}}

.map-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}
.map-grid img{{width:100%;border-radius:8px;border:1px solid var(--border);
  transition:transform .3s,border-color .3s}}
.map-grid img:hover{{transform:scale(1.05);border-color:var(--accent)}}
.map-label{{font-size:11px;color:var(--muted);text-align:center;margin-top:4px;font-weight:600}}

/* ── Insight cards ────────────────────────────────────────────────────── */
.insight-card{{background:var(--card);border-left:3px solid var(--accent);
  border-radius:0 var(--radius) var(--radius) 0;padding:18px 22px;margin-bottom:12px;
  transition:border-color .3s,transform .2s}}
.insight-card:hover{{border-left-color:var(--good);transform:translateX(4px)}}
.insight-card h3{{font-size:14px;margin-bottom:6px;color:var(--ink)}}
.insight-card p{{font-size:13px;color:var(--ink2);line-height:1.7}}

/* ── Pipeline steps ───────────────────────────────────────────────────── */
.step-line{{display:flex;align-items:stretch;gap:0;margin:20px 0}}
.step{{flex:1;text-align:center;padding:18px 10px;background:var(--card);
  border:1px solid var(--border);position:relative;font-size:12px;color:var(--ink2);
  transition:background .3s}}
.step:hover{{background:var(--card2)}}
.step:first-child{{border-radius:var(--radius) 0 0 var(--radius)}}
.step:last-child{{border-radius:0 var(--radius) var(--radius) 0}}
.step .step-title{{font-size:13px;font-weight:700;color:var(--ink);margin-bottom:4px}}
.step .step-icon{{font-size:26px;margin-bottom:8px;display:block}}
.step::after{{content:'\\2192';position:absolute;right:-12px;top:50%;transform:translateY(-50%);
  font-size:18px;color:var(--accent);z-index:1;font-weight:700}}
.step:last-child::after{{display:none}}

/* ── Compare bars ─────────────────────────────────────────────────────── */
.compare-bar{{display:flex;align-items:center;gap:12px;margin-bottom:10px}}
.compare-label{{width:180px;font-size:13px;color:var(--ink2);text-align:right;font-weight:500}}
.compare-track{{flex:1;height:26px;background:var(--card3);border-radius:8px;
  position:relative;overflow:hidden}}
.compare-fill{{height:100%;border-radius:8px;display:flex;align-items:center;padding-left:10px;
  font-size:11px;font-weight:700;color:#fff;transition:width 1s cubic-bezier(.4,0,.2,1)}}
.v1-fill{{background:rgba(108,140,255,0.35)}}
.v2-fill{{background:linear-gradient(90deg,var(--accent),var(--good));
  box-shadow:0 0 12px rgba(52,211,153,0.2)}}

/* ── Efficiency cards ─────────────────────────────────────────────────── */
.stat-row{{display:flex;gap:12px;margin-top:16px;flex-wrap:wrap}}
.stat-chip{{background:var(--card3);border-radius:8px;padding:10px 16px;
  display:flex;flex-direction:column;align-items:center;min-width:100px}}
.stat-chip .stat-val{{font-size:20px;font-weight:800;color:var(--accent)}}
.stat-chip .stat-lbl{{font-size:10px;color:var(--muted);text-transform:uppercase;
  letter-spacing:0.5px;margin-top:2px}}

footer{{padding:30px 48px;margin-left:220px;text-align:center;color:var(--muted);
  font-size:12px;border-top:1px solid var(--border)}}

/* ── Mobile ───────────────────────────────────────────────────────────── */
@media(max-width:900px){{
  nav.sidebar{{transform:translateX(-100%)}}
  .main{{margin-left:0}}
  section{{padding:30px 20px}}
  .hero{{padding:50px 20px 40px}}
  footer{{margin-left:0;padding:20px}}
  .step-line{{flex-wrap:wrap}}
  .step{{flex:1 1 45%}}
  .step::after{{display:none}}
}}
</style>
</head>
<body>

<nav class="sidebar" id="sidebar">
  <div class="logo">LOCO Inspector</div>
  <div class="scroll-progress" id="scroll-progress"></div>
  <a href="#hero" class="active"><span class="num">0</span> Overview</a>
  <a href="#approach"><span class="num">1</span> Our approach</a>
  <a href="#flaws"><span class="num">2</span> Flaws found</a>
  <a href="#v1v2"><span class="num">3</span> v1 vs v2</a>
  <a href="#leaderboard"><span class="num">4</span> Leaderboard</a>
  <a href="#category"><span class="num">5</span> Per-category</a>
  <a href="#features"><span class="num">6</span> Feature selection</a>
  <a href="#eda"><span class="num">7</span> EDA</a>
  <a href="#explainability"><span class="num">8</span> Explainability</a>
  <a href="#insights"><span class="num">9</span> Insights</a>
</nav>

<div class="main">

<!-- HERO -->
<div class="hero" id="hero">
  <canvas class="hero-particles" id="particles"></canvas>
  <h1>LOCO Anomaly Inspector</h1>
  <div class="tagline">Unsupervised Anomaly Detection with Frozen DINOv2</div>
  <div class="sub">MVTec LOCO AD &middot; 5 categories &middot; No task training &middot; Free-tier Colab T4 &middot; Multi-seed evaluation</div>
  <div class="kpis" id="hero-kpis"></div>
</div>

<!-- 1. OUR APPROACH -->
<section id="approach" class="reveal">
  <h2>Our approach <span class="badge">Pipeline</span></h2>
  <p class="section-sub">A multi-branch anomaly detection system built on frozen self-supervised DINOv2 patch features. No neural network training on anomaly data &mdash; only normal images are used.</p>
  <div class="step-line" id="pipeline-steps"></div>
  <div class="grid g2" style="margin-top:24px">
    <div class="card">
      <h3>Why DINOv2?</h3>
      <p style="font-size:13px;color:var(--ink2)">DINOv2 is a self-supervised Vision Transformer that learns rich visual representations without labels. Its patch tokens capture semantics, shapes, and spatial relationships &mdash; exactly what anomaly detection needs. We freeze the backbone and build lightweight scoring on top, making the system fast, reproducible, and deployable on free-tier hardware.</p>
    </div>
    <div class="card">
      <h3>Detection branches</h3>
      <ul style="font-size:13px;color:var(--ink2);padding-left:18px;list-style:none">
        <li style="margin-bottom:6px"><span style="color:var(--accent)">&#9632;</span> <b>PatchCore-style</b> &mdash; k=1 nearest neighbour, top-1% aggregation (structural defects)</li>
        <li style="margin-bottom:6px"><span style="color:var(--purple)">&#9632;</span> <b>Patch Memory</b> &mdash; k=3 mean distance, top-5% aggregation (broader coverage)</li>
        <li style="margin-bottom:6px"><span style="color:var(--teal)">&#9632;</span> <b>Region-Aware</b> &mdash; spatially constrained patch comparison (layout-sensitive)</li>
        <li style="margin-bottom:6px"><span style="color:var(--orange)">&#9632;</span> <b>Composition Histogram</b> &mdash; bag-of-visual-words distribution (global composition)</li>
        <li><span style="color:var(--muted)">&#9632;</span> <b>EfficientAD proxy</b> &mdash; lightweight image-stat baseline (non-DINOv2)</li>
      </ul>
    </div>
  </div>
  <div class="card" style="margin-top:20px" id="pipeline-fig-container"></div>
</section>

<!-- 2. FLAWS FOUND -->
<section id="flaws" class="reveal">
  <h2>The 4 flaws we found <span class="badge">v1 &rarr; v2</span></h2>
  <p class="section-sub">We code-reviewed our own pipeline and found four design flaws. Each was fixed in v2, producing measurable gains. This honest self-improvement story is the centerpiece of our work.</p>
  <div class="flaw-grid" id="flaw-cards"></div>
</section>

<!-- 3. V1 VS V2 -->
<section id="v1v2" class="reveal">
  <h2>Before &amp; after <span class="badge">Impact</span></h2>
  <p class="section-sub">The combined effect of fixing all four flaws. Every method improved &mdash; some dramatically.</p>
  <div class="toggle-group" id="v1v2-toggle"></div>
  <div class="card"><div class="chart-box tall"><canvas id="v1v2Chart"></canvas></div></div>
  <div style="margin-top:20px" id="v1v2-bars"></div>
</section>

<!-- 4. LEADERBOARD -->
<section id="leaderboard" class="reveal">
  <h2>Results leaderboard <span class="badge">v2</span></h2>
  <p class="section-sub">All methods evaluated on the held-out test set. Thresholds derived from validation/good only &mdash; no test-label tuning. Multi-seed mean &plusmn; std across 3 seeds.</p>
  <div class="toggle-group" id="lb-toggle"></div>
  <div class="card"><div class="chart-box"><canvas id="lbChart"></canvas></div></div>
  <div class="card" style="margin-top:20px" id="lb-table"></div>
</section>

<!-- 5. PER-CATEGORY -->
<section id="category" class="reveal">
  <h2>Per-category analysis <span class="badge">Deep dive</span></h2>
  <p class="section-sub">Performance varies sharply across categories. Select a category to explore its strengths and weaknesses.</p>
  <div class="cat-pills" id="cat-pills"></div>
  <div class="grid g2">
    <div class="card"><h3>AUROC by method</h3><div class="chart-box"><canvas id="catChart"></canvas></div></div>
    <div class="card"><h3>Anomaly maps</h3><div id="cat-maps"></div></div>
  </div>
  <div class="card" style="margin-top:20px" id="cat-table"></div>
</section>

<!-- 6. FEATURE SELECTION -->
<section id="features" class="reveal">
  <h2>Feature selection <span class="badge">Criterion 4</span></h2>
  <p class="section-sub">Not all branches help. Leave-one-out analysis reveals which representations improve or hurt fusion.</p>
  <div class="grid g2">
    <div class="card"><h3>Branch importance (leave-one-out)</h3><div class="chart-box"><canvas id="looChart"></canvas></div></div>
    <div class="card"><h3>Feature dimension study (PCA)</h3><div class="chart-box"><canvas id="dimChart"></canvas></div></div>
  </div>
  <div class="card" style="margin-top:20px" id="fs-table"></div>
</section>

<!-- 7. EDA -->
<section id="eda" class="reveal">
  <h2>Exploratory data analysis <span class="badge">EDA</span></h2>
  <p class="section-sub">The MVTec LOCO AD dataset: 5 categories, 3644 images, structural and logical anomaly types.</p>
  <div class="grid g2" id="eda-gallery"></div>
</section>

<!-- 8. EXPLAINABILITY -->
<section id="explainability" class="reveal">
  <h2>Explainability <span class="badge">Visual evidence</span></h2>
  <p class="section-sub">Anomaly heatmaps show where the model thinks defects are. Compare model predictions against ground-truth masks.</p>
  <div class="grid g2" id="qual-gallery"></div>
</section>

<!-- 9. INSIGHTS -->
<section id="insights" class="reveal">
  <h2>Key insights &amp; limitations <span class="badge">Honest</span></h2>
  <p class="section-sub">What we learned, what works, and where the approach falls short.</p>
  <div id="insight-cards"></div>
  <div class="card" style="margin-top:20px">
    <h3>Comparison with published methods</h3>
    <table>
      <thead><tr><th style="text-align:left">Method</th><th>Overall AUROC</th><th>Approach</th><th>Training?</th></tr></thead>
      <tbody>
        <tr><td>SALAD (ICCV 2025)</td><td>96.1%</td><td>EfficientAD + SAM composition maps</td><td>Yes (discriminative)</td></tr>
        <tr><td>CSAD (BMVC 2024)</td><td>95.3%</td><td>Component segmentation + LGST</td><td>Yes (student-teacher)</td></tr>
        <tr><td>EfficientAD (WACV 2024)</td><td>~90%</td><td>PDN student-teacher + autoencoder</td><td>Yes (lightweight)</td></tr>
        <tr class="highlight-row"><td><b>Ours &mdash; Fusion Max (v2)</b></td><td><b>82.7%</b></td><td>Frozen DINOv2 multi-branch fusion</td><td><b>No training</b></td></tr>
        <tr><td>PatchCore (CVPR 2022)</td><td>~82%</td><td>WRN-101 memory bank + coreset</td><td>No training</td></tr>
      </tbody>
    </table>
    <p style="font-size:12px;color:var(--muted);margin-top:10px">Our approach is competitive with PatchCore while using a smaller backbone (DINOv2-small, 384-dim vs 1024-dim) and running entirely on free-tier Colab T4. Methods above 90% use task-specific training and heavier compute.</p>
  </div>
</section>

</div>

<footer>
  LOCO Anomaly Inspector &mdash; Data Analytics Lab, Spring 2026 &middot;
  <a href="https://github.com/Az-main/Data-Analytics-Lab-Project" target="_blank">GitHub Repository</a>
  &middot; Built with frozen DINOv2 &middot; No test-label tuning
</footer>

<script>
const D = {DATA_JSON};
const pct = x => x == null ? '—' : (x*100).toFixed(1)+'%';
const f3 = x => x == null ? '—' : x.toFixed(3);
const f1 = x => x == null ? '—' : (x*100).toFixed(1);

// ── HERO KPIs ───────────────────────────────────────────────────────────────
(function(){{
  const best = D.v2_main.reduce((a,b) => b.overall > a.overall ? b : a);
  const v1best = D.v1v2.length ? D.v1v2.reduce((a,b) => b.v1_overall > a.v1_overall ? b : a) : null;
  const kpis = [
    {{label:'Best overall',value:pct(best.overall),delta:'+'+((best.overall-(v1best?v1best.v1_overall:0))*100).toFixed(1)+'pp vs v1',method:best.method}},
    {{label:'Logical AUROC',value:pct(best.logical),delta:''}},
    {{label:'Structural AUROC',value:pct(best.structural),delta:best.structural>0.9?'Above 90%':''}},
    {{label:'Seeds',value:D.v2_config.seeds.length,delta:'mean \\u00b1 std'}},
    {{label:'Categories',value:D.cats.length,delta:'3644 images'}},
    {{label:'Training required',value:'None',delta:'Frozen backbone'}},
  ];
  document.getElementById('hero-kpis').innerHTML = kpis.map(k =>
    `<div class="kpi-card"><div class="kpi-label">${{k.label}}</div>
     <div class="kpi-value">${{k.value}}</div>
     ${{k.delta?`<div class="kpi-delta up">${{k.delta}}</div>`:''}}</div>`
  ).join('');
}})();

// ── PIPELINE STEPS ──────────────────────────────────────────────────────────
(function(){{
  const steps = [
    {{icon:'\\ud83d\\uddbc',title:'Raw images',desc:'MVTec LOCO AD'}},
    {{icon:'\\ud83d\\udd32',title:'Letterbox 384\\u00b2',desc:'Aspect-preserving resize'}},
    {{icon:'\\u2702',title:'Padding crop',desc:'Remove dead pixels (v2)'}},
    {{icon:'\\ud83e\\udde0',title:'DINOv2 extraction',desc:'Frozen ViT-S/14 patches'}},
    {{icon:'\\ud83d\\udcca',title:'5 scoring branches',desc:'Per-category models (v2)'}},
    {{icon:'\\ud83d\\udd00',title:'Score fusion',desc:'Validation z-normalisation'}},
    {{icon:'\\u2705',title:'Anomaly decision',desc:'Threshold + heatmap'}},
  ];
  document.getElementById('pipeline-steps').innerHTML = steps.map(s =>
    `<div class="step"><div class="step-icon">${{s.icon}}</div><div class="step-title">${{s.title}}</div>${{s.desc}}</div>`
  ).join('');
  const fig = D.pipeline_fig;
  if(fig) document.getElementById('pipeline-fig-container').innerHTML =
    `<h3>System architecture</h3><img src="${{fig}}" class="eda" alt="Pipeline overview">`;
  else document.getElementById('pipeline-fig-container').style.display='none';
}})();

// ── FLAW CARDS ──────────────────────────────────────────────────────────────
(function(){{
  const flaws = [
    {{n:1,title:'Letterbox padding fed to DINOv2',
      v1:'20\\u201350% of patch tokens were padding (50% for juice_bottle)',
      v2:'Content box cropped before extraction using metadata'}},
    {{n:2,title:'Global cross-category models',
      v1:'ONE memory bank, ONE vocabulary, ONE histogram stat shared across all 5 categories',
      v2:'Everything fitted per category \\u2014 banks, vocabularies, stats, fusion norms'}},
    {{n:3,title:'Redundant extraction + CPU search',
      v1:'Features re-extracted 4\\u00d7 (once per stage); NN search on CPU',
      v2:'Single-pass extraction to disk cache; GPU nearest-neighbour search'}},
    {{n:4,title:'PatchCore = PatchMemory (duplicated)',
      v1:'Byte-identical implementations counting as two methods',
      v2:'Differentiated: k=1/top-1% vs k=3/top-5% aggregation'}},
  ];
  document.getElementById('flaw-cards').innerHTML = flaws.map(f =>
    `<div class="flaw-card"><div class="flaw-num">#${{f.n}}</div>
     <h4>${{f.title}}</h4>
     <div class="flaw-v1">\\u274c v1: ${{f.v1}}</div>
     <div class="flaw-v2">\\u2705 v2: ${{f.v2}}</div></div>`
  ).join('');
}})();

// ── V1 VS V2 CHART ──────────────────────────────────────────────────────────
(function(){{
  if(!D.v1v2.length) return;
  const modes = ['overall','logical','structural'];
  const tg = document.getElementById('v1v2-toggle');
  modes.forEach((m,i) => {{
    const b = document.createElement('button');
    b.className = 'toggle-btn' + (i===0?' active':'');
    b.textContent = m.charAt(0).toUpperCase()+m.slice(1);
    b.onclick = () => updateV1V2(m, b);
    tg.appendChild(b);
  }});

  const ctx = document.getElementById('v1v2Chart').getContext('2d');
  let chart;
  function updateV1V2(mode, btn) {{
    tg.querySelectorAll('.toggle-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    const labels = D.v1v2.map(r=>r.method.replace('DINOv2 ','').replace('Detector ',''));
    const v1 = D.v1v2.map(r=>+(r['v1_'+mode]*100).toFixed(1));
    const v2 = D.v1v2.map(r=>+(r['v2_'+mode]*100).toFixed(1));
    if(chart) chart.destroy();
    chart = new Chart(ctx, {{
      type:'bar',
      data:{{ labels, datasets:[
        {{label:'v1',data:v1,backgroundColor:'rgba(108,140,255,0.35)',borderColor:'rgba(108,140,255,0.6)',borderWidth:1,borderRadius:3}},
        {{label:'v2',data:v2,backgroundColor:'rgba(52,211,153,0.6)',borderColor:'rgba(52,211,153,0.9)',borderWidth:1,borderRadius:3}},
      ]}},
      options:{{responsive:true,maintainAspectRatio:false,
        plugins:{{legend:{{labels:{{color:'#9aa6c8'}}}},
          tooltip:{{callbacks:{{afterBody:items=>{{const i=items[0].dataIndex;const d=(v2[i]-v1[i]).toFixed(1);return d>0?'Gain: +'+d+' pp':'';}} }} }} }},
        scales:{{
          y:{{min:40,max:100,ticks:{{color:'#7e89b0',callback:v=>v+'%'}},grid:{{color:'rgba(42,49,85,0.5)'}}}},
          x:{{ticks:{{color:'#9aa6c8',font:{{size:11}},maxRotation:30}},grid:{{display:false}}}}
        }}
      }}
    }});
    // bars
    const bars = document.getElementById('v1v2-bars');
    bars.innerHTML = '<h3 style="margin-bottom:16px">Improvement breakdown ('+mode+')</h3>' +
      D.v1v2.sort((a,b)=>(b['gain_'+mode]||0) - (a['gain_'+mode]||0)).map(r => {{
        const v1v = r['v1_'+mode], v2v = r['v2_'+mode];
        const gain = ((v2v-v1v)*100).toFixed(1);
        return `<div class="compare-bar">
          <div class="compare-label">${{r.method.replace('DINOv2 ','').replace('Detector ','')}}</div>
          <div class="compare-track">
            <div class="compare-fill v1-fill" style="width:${{v1v*100}}%">${{(v1v*100).toFixed(1)}}%</div>
          </div>
          <div class="compare-track">
            <div class="compare-fill v2-fill" style="width:${{v2v*100}}%">${{(v2v*100).toFixed(1)}}%</div>
          </div>
          <div style="min-width:60px;font-size:13px;font-weight:600;color:${{+gain>0?'var(--good)':'var(--bad)'}}">${{+gain>0?'+':''}}${{gain}}pp</div>
        </div>`;
      }}).join('');
  }}
  updateV1V2('overall', tg.children[0]);
}})();

// ── LEADERBOARD ─────────────────────────────────────────────────────────────
(function(){{
  const modes = ['overall','logical','structural'];
  const tg = document.getElementById('lb-toggle');
  modes.forEach((m,i) => {{
    const b = document.createElement('button');
    b.className = 'toggle-btn' + (i===0?' active':'');
    b.textContent = m.charAt(0).toUpperCase()+m.slice(1);
    b.onclick = () => updateLB(m, b);
    tg.appendChild(b);
  }});

  const ctx = document.getElementById('lbChart').getContext('2d');
  let chart;
  function updateLB(mode, btn) {{
    tg.querySelectorAll('.toggle-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    const sorted = [...D.v2_main].sort((a,b)=>b[mode]-a[mode]);
    const labels = sorted.map(r=>r.method);
    const vals = sorted.map(r=>+(r[mode]*100).toFixed(1));
    const colors = sorted.map((_,i) => i===0 ? 'rgba(52,211,153,0.7)' : 'rgba(108,140,255,0.5)');
    if(chart) chart.destroy();
    chart = new Chart(ctx, {{
      type:'bar', data:{{ labels, datasets:[{{data:vals,backgroundColor:colors,borderRadius:4}}] }},
      options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,
        plugins:{{legend:{{display:false}},
          tooltip:{{callbacks:{{label:c=>c.parsed.x.toFixed(1)+'%'}} }} }},
        scales:{{
          x:{{min:50,max:100,ticks:{{color:'#7e89b0',callback:v=>v+'%'}},grid:{{color:'rgba(42,49,85,0.5)'}}}},
          y:{{ticks:{{color:'#c0c8e0',font:{{size:12}}}},grid:{{display:false}}}}
        }}
      }}
    }});
    // table
    const ms = {{}};
    D.multiseed.forEach(r => {{ ms[r.method+'_'+r.anomaly_type] = r; }});
    document.getElementById('lb-table').innerHTML = `<h3>Multi-seed results (mean \\u00b1 std, ${{D.v2_config.seeds.length}} seeds)</h3>
      <table><thead><tr><th style="text-align:left">Method</th><th>Overall</th><th>Logical</th><th>Structural</th><th>F1 (overall)</th></tr></thead>
      <tbody>${{sorted.map((r,i) => {{
        const msO = ms[r.method+'_overall'], msL = ms[r.method+'_logical'], msS = ms[r.method+'_structural'];
        return `<tr class="${{i===0?'highlight-row':''}}">
          <td>${{r.method}}</td>
          <td>${{msO?f1(msO.mean)+'\\u00b1'+msO.std.toFixed(3):pct(r.overall)}}</td>
          <td>${{msL?f1(msL.mean)+'\\u00b1'+msL.std.toFixed(3):pct(r.logical)}}</td>
          <td>${{msS?f1(msS.mean)+'\\u00b1'+msS.std.toFixed(3):pct(r.structural)}}</td>
          <td>${{pct(r.f1_overall)}}</td></tr>`;
      }}).join('')}}</tbody></table>`;
  }}
  updateLB('overall', tg.children[0]);
}})();

// ── PER-CATEGORY ────────────────────────────────────────────────────────────
(function(){{
  const pills = document.getElementById('cat-pills');
  D.cats.forEach((cat,i) => {{
    const b = document.createElement('div');
    b.className = 'cat-pill' + (i===0?' active':'');
    b.textContent = D.cat_labels[cat] || cat;
    b.onclick = () => updateCat(cat, b);
    pills.appendChild(b);
  }});

  const ctx = document.getElementById('catChart').getContext('2d');
  let chart;
  function updateCat(cat, btn) {{
    pills.querySelectorAll('.cat-pill').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    const rows = D.v2_per.filter(r=>r.category===cat && r.anomaly_type==='overall');
    rows.sort((a,b)=>b.auroc-a.auroc);
    const labels = rows.map(r=>r.method);
    const vals = rows.map(r=>+(r.auroc*100).toFixed(1));
    if(chart) chart.destroy();
    chart = new Chart(ctx, {{
      type:'bar', data:{{ labels, datasets:[{{data:vals,backgroundColor:'rgba(108,140,255,0.5)',borderRadius:4}}] }},
      options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,
        plugins:{{legend:{{display:false}}}},
        scales:{{
          x:{{min:30,max:100,ticks:{{color:'#7e89b0',callback:v=>v+'%'}},grid:{{color:'rgba(42,49,85,0.5)'}}}},
          y:{{ticks:{{color:'#c0c8e0',font:{{size:11}}}},grid:{{display:false}}}}
        }}
      }}
    }});
    // maps
    const maps = D.anomaly_maps[cat] || {{}};
    document.getElementById('cat-maps').innerHTML = Object.keys(maps).length ?
      `<div class="map-grid">${{['normal','logical','structural'].map(t =>
        maps[t] ? `<div><img src="${{maps[t]}}" alt="${{t}}"><div class="map-label">${{t}}</div></div>` : ''
      ).join('')}}</div><p style="font-size:11px;color:var(--muted);margin-top:8px">Region-Aware DINOv2 anomaly heatmaps. Bright = high anomaly score.</p>` :
      '<p style="color:var(--muted);font-size:13px">No anomaly maps available for this category.</p>';
    // table
    const all = D.v2_per.filter(r=>r.category===cat);
    const methods = [...new Set(all.map(r=>r.method))];
    document.getElementById('cat-table').innerHTML = `<h3>${{D.cat_labels[cat]}} &mdash; detailed metrics</h3>
      <table><thead><tr><th style="text-align:left">Method</th><th>Overall</th><th>Logical</th><th>Structural</th><th>F1</th></tr></thead>
      <tbody>${{methods.map(m => {{
        const o = all.find(r=>r.method===m&&r.anomaly_type==='overall');
        const l = all.find(r=>r.method===m&&r.anomaly_type==='logical');
        const s = all.find(r=>r.method===m&&r.anomaly_type==='structural');
        return `<tr><td>${{m}}</td><td>${{o?pct(o.auroc):'—'}}</td><td>${{l?pct(l.auroc):'—'}}</td>
          <td>${{s?pct(s.auroc):'—'}}</td><td>${{o?pct(o.f1_max):'—'}}</td></tr>`;
      }}).join('')}}</tbody></table>`;
  }}
  updateCat(D.cats[0], pills.children[0]);
}})();

// ── FEATURE SELECTION ───────────────────────────────────────────────────────
(function(){{
  // LOO chart
  if(D.feature_loo.length) {{
    const sorted = [...D.feature_loo].sort((a,b)=>b.importance_delta-a.importance_delta);
    new Chart(document.getElementById('looChart'), {{
      type:'bar',
      data:{{ labels:sorted.map(r=>r.branch.replace('DINOv2 ','')),
        datasets:[{{data:sorted.map(r=>+(r.importance_delta*100).toFixed(2)),
          backgroundColor:sorted.map(r=>r.importance_delta>0?'rgba(52,211,153,0.6)':'rgba(248,113,113,0.6)'),
          borderRadius:4}}] }},
      options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,
        plugins:{{legend:{{display:false}},title:{{display:true,text:'Importance delta (pp) \\u2014 positive = helps fusion',color:'#9aa6c8',font:{{size:12}}}}}},
        scales:{{
          x:{{ticks:{{color:'#7e89b0',callback:v=>v.toFixed(1)+'pp'}},grid:{{color:'rgba(42,49,85,0.5)'}}}},
          y:{{ticks:{{color:'#c0c8e0',font:{{size:11}}}},grid:{{display:false}}}}
        }}
      }}
    }});
  }}
  // Dim chart
  if(D.feature_dim.length) {{
    new Chart(document.getElementById('dimChart'), {{
      type:'line',
      data:{{ labels:D.feature_dim.map(r=>r.dims+' dims'),
        datasets:[{{data:D.feature_dim.map(r=>+(r.mean_overall_auroc*100).toFixed(1)),
          borderColor:'rgba(108,140,255,0.8)',backgroundColor:'rgba(108,140,255,0.15)',
          fill:true,tension:0.3,pointRadius:6,pointBackgroundColor:'#6c8cff'}}] }},
      options:{{responsive:true,maintainAspectRatio:false,
        plugins:{{legend:{{display:false}},title:{{display:true,text:'PCA-reduced vs full 384-dim DINOv2 features',color:'#9aa6c8',font:{{size:12}}}}}},
        scales:{{
          y:{{min:60,max:80,ticks:{{color:'#7e89b0',callback:v=>v+'%'}},grid:{{color:'rgba(42,49,85,0.5)'}}}},
          x:{{ticks:{{color:'#c0c8e0'}},grid:{{color:'rgba(42,49,85,0.3)'}}}}
        }}
      }}
    }});
  }}
  // FS table
  if(D.feature_sel.length) {{
    document.getElementById('fs-table').innerHTML = `<h3>Feature set comparison</h3>
      <table><thead><tr><th style="text-align:left">Configuration</th><th>Branches</th><th>Overall</th><th>Logical</th><th>Structural</th></tr></thead>
      <tbody>${{D.feature_sel.map(r=>`<tr><td>${{r.model}}</td><td>${{r.n_branches}}</td>
        <td>${{pct(r.overall)}}</td><td>${{pct(r.logical)}}</td><td>${{pct(r.structural)}}</td></tr>`).join('')}}</tbody></table>`;
  }}
}})();

// ── EDA ─────────────────────────────────────────────────────────────────────
(function(){{
  const g = document.getElementById('eda-gallery');
  g.innerHTML = Object.entries(D.eda).map(([k,v]) =>
    `<div class="card"><h3>${{k}}</h3><img src="${{v}}" class="eda" alt="${{k}}"></div>`
  ).join('');
  if(!Object.keys(D.eda).length) g.innerHTML = '<div class="card"><p style="color:var(--muted)">EDA images not available on this machine. Run preprocessing to generate them.</p></div>';
}})();

// ── EXPLAINABILITY ──────────────────────────────────────────────────────────
(function(){{
  const g = document.getElementById('qual-gallery');
  g.innerHTML = Object.entries(D.qualitative).map(([k,v]) =>
    `<div class="card"><h3>${{k}}</h3><img src="${{v}}" class="eda" alt="${{k}}"></div>`
  ).join('');
  if(!Object.keys(D.qualitative).length) g.innerHTML = '<div class="card"><p style="color:var(--muted)">Qualitative analysis images will be populated after running the full evaluation pipeline.</p></div>';
}})();

// ── INSIGHTS ────────────────────────────────────────────────────────────────
(function(){{
  const insights = [
    {{title:'Fusion Max is the new champion',text:'Per-category normalization (v2 fix #2) transformed Fusion Max from one of the weakest fusions in v1 (71.4%) to the best overall method in v2 (82.7%). The fix ensures each category\\'s scores are comparable before taking the maximum.'}},
    {{title:'Structural detection crossed 90%',text:'Fusion Max reaches 90.3% structural AUROC. Removing letterbox padding (v2 fix #1) eliminated 20-50% of noise tokens, and per-category memory banks sharpened the normal reference.'}},
    {{title:'Logical anomalies remain the harder problem',text:'Best logical AUROC is 76.9% vs 90.3% structural. Logical defects (wrong count, missing parts) require compositional understanding that patch-level comparison alone cannot fully capture.'}},
    {{title:'Composition Histogram recovered but remains weakest',text:'From 49.8% structural (v1, harmful) to 64.5% (v2). Per-category vocabularies fixed the cross-category confusion, but the bag-of-words representation still loses spatial structure.'}},
    {{title:'Multi-seed results are stable',text:'Standard deviations across 3 seeds are 0.0\\u20130.8pp, confirming the results are not artifacts of a lucky random seed.'}},
    {{title:'Honest limitations',text:'Letterbox padding is now cropped but not fully masked in evaluation metrics. We do not report sPRO/AUPRO (pixel-level localization). We use DINOv2-small; DINOv2-base could improve results by 2-4pp. We do not claim to match SALAD (96.1%) or CSAD (95.3%).'}},
  ];
  document.getElementById('insight-cards').innerHTML = insights.map(ins =>
    `<div class="insight-card"><h3>${{ins.title}}</h3><p>${{ins.text}}</p></div>`
  ).join('');
}})();

// ── SIDEBAR NAV HIGHLIGHT + SCROLL PROGRESS ─────────────────────────────────
(function(){{
  const links = document.querySelectorAll('nav.sidebar a');
  const sections = [...links].map(a => document.querySelector(a.getAttribute('href')));
  const progress = document.getElementById('scroll-progress');
  window.addEventListener('scroll', () => {{
    let current = 0;
    sections.forEach((s,i) => {{ if(s && window.scrollY >= s.offsetTop - 120) current = i; }});
    links.forEach((a,i) => a.classList.toggle('active', i===current));
    const pct = Math.min(100, (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100);
    if(progress) progress.style.width = pct + '%';
  }});
}})();

// ── SCROLL REVEAL ───────────────────────────────────────────────────────────
(function(){{
  const obs = new IntersectionObserver((entries) => {{
    entries.forEach(e => {{ if(e.isIntersecting) {{ e.target.classList.add('visible'); }} }});
  }}, {{threshold:0.08,rootMargin:'0px 0px -40px 0px'}});
  document.querySelectorAll('.reveal,.reveal-left,.reveal-right,.reveal-scale').forEach(el => obs.observe(el));
}})();

// ── HERO PARTICLES ──────────────────────────────────────────────────────────
(function(){{
  const canvas = document.getElementById('particles');
  if(!canvas) return;
  const ctx = canvas.getContext('2d');
  let w, h, particles = [];
  function resize() {{ w = canvas.width = canvas.parentElement.offsetWidth; h = canvas.height = canvas.parentElement.offsetHeight; }}
  resize(); window.addEventListener('resize', resize);
  for(let i = 0; i < 50; i++) {{
    particles.push({{
      x: Math.random() * w, y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.4, vy: (Math.random() - 0.5) * 0.3,
      r: Math.random() * 2 + 0.5, a: Math.random() * 0.4 + 0.1
    }});
  }}
  function draw() {{
    ctx.clearRect(0, 0, w, h);
    particles.forEach(p => {{
      p.x += p.vx; p.y += p.vy;
      if(p.x < 0) p.x = w; if(p.x > w) p.x = 0;
      if(p.y < 0) p.y = h; if(p.y > h) p.y = 0;
      ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(108,140,255,${{p.a}})`; ctx.fill();
    }});
    for(let i = 0; i < particles.length; i++) {{
      for(let j = i + 1; j < particles.length; j++) {{
        const dx = particles[i].x - particles[j].x, dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx*dx + dy*dy);
        if(dist < 120) {{
          ctx.beginPath(); ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(108,140,255,${{0.08 * (1 - dist/120)}})`;
          ctx.lineWidth = 0.5; ctx.stroke();
        }}
      }}
    }}
    requestAnimationFrame(draw);
  }}
  draw();
}})();

// ── ANIMATED COUNTERS ───────────────────────────────────────────────────────
(function(){{
  const obs = new IntersectionObserver((entries) => {{
    entries.forEach(e => {{
      if(e.isIntersecting && !e.target.dataset.counted) {{
        e.target.dataset.counted = '1';
        const text = e.target.textContent;
        const match = text.match(/(\\d+\\.?\\d*)/);
        if(!match) return;
        const target = parseFloat(match[1]);
        const suffix = text.replace(match[0], '');
        const prefix = text.substring(0, text.indexOf(match[0]));
        const duration = 1200;
        const start = performance.now();
        function tick(now) {{
          const elapsed = now - start;
          const progress = Math.min(elapsed / duration, 1);
          const eased = 1 - Math.pow(1 - progress, 3);
          const current = (target * eased).toFixed(text.includes('.') ? 1 : 0);
          e.target.textContent = prefix + current + suffix;
          if(progress < 1) requestAnimationFrame(tick);
        }}
        requestAnimationFrame(tick);
      }}
    }});
  }}, {{threshold:0.5}});
  setTimeout(() => {{
    document.querySelectorAll('.kpi-value').forEach(el => obs.observe(el));
  }}, 200);
}})();

// ── CARD GLOW (follow mouse) ────────────────────────────────────────────────
document.querySelectorAll('.card-glow').forEach(card => {{
  card.addEventListener('mousemove', e => {{
    const r = card.getBoundingClientRect();
    card.style.setProperty('--mouse-x', ((e.clientX - r.left) / r.width * 100) + '%');
    card.style.setProperty('--mouse-y', ((e.clientY - r.top) / r.height * 100) + '%');
  }});
}});
</script>
</body>
</html>'''

# ── Write output ─────────────────────────────────────────────────────────────
(OUT / "dashboard.html").write_text(HTML, encoding="utf-8")
print(f"\nDashboard written to: {OUT / 'dashboard.html'}")
print(f"File size: {(OUT / 'dashboard.html').stat().st_size / 1e6:.2f} MB")
