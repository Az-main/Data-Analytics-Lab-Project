# -*- coding: utf-8 -*-
"""Generates Run_DINOv2_Colab.ipynb — a careful, self-contained Colab notebook
that runs the LOCO pipeline with REAL DINOv2 features on a free GPU."""
import json, os

REPO = "https://github.com/Az-main/Data-Analytics-Lab-Project.git"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Run_DINOv2_Colab.ipynb")

def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text}

def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": text}

cells = []

cells.append(md(
"""# Real DINOv2 run — MVTec LOCO Anomaly Inspector (Colab GPU)

This notebook re-runs your pipeline with **real `facebook/dinov2-small` patch features** instead of the
handcrafted fallback, on a free GPU, then exports the result CSVs to download back to your PC.

### Before you run — two one-time setup steps
1. **Turn on the GPU:** menu **Runtime → Change runtime type → Hardware accelerator = T4 GPU → Save.**
2. **Make your dataset visible to Colab.** Your `Phase 1` folder lives in Google Drive under
   *Other computers* (backups), which Colab does **not** mount automatically. Easiest fix:
   - Open **drive.google.com** → find the **`Phase 1`** folder (under *Computers → My Computer → … → Data Analaytics Lab*).
   - **Right-click it → Organize → Add shortcut to Drive → My Drive → Add.**
   - It now appears in **My Drive**, which Colab can mount. (Cell 4 will auto-find it.)

Then just **Runtime → Run all**. Total time ≈ **40–80 min** (the nearest-neighbour search on CPU is the slow part).
Keep the tab open so the session doesn't disconnect.
"""))

cells.append(md("## 1. Check the GPU"))
cells.append(code(
"""import torch
print("torch:", torch.__version__)
assert torch.cuda.is_available(), (
    "No GPU! Set Runtime -> Change runtime type -> T4 GPU, then Run all again.")
print("GPU :", torch.cuda.get_device_name(0))
"""))

cells.append(md("## 2. Dependencies (transformers / DINOv2)"))
cells.append(code(
"""# Colab ships torch+CUDA. Ensure a transformers with DINOv2 support is importable.
try:
    from transformers import AutoImageProcessor, AutoModel
    import transformers; print("transformers:", transformers.__version__)
except Exception:
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U",
                    "transformers>=4.40", "huggingface_hub>=0.20"], check=True)
    from transformers import AutoImageProcessor, AutoModel
    import transformers; print("installed transformers:", transformers.__version__)
"""))

cells.append(md("## 3. Mount Google Drive"))
cells.append(code(
"""from google.colab import drive
drive.mount('/content/drive')
"""))

cells.append(md(
"""## 4. Locate & verify your dataset
Set `PHASE1_DRIVE` if auto-detection fails. The check below confirms all 5 categories are present."""))
cells.append(code(
"""import os, glob

CATEGORIES = ["breakfast_box", "juice_bottle", "pushpins", "screw_bag", "splicing_connectors"]

def looks_like_phase1(p):
    try:
        return p and all(os.path.isdir(os.path.join(p, c, "test")) for c in CATEGORIES)
    except Exception:
        return False

# 0) set this manually if needed, e.g. "/content/drive/MyDrive/Phase 1"
PHASE1_DRIVE = ""

guesses = [PHASE1_DRIVE,
           "/content/drive/MyDrive/Phase 1",
           "/content/drive/MyDrive/Data Analaytics Lab/Phase 1",
           "/content/drive/MyDrive/Data Analytics Lab/Phase 1"]
found = next((g for g in guesses if looks_like_phase1(g)), None)

if not found:  # shallow search of My Drive for a folder named 'Phase 1'
    for hit in glob.glob("/content/drive/MyDrive/**/Phase 1", recursive=True):
        if looks_like_phase1(hit):
            found = hit; break

assert found, ("Could not find 'Phase 1' with the 5 categories. Do the 'Add shortcut to Drive' step "
               "in the intro, or set PHASE1_DRIVE above to the exact path and re-run this cell.")
PHASE1_DRIVE = found
print("Found dataset at:", PHASE1_DRIVE)
for c in CATEGORIES:
    n = len(glob.glob(os.path.join(PHASE1_DRIVE, c, "train", "good", "*.png")))
    print(f"  {c:22s} train/good = {n}")
"""))

cells.append(md(
"""## 5. Copy the data to local Colab disk
Drive is slow for thousands of small reads; copying once (~5.7 GB) makes preprocessing fast and reliable."""))
cells.append(code(
"""import os, subprocess, time
PHASE1_LOCAL = "/content/Phase 1"
if looks_like_phase1(PHASE1_LOCAL):
    print("Local copy already present:", PHASE1_LOCAL)
else:
    t = time.time()
    print("Copying dataset to", PHASE1_LOCAL, "...")
    r = subprocess.run(["cp", "-r", PHASE1_DRIVE, PHASE1_LOCAL])
    if r.returncode != 0 or not looks_like_phase1(PHASE1_LOCAL):
        import shutil
        if os.path.exists(PHASE1_LOCAL): shutil.rmtree(PHASE1_LOCAL, ignore_errors=True)
        shutil.copytree(PHASE1_DRIVE, PHASE1_LOCAL)
    assert looks_like_phase1(PHASE1_LOCAL), "Copy failed."
    print(f"Done in {time.time()-t:.0f}s")
"""))

cells.append(md(
"""## 6. Get the pipeline code & build the folder layout
Clones your repo into the `Project_A_LOCO_AD` slot and symlinks `Phase 1` next to it, so
`get_project_paths()` resolves correctly. If your repo is private, the cell tells you how to upload the
one file it needs instead."""))
cells.append(code(
f"""import os, sys, subprocess
LAB_ROOT = "/content/lab"
PROJ = os.path.join(LAB_ROOT, "Project_A_LOCO_AD")
os.makedirs(LAB_ROOT, exist_ok=True)

# 6a. get the code (clone repo; fall back to manual upload)
if not os.path.exists(os.path.join(PROJ, "01_notebooks", "loco_project_utils.py")):
    rc = subprocess.run(["git", "clone", "--depth", "1", "{REPO}", PROJ]).returncode
    if rc != 0 or not os.path.exists(os.path.join(PROJ, "01_notebooks", "loco_project_utils.py")):
        os.makedirs(os.path.join(PROJ, "01_notebooks"), exist_ok=True)
        print("Repo clone failed (private?). Upload loco_project_utils.py now:")
        from google.colab import files
        up = files.upload()
        for fn in up:
            os.replace(fn, os.path.join(PROJ, "01_notebooks", "loco_project_utils.py"))
print("engine present:", os.path.exists(os.path.join(PROJ, "01_notebooks", "loco_project_utils.py")))

# 6b. symlink Phase 1 next to the project (use the local copy)
link = os.path.join(LAB_ROOT, "Phase 1")
if not os.path.exists(link):
    os.symlink(PHASE1_LOCAL, link)
print("lab_root contents:", sorted(os.listdir(LAB_ROOT)))

# 6c. import the engine
sys.path.insert(0, os.path.join(PROJ, "01_notebooks"))
import loco_project_utils as L
print("imported loco_project_utils OK")
"""))

cells.append(md(
"""## 7. Force REAL DINOv2 features (cosine recipe, no silent fallback)
This replaces `extract_patch_features` with a DINOv2-only extractor that:
- uses `facebook/dinov2-small` (set `MODEL_SIZE='base'` for higher accuracy — ~2× slower NN),
- **L2-normalizes** patch tokens so the pipeline's Euclidean NN becomes **cosine** (AnomalyDINO recipe),
- tags outputs honestly as `dinov2-small`/`dinov2-base`,
- **raises** if the model can't load (so results can never silently fall back to handcrafted)."""))
cells.append(code(
"""import math, numpy as np, torch
from transformers import AutoImageProcessor, AutoModel
from PIL import Image

MODEL_SIZE = "small"            # "small" (fast, default) or "base" (better, ~2x slower NN)
NORMALIZE  = True               # L2-normalize -> Euclidean NN == cosine
MODEL_NAME = f"facebook/dinov2-{MODEL_SIZE}"
MODEL_TAG  = f"dinov2-{MODEL_SIZE}"
_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
_orig_simple = L.simple_patch_features

def dinov2_extract(image_path, backend="auto", grid=24, model_cache=None, include_xy=False):
    if backend not in {"auto", "dinov2"}:
        feats, coords, shape = _orig_simple(image_path, grid=grid, include_xy=include_xy)
        return feats, coords, shape, "fallback_patch_stats"
    cache = model_cache if model_cache is not None else {}
    if "model" not in cache:
        cache["processor"] = AutoImageProcessor.from_pretrained(MODEL_NAME)
        cache["model"] = AutoModel.from_pretrained(MODEL_NAME).to(_DEVICE).eval()
    processor, model = cache["processor"], cache["model"]
    with Image.open(image_path) as im:
        inputs = processor(images=im.convert("RGB"), return_tensors="pt").to(_DEVICE)
    with torch.no_grad():
        out = model(**inputs).last_hidden_state[0, 1:, :]   # drop CLS -> [num_patches, dim]
        if NORMALIZE:
            out = torch.nn.functional.normalize(out, dim=1)
        patches = out.float().cpu().numpy()
    g = int(round(math.sqrt(patches.shape[0])))
    coords = np.array([(i, j) for i in range(g) for j in range(g)], dtype=np.int16)
    shape = (g, g)
    if include_xy:
        xy = coords.astype(np.float32).copy()
        xy[:, 0] /= max(1, g - 1); xy[:, 1] /= max(1, g - 1)
        patches = np.concatenate([patches, xy], axis=1)
    return patches.astype(np.float32), coords, shape, MODEL_TAG

L.extract_patch_features = dinov2_extract   # module-global swap; stages pick this up

# smoke test on one image
import glob
_sample = glob.glob(os.path.join(PHASE1_LOCAL, "breakfast_box", "train", "good", "*.png"))[0]
_f, _c, _s, _tag = L.extract_patch_features(_sample, backend="dinov2")
print(f"OK: features {_f.shape} (grid {_s}), backend tag = {_tag}, device = {_DEVICE}")
assert _tag.startswith("dinov2"), "DINOv2 extractor not active!"
"""))

cells.append(md("## 8. Preprocess (letterbox 384²) — builds the cleaned dataset the methods read"))
cells.append(code(
"""import time
L.set_reproducible_seed(42)
t = time.time(); print("Preprocessing...")
res = L.run_stage01_preprocessing(lab_root=LAB_ROOT)
print(f"Done in {time.time()-t:.0f}s")
"""))

cells.append(md("## 9. Global baseline (EfficientAD proxy — image-level, not DINOv2 by design)"))
cells.append(code(
"""import time
t = time.time(); L.run_stage04_efficientad(lab_root=LAB_ROOT); print(f"stage04 done in {time.time()-t:.0f}s")
"""))

cells.append(md("## 10–13. The DINOv2 detectors (this is the slow part — NN search on CPU)"))
cells.append(code(
"""import time
for name, fn in [("stage05 PatchCore(DINOv2)",   lambda: L.run_stage05_patchcore(LAB_ROOT, backend='dinov2')),
                 ("stage06 DINOv2 PatchMemory",  lambda: L.run_stage06_dinov2_patchmemory(LAB_ROOT, backend='dinov2')),
                 ("stage07 GridAware(DINOv2)",    lambda: L.run_stage07_gridaware(LAB_ROOT, backend='dinov2')),
                 ("stage08 CompositionHist(DINOv2)", lambda: L.run_stage08_composition_histogram(LAB_ROOT, backend='dinov2'))]:
    t = time.time(); fn(); print(f"{name} done in {time.time()-t:.0f}s")
"""))

cells.append(md("## 14. Fusion + final tables"))
cells.append(code(
"""import time
t = time.time()
L.run_stage09_fusion(lab_root=LAB_ROOT)
L.run_stage10_final_tables(lab_root=LAB_ROOT)
print(f"fusion + tables done in {time.time()-t:.0f}s")
"""))

cells.append(md("## 15. Verify the run is REAL DINOv2, and preview results"))
cells.append(code(
"""import pandas as pd
paths = L.get_project_paths(lab_root=LAB_ROOT)
runtime_csvs = {
    "PatchCore":          paths.baseline_root / "PatchCore" / "patchcore_runtime_memory.csv",
    "DINOv2 PatchMemory": paths.method_root / "DINOv2_PatchMemory" / "dinov2_patchmemory_runtime_memory.csv",
    "GridAware":          paths.method_root / "GridAware_DINOv2" / "gridaware_runtime_memory.csv",
    "CompositionHist":    paths.method_root / "CompositionHistogram" / "composition_hist_runtime_memory.csv",
}
print("=== feature_backend check (must be dinov2-*) ===")
ok = True
for name, p in runtime_csvs.items():
    if p.exists():
        b = pd.read_csv(p)["feature_backend"].iloc[0]
        flag = "OK" if str(b).startswith("dinov2") else "  <-- NOT DINOv2!"
        ok &= str(b).startswith("dinov2")
        print(f"  {name:20s}: {b}{'' if flag=='OK' else flag}")
print("ALL DINOv2:", ok)

mr = paths.method_root / "Final_Evaluation" / "main_results_table.csv"
if mr.exists():
    print("\\n=== main_results_table.csv ===")
    print(pd.read_csv(mr).to_string(index=False))
"""))

cells.append(md("## 16. Package results → save to Drive + download"))
cells.append(code(
"""import shutil, os
paths = L.get_project_paths(lab_root=LAB_ROOT)
stage_dir = "/content/loco_dinov2_results"
if os.path.exists(stage_dir): shutil.rmtree(stage_dir)
os.makedirs(stage_dir)
# copy the two result trees (CSVs, configs, maps) that the dashboard + report rebuild from
shutil.copytree(paths.baseline_root, os.path.join(stage_dir, "05_baselines"))
shutil.copytree(paths.method_root,  os.path.join(stage_dir, "06_method_results"))
zip_path = shutil.make_archive("/content/loco_dinov2_results", "zip", stage_dir)
size_mb = os.path.getsize(zip_path) / 1e6
print(f"Created {zip_path} ({size_mb:.1f} MB)")
# save a copy to Drive so it survives a disconnect
try:
    shutil.copy(zip_path, "/content/drive/MyDrive/loco_dinov2_results.zip")
    print("Saved to Drive: MyDrive/loco_dinov2_results.zip")
except Exception as e:
    print("Drive copy skipped:", e)
from google.colab import files
files.download(zip_path)
"""))

cells.append(md(
"""## ✅ Done — bring the results back
You now have **`loco_dinov2_results.zip`** (downloaded and in your Drive).

Tell Claude on your PC *"the DINOv2 results are downloaded"* and point it to the zip. It will:
1. unzip the new score CSVs into your project (`05_baselines/`, `06_method_results/`),
2. regenerate the dashboard + report + slides with the real DINOv2 numbers,
3. update the method-name labels and remove the "handcrafted" caveat.

**Honest caveats to keep in the report:** features are real DINOv2 (cosine NN), but letterbox padding is not
masked out, and results are single-seed. Both are noted as future work."""))

nb = {
    "cells": cells,
    "metadata": {
        "accelerator": "GPU",
        "colab": {"provenance": [], "toc_visible": True},
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 4,
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)
print("Wrote", OUT, "with", len(cells), "cells")
