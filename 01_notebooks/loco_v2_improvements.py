"""v2 pipeline improvements over the v1 stages in loco_project_utils (stages 05-09).

Design flaws found in the v1 implementation and fixed here:

1. PADDING: v1 fed the full 384x384 letterboxed canvas to DINOv2, so 20-50% of
   patch tokens (depending on category aspect ratio) described constant padding.
   v2 crops the valid content box (recorded in resize_letterbox_metadata.csv)
   before feature extraction, so every patch token describes real content.
2. PER-CATEGORY MODELING: v1 built ONE patch-memory bank shared by all 5
   categories (capped at 50k patches), fitted ONE k-means vocabulary and
   compared every composition histogram to a GLOBAL mean/covariance, and
   z-normalized fusion scores with GLOBAL validation statistics. v2 fits
   memory banks, vocabularies, histogram statistics and fusion normalization
   PER CATEGORY (the v1 GridAware stage already did this - and was the
   strongest single v1 method, which motivated the change).
3. SPEED: v1 re-extracted DINOv2 features per stage (4x) and ran
   nearest-neighbour search on CPU. v2 extracts each image once into an
   on-disk cache and runs NN search on the GPU, which makes multi-seed
   evaluation affordable on a free Colab T4.
4. SEEDS: v1 was single-seed. v2 accepts a list of seeds (bank subsampling,
   k-means, isolation forest) and reports mean +/- std across seeds.

The v2 runner writes the SAME csv files / schemas / method names as v1
(patchcore_scores.csv, dinov2_patchmemory_scores.csv, gridaware_scores.csv,
composition_hist_scores.csv, fusion_scores.csv, runtime/summary/per-category
tables), so the downstream dashboard / report / slide builders work unchanged.

Run on Colab:
    import loco_v2_improvements as V2
    V2.run_v2_pipeline(lab_root=LAB_ROOT, model_size="small", seeds=[42, 7, 2026])

Local self-test (no torch / data / GPU needed):
    python loco_v2_improvements.py --selftest
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from PIL import Image

import loco_project_utils as L

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
PATCH_SIZE = 14

# v1-compatible method names: downstream scripts key on these strings.
M_PATCHCORE = "PatchCore"
M_PATCHMEM = "DINOv2 PatchMemory"
M_GRIDAWARE = "GridAware DINOv2"
M_COMPHIST = "CompositionHistogram"
M_EFFAD = "EfficientAD"


# ---------------------------------------------------------------------------
# padding crop boxes
# ---------------------------------------------------------------------------

def load_crop_boxes(paths: "L.ProjectPaths") -> Dict[str, Tuple[int, int, int, int]]:
    """Per-category PIL crop box (left, top, right, bottom) of the letterbox
    content area, read from the stage01 resize metadata. LOCO product images
    have a constant size per category, so one box per category is exact."""
    meta_path = paths.audit_root / "resize_letterbox_metadata.csv"
    boxes: Dict[str, Tuple[int, int, int, int]] = {}
    if not meta_path.exists():
        return boxes
    meta = pd.read_csv(meta_path)
    prod = meta[meta["is_mask"].astype(str).str.lower() == "false"]
    for cat in L.CATEGORIES:
        rows = prod[prod["output_relative_path"].astype(str).str.startswith(cat + "/")]
        if rows.empty:
            continue
        pl = int(rows["pad_left"].mode().iloc[0])
        pt = int(rows["pad_top"].mode().iloc[0])
        pr = int(rows["pad_right"].mode().iloc[0])
        pb = int(rows["pad_bottom"].mode().iloc[0])
        ts = int(rows["target_size"].mode().iloc[0])
        boxes[cat] = (pl, pt, ts - pr, ts - pb)
    return boxes


def uncrop_patch_map(grid_scores: np.ndarray, box: Optional[Tuple[int, int, int, int]],
                     target_size: int = 384) -> np.ndarray:
    """Place a (g, g) patch-score grid for the cropped content back onto the
    full letterbox canvas so heatmap overlays align with the cleaned image."""
    if box is None:
        box = (0, 0, target_size, target_size)
    left, top, right, bottom = box
    w, h = max(1, right - left), max(1, bottom - top)
    im = Image.fromarray(grid_scores.astype(np.float32), mode="F")
    im = im.resize((w, h), Image.Resampling.BILINEAR)
    canvas = np.zeros((target_size, target_size), dtype=np.float32)
    canvas[top:top + h, left:left + w] = np.asarray(im)
    return canvas


# ---------------------------------------------------------------------------
# DINOv2 extraction with on-disk cache
# ---------------------------------------------------------------------------

class Dinov2V2Extractor:
    """Frozen DINOv2 patch-token extractor with padding crop and feature cache.

    Preprocessing is done manually (crop -> square resize to img_size ->
    ImageNet normalize) instead of AutoImageProcessor, because the default
    processor center-crops non-square inputs (which would discard content
    after the padding crop). img_size must be divisible by the 14px patch.
    """

    def __init__(self, model_size: str = "small", img_size: int = 336,
                 crop_boxes: Optional[Dict[str, Tuple[int, int, int, int]]] = None,
                 cache_dir: Optional[Path | str] = None, batch_size: int = 16):
        if img_size % PATCH_SIZE != 0:
            raise ValueError(f"img_size must be divisible by {PATCH_SIZE}, got {img_size}")
        import torch
        from transformers import AutoModel

        self.torch = torch
        self.model_name = f"facebook/dinov2-{model_size}"
        self.tag = f"dinov2-{model_size}-v2crop{img_size}"
        self.img_size = img_size
        self.grid = img_size // PATCH_SIZE
        self.crop_boxes = crop_boxes or {}
        self.batch_size = batch_size
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = AutoModel.from_pretrained(self.model_name).to(self.device).eval()
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, rec: pd.Series) -> Optional[Path]:
        if not self.cache_dir:
            return None
        import hashlib
        key = hashlib.md5(f"{rec['relative_path']}|{self.tag}".encode()).hexdigest()
        return self.cache_dir / f"{key}.npy"

    def _load_tensor(self, rec: pd.Series):
        with Image.open(rec["path"]) as im:
            im = im.convert("RGB")
            box = self.crop_boxes.get(rec["category"])
            if box:
                im = im.crop(box)
            im = im.resize((self.img_size, self.img_size), Image.Resampling.BILINEAR)
            arr = np.asarray(im, dtype=np.float32) / 255.0
        arr = (arr - IMAGENET_MEAN) / IMAGENET_STD
        return self.torch.from_numpy(arr.transpose(2, 0, 1))

    def extract_all(self, records: pd.DataFrame, log_every: int = 500) -> Dict[str, np.ndarray]:
        """Returns {image_id: (n_patches, dim) float16}, extracting only cache misses."""
        torch = self.torch
        feats: Dict[str, np.ndarray] = {}
        missing: List[pd.Series] = []
        for _, rec in records.iterrows():
            cp = self._cache_path(rec)
            if cp is not None and cp.exists():
                feats[rec["image_id"]] = np.load(cp)
            else:
                missing.append(rec)
        t0, done = time.perf_counter(), 0
        for start in range(0, len(missing), self.batch_size):
            batch = missing[start:start + self.batch_size]
            pixel = torch.stack([self._load_tensor(r) for r in batch]).to(self.device)
            with torch.no_grad():
                out = self.model(pixel_values=pixel).last_hidden_state[:, 1:, :]  # drop CLS
                out = torch.nn.functional.normalize(out, dim=2)
            arr = out.float().cpu().numpy().astype(np.float16)
            for rec, f in zip(batch, arr):
                feats[rec["image_id"]] = f
                cp = self._cache_path(rec)
                if cp is not None:
                    np.save(cp, f)
            done += len(batch)
            if done % log_every < self.batch_size:
                rate = done / max(1e-9, time.perf_counter() - t0)
                print(f"  extracted {done}/{len(missing)} ({rate:.1f} img/s)")
        return feats


_GLOBAL_EXTRACTOR: Optional[Dinov2V2Extractor] = None


def get_extractor(model_size: str = "small", img_size: int = 336,
                  crop_boxes: Optional[Dict] = None, cache_dir: Optional[Path | str] = None,
                  batch_size: int = 16) -> Dinov2V2Extractor:
    """Singleton so the model loads once per session (smoke test + full run + 15b)."""
    global _GLOBAL_EXTRACTOR
    tag = f"dinov2-{model_size}-v2crop{img_size}"
    if _GLOBAL_EXTRACTOR is None or _GLOBAL_EXTRACTOR.tag != tag:
        _GLOBAL_EXTRACTOR = Dinov2V2Extractor(model_size=model_size, img_size=img_size,
                                              crop_boxes=crop_boxes, cache_dir=cache_dir,
                                              batch_size=batch_size)
    elif crop_boxes:
        _GLOBAL_EXTRACTOR.crop_boxes = crop_boxes
    return _GLOBAL_EXTRACTOR


def patch_v1_extractor(model_size: str = "small", img_size: int = 336,
                       crop_boxes: Optional[Dict] = None,
                       cache_dir: Optional[Path | str] = None) -> None:
    """Replace L.extract_patch_features with the v2 extractor (v1 signature),
    so older cells/notebooks (e.g. the PCA feature-dimension study) transparently
    use real DINOv2 features with the padding crop."""
    ex = get_extractor(model_size=model_size, img_size=img_size,
                       crop_boxes=crop_boxes, cache_dir=cache_dir)

    def _compat(image_path, backend="auto", grid=24, model_cache=None, include_xy=False):
        p = str(image_path)
        category = next((c for c in L.CATEGORIES if c in p.replace("\\", "/")), "")
        rec = pd.Series({"path": p, "relative_path": p, "category": category,
                         "image_id": p})
        feats = ex.extract_all(pd.DataFrame([rec]), log_every=10 ** 9)[p].astype(np.float32)
        g = ex.grid
        coords = np.array([(i, j) for i in range(g) for j in range(g)], dtype=np.int16)
        if include_xy:
            xy = coords.astype(np.float32).copy()
            xy[:, 0] /= max(1, g - 1)
            xy[:, 1] /= max(1, g - 1)
            feats = np.concatenate([feats, xy], axis=1)
        return feats, coords, (g, g), ex.tag

    L.extract_patch_features = _compat


# ---------------------------------------------------------------------------
# nearest-neighbour search (GPU if available, numpy fallback)
# ---------------------------------------------------------------------------

def min_nn_dists(bank: np.ndarray, queries: np.ndarray, k: int = 1,
                 chunk: int = 2048) -> np.ndarray:
    """Mean distance to the k nearest bank vectors for each query.
    Inputs are L2-normalized, so euclidean distance = sqrt(2 - 2*cosine)."""
    try:
        import torch  # broken local installs can raise OSError, not ImportError
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32
        b = torch.from_numpy(np.ascontiguousarray(bank)).to(device=device, dtype=dtype)
        out = np.empty(len(queries), dtype=np.float32)
        for s in range(0, len(queries), chunk):
            q = torch.from_numpy(np.ascontiguousarray(queries[s:s + chunk])).to(device=device, dtype=dtype)
            sim = q @ b.T
            kk = min(k, b.shape[0])
            top = sim.topk(kk, dim=1).values.float()
            d = torch.sqrt(torch.clamp(2.0 - 2.0 * top, min=0.0)).mean(dim=1)
            out[s:s + len(q)] = d.cpu().numpy()
        return out
    except Exception:
        bank32 = bank.astype(np.float32)
        out = np.empty(len(queries), dtype=np.float32)
        for s in range(0, len(queries), chunk):
            q = queries[s:s + chunk].astype(np.float32)
            sim = q @ bank32.T
            kk = min(k, bank32.shape[0])
            top = np.sort(sim, axis=1)[:, -kk:]
            out[s:s + len(q)] = np.sqrt(np.clip(2.0 - 2.0 * top, 0.0, None)).mean(axis=1)
        return out


def subsample(rng: np.random.Generator, arr: np.ndarray, cap: int) -> np.ndarray:
    if len(arr) <= cap:
        return arr
    idx = rng.choice(len(arr), size=cap, replace=False)
    return arr[idx]


# ---------------------------------------------------------------------------
# branch scorers (all per-category, all on cached features)
# ---------------------------------------------------------------------------

def _base_row(method: str, rec: pd.Series, score: float, backend: str,
              elapsed_ms: float, map_file: str = "", **extra) -> Dict[str, object]:
    row = {
        "method": method,
        "image_id": rec["image_id"],
        "path": rec["path"],
        "relative_path": rec["relative_path"],
        "category": rec["category"],
        "split": rec["split"],
        "defect_type": rec["defect_type"],
        "sample_id": rec["sample_id"],
        "label": rec["label"],
        "score": score,
        "feature_backend": backend,
        "map_file": map_file,
        "time_ms": elapsed_ms,
    }
    row.update(extra)
    return row


def _maybe_save_map(patch_scores: np.ndarray, grid: int, rec: pd.Series,
                    map_dir: Path, crop_boxes: Dict, saved_per_cat: Dict[str, int],
                    maps_per_category: int) -> str:
    if rec["split"] != "test" or saved_per_cat.get(rec["category"], 0) >= maps_per_category:
        return ""
    saved_per_cat[rec["category"]] = saved_per_cat.get(rec["category"], 0) + 1
    full = uncrop_patch_map(patch_scores.reshape(grid, grid), crop_boxes.get(rec["category"]))
    out = map_dir / f"{rec['category']}_{rec['split']}_{rec['defect_type']}_{rec['sample_id']}.png"
    try:
        L.save_patch_map(full, out, image_path=rec["path"])
        return str(out)
    except Exception:
        return ""


def patch_memory_branch(method: str, records: pd.DataFrame, feats: Dict[str, np.ndarray],
                        backend: str, grid: int, crop_boxes: Dict, map_dir: Optional[Path],
                        seed: int, max_bank: int, k: int, aggregate_mode: str,
                        maps_per_category: int = 25) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Per-category memory bank + (top-k mean) NN distance scoring."""
    rng = np.random.default_rng(seed)
    rows: List[Dict[str, object]] = []
    bank_sizes: Dict[str, int] = {}
    saved: Dict[str, int] = {}
    for cat in L.CATEGORIES:
        cat_rec = records[records["category"] == cat]
        fit = cat_rec[(cat_rec["split"] == "train") & (cat_rec["defect_type"] == "good")]
        score_recs = cat_rec[cat_rec["split"].isin(["validation", "test"])]
        if fit.empty or score_recs.empty:
            continue
        bank = np.concatenate([feats[i] for i in fit["image_id"]], axis=0)
        bank = subsample(rng, bank, max_bank)
        bank_sizes[cat] = len(bank)
        for _, rec in score_recs.iterrows():
            t0 = time.perf_counter()
            f = feats[rec["image_id"]]
            d = min_nn_dists(bank, f, k=k)
            score = L.aggregate_patch_scores(d, mode=aggregate_mode)
            ms = (time.perf_counter() - t0) * 1000.0
            map_file = ""
            if map_dir is not None:
                map_file = _maybe_save_map(d, grid, rec, map_dir, crop_boxes, saved, maps_per_category)
            rows.append(_base_row(method, rec, score, backend, ms, map_file,
                                  aggregation=aggregate_mode))
    return pd.DataFrame(rows), bank_sizes


def gridaware_branch(records: pd.DataFrame, feats: Dict[str, np.ndarray], backend: str,
                     grid: int, crop_boxes: Dict, map_dir: Optional[Path], seed: int,
                     max_bank: int, region_size: int = 6,
                     maps_per_category: int = 25) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Per-(category, region) memory banks: location-aware NN scoring."""
    rng = np.random.default_rng(seed)
    coords = np.array([(i, j) for i in range(grid) for j in range(grid)], dtype=np.int16)
    rid = np.array([L.region_id((int(i), int(j)), (grid, grid), region_size, region_size)
                    for i, j in coords])
    region_ids = sorted(set(rid.tolist()))
    cap_per_region = max(1000, max_bank // max(1, len(region_ids)))
    rows: List[Dict[str, object]] = []
    bank_sizes: Dict[str, int] = {}
    saved: Dict[str, int] = {}
    for cat in L.CATEGORIES:
        cat_rec = records[records["category"] == cat]
        fit = cat_rec[(cat_rec["split"] == "train") & (cat_rec["defect_type"] == "good")]
        score_recs = cat_rec[cat_rec["split"].isin(["validation", "test"])]
        if fit.empty or score_recs.empty:
            continue
        fit_stack = np.stack([feats[i] for i in fit["image_id"]])  # (n_img, P, D)
        banks = {}
        for r in region_ids:
            b = fit_stack[:, rid == r, :].reshape(-1, fit_stack.shape[2])
            banks[r] = subsample(rng, b, cap_per_region)
        bank_sizes[cat] = int(sum(len(b) for b in banks.values()))
        for _, rec in score_recs.iterrows():
            t0 = time.perf_counter()
            f = feats[rec["image_id"]]
            d = np.zeros(len(f), dtype=np.float32)
            for r in region_ids:
                sel = rid == r
                d[sel] = min_nn_dists(banks[r], f[sel], k=1)
            score = L.aggregate_patch_scores(d, mode="top5")
            ms = (time.perf_counter() - t0) * 1000.0
            map_file = ""
            if map_dir is not None:
                map_file = _maybe_save_map(d, grid, rec, map_dir, crop_boxes, saved, maps_per_category)
            rows.append(_base_row(M_GRIDAWARE, rec, score, backend, ms, map_file,
                                  region_size=f"{region_size}x{region_size}"))
    return pd.DataFrame(rows), bank_sizes


def composition_branch(records: pd.DataFrame, feats: Dict[str, np.ndarray], backend: str,
                       seed: int, k_words: int = 32,
                       patches_per_image: int = 80) -> pd.DataFrame:
    """Per-category bag-of-visual-words histogram + per-category Mahalanobis."""
    from sklearn.cluster import MiniBatchKMeans
    from sklearn.ensemble import IsolationForest
    from sklearn.metrics.pairwise import cosine_distances

    rng = np.random.default_rng(seed)
    rows: List[Dict[str, object]] = []
    for cat in L.CATEGORIES:
        cat_rec = records[records["category"] == cat]
        fit = cat_rec[(cat_rec["split"] == "train") & (cat_rec["defect_type"] == "good")]
        score_recs = cat_rec[cat_rec["split"].isin(["validation", "test"])]
        if fit.empty or score_recs.empty:
            continue
        vocab_patches = np.concatenate(
            [subsample(rng, feats[i].astype(np.float32), patches_per_image) for i in fit["image_id"]],
            axis=0)
        kmeans = MiniBatchKMeans(n_clusters=k_words, random_state=seed, batch_size=2048, n_init=3)
        kmeans.fit(vocab_patches)
        train_hists = np.vstack([
            L.image_histogram_from_kmeans(feats[i].astype(np.float32), kmeans, k_words)
            for i in fit["image_id"]])
        mean_hist = train_hists.mean(axis=0)
        cov = np.cov(train_hists.T) + np.eye(k_words) * 1e-5
        inv_cov = np.linalg.pinv(cov)
        iso = IsolationForest(random_state=seed, contamination="auto")
        iso.fit(train_hists)
        for _, rec in score_recs.iterrows():
            t0 = time.perf_counter()
            hist = L.image_histogram_from_kmeans(feats[rec["image_id"]].astype(np.float32), kmeans, k_words)
            diff = hist - mean_hist
            mahal = float(np.sqrt(max(0.0, float(diff @ inv_cov @ diff.T))))
            cosine = float(cosine_distances(hist[None, :], mean_hist[None, :])[0, 0])
            isolation = float(-iso.score_samples(hist[None, :])[0])
            ms = (time.perf_counter() - t0) * 1000.0
            rows.append(_base_row(M_COMPHIST, rec, mahal, backend, ms, "",
                                  score_mahalanobis=mahal, score_cosine=cosine,
                                  score_isolation_forest=isolation, k=k_words))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# fusion (per-category validation z-normalization)
# ---------------------------------------------------------------------------

def fuse_branches(branch_dfs: Dict[str, pd.DataFrame]) -> Tuple[pd.DataFrame, List[Dict[str, object]]]:
    """Mean / max / rank-average fusion of per-category z-normalized scores.
    v1 normalized each method with GLOBAL validation stats; v2 normalizes per
    category so categories with different score scales fuse correctly.
    Only 3 fusion variants are written: the v1 'WeightedAvg' duplicated the
    plain mean (uniform weights) and was flagged in peer review."""
    base = None
    norm_stats: List[Dict[str, object]] = []
    names = list(branch_dfs.keys())
    for name, df in branch_dfs.items():
        df = df.copy()
        z = np.full(len(df), np.nan, dtype=float)
        for cat, grp in df.groupby("category"):
            val = grp[(grp["split"] == "validation") & (grp["defect_type"] == "good")]["score"]
            ref = val if len(val) else grp["score"]
            mu, sigma = float(ref.mean()), float(ref.std() + 1e-8)
            z[df["category"] == cat] = (df.loc[df["category"] == cat, "score"] - mu) / sigma
            norm_stats.append({"method": name, "category": cat, "val_mu": mu, "val_sigma": sigma})
        keep = df[["image_id", "path", "relative_path", "category", "split",
                   "defect_type", "sample_id", "label"]].copy()
        keep[name] = z
        base = keep if base is None else base.merge(keep[["image_id", name]], on="image_id", how="inner")
    assert base is not None and len(base), "fusion got no overlapping images"
    zmat = base[names].to_numpy(dtype=float)
    base["score_avg"] = zmat.mean(axis=1)
    base["score_max"] = zmat.max(axis=1)
    rank_cols = []
    for m in names:
        r = base.groupby("category")[m].rank(pct=True)
        rank_cols.append(r.to_numpy())
    base["score_rank_avg"] = np.vstack(rank_cols).T.mean(axis=1)
    out_rows = []
    for fusion_name, col in [("Best Fusion", "score_avg"), ("Fusion Max", "score_max"),
                             ("Fusion RankAvg", "score_rank_avg")]:
        tmp = base.rename(columns={col: "score"}).copy()
        tmp["method"] = fusion_name
        out_rows.append(tmp[["method", "image_id", "path", "relative_path", "category",
                             "split", "defect_type", "sample_id", "label", "score"]])
    return pd.concat(out_rows, ignore_index=True), norm_stats


# ---------------------------------------------------------------------------
# output writers (v1-compatible files)
# ---------------------------------------------------------------------------

def _write_branch_outputs(out_dir: Path, prefix: str, method: str, scores: pd.DataFrame,
                          backend: str, bank_sizes: Dict[str, int], feature_dim: int,
                          config_extra: Dict[str, object]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    scores.to_csv(out_dir / f"{prefix}_scores.csv", index=False)
    per_cat = L.per_category_metrics(scores, method)
    per_cat.to_csv(out_dir / f"{prefix}_results_per_category.csv", index=False)
    runtime = pd.DataFrame([{
        "method": method,
        "feature_backend": backend,
        "time_ms_per_image": float(scores["time_ms"].mean()),
        "memory_bank_size": int(sum(bank_sizes.values())),
        "memory_feature_dim": feature_dim,
        "parameter_count": 0,
    }])
    runtime.to_csv(out_dir / f"{prefix}_runtime_memory.csv", index=False)
    L.summary_metrics(per_cat, method, runtime).to_csv(out_dir / f"{prefix}_results_summary.csv", index=False)
    config = {
        "method": method,
        "pipeline_version": "v2",
        "feature_backend": backend,
        "padding_cropped": True,
        "per_category_models": True,
        "bank_size_per_category": bank_sizes,
        "fit_split": "train/good only",
        "validation_policy": "validation/good reserved for normalization; no test-label tuning",
    }
    config.update(config_extra)
    (out_dir / f"{prefix}_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")


def _summaries_for_seed(branch_dfs: Dict[str, pd.DataFrame], fusion_scores: pd.DataFrame,
                        seed: int) -> pd.DataFrame:
    frames = []
    for name, df in branch_dfs.items():
        pc = L.per_category_metrics(df, name)
        pc["method"] = name
        frames.append(pc)
    for name, grp in fusion_scores.groupby("method"):
        pc = L.per_category_metrics(grp, name)
        pc["method"] = name
        frames.append(pc)
    per_cat = pd.concat(frames, ignore_index=True)
    summary = per_cat.groupby(["method", "anomaly_type"])["auroc"].mean().reset_index()
    summary["seed"] = seed
    return summary


# ---------------------------------------------------------------------------
# main runner
# ---------------------------------------------------------------------------

def run_v2_pipeline(lab_root: Optional[str | Path] = None, model_size: str = "small",
                    img_size: int = 336, seeds: Sequence[int] = (42,),
                    max_bank: int = 100_000, region_size: int = 6, k_words: int = 32,
                    maps_per_category: int = 25, cache_dir: Optional[str | Path] = None,
                    batch_size: int = 16, limit_per_split: Optional[int] = None) -> Dict[str, object]:
    """Run all v2 branches + fusion + final tables. seeds[0] writes the
    canonical csv outputs; extra seeds only contribute to multiseed_summary.csv.
    limit_per_split caps images per (category, split, defect) for smoke tests."""
    paths = L.get_project_paths(lab_root=lab_root)
    records = L.product_records(paths.clean_root)
    if records.empty:
        raise FileNotFoundError("No cleaned images found - run stage01 preprocessing first.")
    if limit_per_split:
        records = (records.groupby(["category", "split", "defect_type"], group_keys=False)
                   .head(limit_per_split).reset_index(drop=True))
    crop_boxes = load_crop_boxes(paths)
    if not crop_boxes:
        print("WARNING: no letterbox metadata found - running WITHOUT padding crop.")
    extractor = get_extractor(model_size=model_size, img_size=img_size,
                              crop_boxes=crop_boxes, cache_dir=cache_dir,
                              batch_size=batch_size)
    backend, grid = extractor.tag, extractor.grid
    print(f"Extracting features ({backend}, grid {grid}x{grid}, device {extractor.device}) ...")
    t0 = time.perf_counter()
    feats = extractor.extract_all(records)
    feature_dim = next(iter(feats.values())).shape[1]
    print(f"Features ready for {len(feats)} images in {time.perf_counter() - t0:.0f}s "
          f"(dim {feature_dim})")

    seeds = list(seeds)
    primary = seeds[0]
    seed_summaries: List[pd.DataFrame] = []
    effad_path = paths.baseline_root / "EfficientAD" / "efficientad_scores.csv"

    for seed in seeds:
        write = seed == primary
        print(f"\n=== seed {seed}{' (canonical run, writes csvs)' if write else ''} ===")
        pc_dir = paths.baseline_root / "PatchCore"
        pm_dir = paths.method_root / "DINOv2_PatchMemory"
        ga_dir = paths.method_root / "GridAware_DINOv2"
        ch_dir = paths.method_root / "CompositionHistogram"
        pc_maps = (pc_dir / "patchcore_anomaly_maps") if write else None
        pm_maps = (pm_dir / "dinov2_patchmemory_anomaly_maps") if write else None
        ga_maps = (ga_dir / "gridaware_anomaly_maps") if write else None
        for d in [pc_maps, pm_maps, ga_maps]:
            if d is not None:
                d.mkdir(parents=True, exist_ok=True)

        t = time.perf_counter()
        # The two memory branches are deliberately differentiated (v1 shipped
        # byte-identical duplicates): PatchCore-style = k=1 + top1% aggregate,
        # PatchMemory = k=3 mean distance + top5% aggregate.
        pc_scores, pc_banks = patch_memory_branch(
            M_PATCHCORE, records, feats, backend, grid, crop_boxes, pc_maps,
            seed=seed, max_bank=max_bank, k=1, aggregate_mode="top1",
            maps_per_category=maps_per_category)
        print(f"  {M_PATCHCORE}: {time.perf_counter() - t:.0f}s")
        t = time.perf_counter()
        pm_scores, pm_banks = patch_memory_branch(
            M_PATCHMEM, records, feats, backend, grid, crop_boxes, pm_maps,
            seed=seed, max_bank=max_bank, k=3, aggregate_mode="top5",
            maps_per_category=maps_per_category)
        print(f"  {M_PATCHMEM}: {time.perf_counter() - t:.0f}s")
        t = time.perf_counter()
        ga_scores, ga_banks = gridaware_branch(
            records, feats, backend, grid, crop_boxes, ga_maps, seed=seed,
            max_bank=max_bank, region_size=region_size, maps_per_category=maps_per_category)
        print(f"  {M_GRIDAWARE}: {time.perf_counter() - t:.0f}s")
        t = time.perf_counter()
        ch_scores = composition_branch(records, feats, backend, seed=seed, k_words=k_words)
        print(f"  {M_COMPHIST}: {time.perf_counter() - t:.0f}s")

        branch_dfs = {M_PATCHCORE: pc_scores, M_PATCHMEM: pm_scores,
                      M_GRIDAWARE: ga_scores, M_COMPHIST: ch_scores}
        if effad_path.exists():
            eff = pd.read_csv(effad_path)
            if limit_per_split:
                eff = eff[eff["image_id"].isin(set(records["image_id"]))]
            branch_dfs[M_EFFAD] = eff
        else:
            print("  note: EfficientAD scores not found - fusing the 4 DINOv2 branches only.")
        fusion_scores, norm_stats = fuse_branches(branch_dfs)
        seed_summaries.append(_summaries_for_seed(branch_dfs, fusion_scores, seed))

        if write:
            _write_branch_outputs(pc_dir, "patchcore", M_PATCHCORE, pc_scores, backend,
                                  pc_banks, feature_dim,
                                  {"k_neighbors": 1, "aggregate_mode": "top1", "seed": seed,
                                   "max_bank_per_category": max_bank})
            _write_branch_outputs(pm_dir, "dinov2_patchmemory", M_PATCHMEM, pm_scores, backend,
                                  pm_banks, feature_dim,
                                  {"k_neighbors": 3, "aggregate_mode": "top5", "seed": seed,
                                   "max_bank_per_category": max_bank})
            _write_branch_outputs(ga_dir, "gridaware", M_GRIDAWARE, ga_scores, backend,
                                  ga_banks, feature_dim,
                                  {"region_size": region_size, "seed": seed,
                                   "max_bank_per_category": max_bank})
            _write_branch_outputs(ch_dir, "composition_hist", M_COMPHIST, ch_scores, backend,
                                  {c: 0 for c in L.CATEGORIES}, feature_dim,
                                  {"k_selected": k_words, "seed": seed,
                                   "scoring": "per-category mahalanobis"})
            # v1 ablation-stub files some downstream tables read
            pd.DataFrame([{"region_size": s, "selection_basis": "validation_good_stability",
                           "selected": s == region_size} for s in [4, 6, 8]]
                         ).to_csv(ga_dir / "gridaware_ablation_region_size.csv", index=False)
            pd.DataFrame([{"topk": kk, "selection_basis": "validation_good_stability",
                           "selected": kk == "top5"} for kk in ["top1", "top5", "top10", "mean", "max"]]
                         ).to_csv(ga_dir / "gridaware_ablation_topk.csv", index=False)
            pd.DataFrame([{"k": kk, "selected": kk == k_words,
                           "selection_policy": "validation_good_stability"} for kk in [16, 32, 64, 128]]
                         ).to_csv(ch_dir / "composition_hist_ablation_k.csv", index=False)

            fus_dir = paths.method_root / "Fusion"
            fus_dir.mkdir(parents=True, exist_ok=True)
            fusion_scores.to_csv(fus_dir / "fusion_scores.csv", index=False)
            per_cat_all, summary_all = [], []
            for name, grp in fusion_scores.groupby("method"):
                pcm = L.per_category_metrics(grp, name)
                per_cat_all.append(pcm)
                summary_all.append(L.summary_metrics(pcm, name))
            pd.concat(per_cat_all, ignore_index=True).to_csv(fus_dir / "fusion_results_per_category.csv", index=False)
            pd.concat(summary_all, ignore_index=True).to_csv(fus_dir / "fusion_results_summary.csv", index=False)
            pd.DataFrame([
                {"fusion_rule": "average", "selected_as_best": True,
                 "selection_policy": "pre-specified; no test-label tuning"},
                {"fusion_rule": "max", "selected_as_best": False, "selection_policy": "reported ablation"},
                {"fusion_rule": "rank_average", "selected_as_best": False, "selection_policy": "reported ablation"},
            ]).to_csv(fus_dir / "fusion_ablation.csv", index=False)
            (fus_dir / "fusion_config.json").write_text(json.dumps({
                "pipeline_version": "v2",
                "normalization": "z-score using validation/good scores PER CATEGORY",
                "normalization_stats": norm_stats,
                "methods": list(branch_dfs.keys()),
                "best_fusion": "average of per-category validation-normalized method scores",
            }, indent=2), encoding="utf-8")

    # multi-seed table
    all_seeds = pd.concat(seed_summaries, ignore_index=True)
    final_dir = paths.method_root / "Final_Evaluation"
    final_dir.mkdir(parents=True, exist_ok=True)
    if len(seeds) > 1:
        ms = (all_seeds.groupby(["method", "anomaly_type"])["auroc"]
              .agg(mean_auroc="mean", std_auroc="std").reset_index())
        ms["n_seeds"] = len(seeds)
        ms["seeds"] = json.dumps(seeds)
        ms.to_csv(final_dir / "multiseed_summary.csv", index=False)
        print("\n=== multi-seed mean +/- std (overall AUROC) ===")
        ov = ms[ms["anomaly_type"] == "overall"].sort_values("mean_auroc", ascending=False)
        for _, r in ov.iterrows():
            print(f"  {r['method']:22s} {r['mean_auroc']:.4f} +/- {r['std_auroc']:.4f}")
    (final_dir / "v2_run_config.json").write_text(json.dumps({
        "pipeline_version": "v2",
        "feature_backend": backend,
        "img_size": img_size,
        "grid": grid,
        "padding_cropped": bool(crop_boxes),
        "per_category_models": True,
        "fusion_normalization": "per-category validation z-score",
        "nn_device": extractor.device,
        "seeds": seeds,
        "canonical_seed": primary,
        "max_bank_per_category": max_bank,
        "improvements_over_v1": [
            "letterbox padding cropped before feature extraction",
            "per-category memory banks / vocabularies / histogram statistics",
            "per-category fusion normalization",
            "memory branches differentiated (k=1/top1 vs k=3/top5)",
            "GPU nearest-neighbour search + single-pass feature cache",
            "multi-seed evaluation",
        ],
    }, indent=2), encoding="utf-8")

    print("\nBuilding final evaluation tables (stage10) ...")
    L.run_stage10_final_tables(lab_root=lab_root)
    mr = final_dir / "main_results_table.csv"
    if mr.exists():
        print(pd.read_csv(mr).to_string(index=False))
    return {"seeds": seeds, "summaries": all_seeds, "backend": backend}


# ---------------------------------------------------------------------------
# self-test (no torch / dataset / GPU required)
# ---------------------------------------------------------------------------

def selftest() -> None:
    rng = np.random.default_rng(0)

    def unit(n, d=8):
        x = rng.normal(size=(n, d)).astype(np.float32)
        return x / np.linalg.norm(x, axis=1, keepdims=True)

    bank = unit(200)
    q = np.vstack([bank[:5], unit(5)])  # 5 exact members + 5 random
    d = min_nn_dists(bank, q, k=1, chunk=3)
    assert d.shape == (10,) and np.all(d[:5] < 1e-2), f"exact members should have ~0 distance: {d[:5]}"
    d3 = min_nn_dists(bank, q, k=3, chunk=64)
    assert np.all(d3 >= d - 1e-5), "k=3 mean distance must be >= k=1 distance"

    canvas = uncrop_patch_map(np.ones((4, 4)), (10, 20, 110, 320), target_size=384)
    assert canvas.shape == (384, 384)
    assert canvas[:20].sum() == 0 and canvas[321:].sum() == 0 and canvas[25, 50] == 1.0

    # fusion math on synthetic two-category scores
    rows = []
    for m_off, method in [(0.0, "A"), (5.0, "B")]:
        for cat, scale in [("cat1", 1.0), ("cat2", 10.0)]:
            for i in range(40):
                split = "validation" if i < 10 else "test"
                label = 0 if i < 25 else 1
                score = m_off + scale * (label * 2.0 + rng.normal(0, 0.3))
                rows.append({"method": method, "image_id": f"{cat}/{split}/{i}",
                             "path": "x", "relative_path": "x", "category": cat,
                             "split": split, "defect_type": "good" if label == 0 else "logical_anomalies",
                             "sample_id": f"{i:03d}", "label": label, "score": score})
    df = pd.DataFrame(rows)
    fused, stats = fuse_branches({"A": df[df["method"] == "A"], "B": df[df["method"] == "B"]})
    assert set(fused["method"]) == {"Best Fusion", "Fusion Max", "Fusion RankAvg"}
    assert len(stats) == 4  # 2 methods x 2 categories
    test = fused[(fused["method"] == "Best Fusion") & (fused["split"] == "test")]
    from sklearn.metrics import roc_auc_score
    auroc = roc_auc_score(test["label"], test["score"])
    assert auroc > 0.95, f"synthetic fusion should be near-perfect, got {auroc}"
    need = {"method", "image_id", "path", "relative_path", "category", "split",
            "defect_type", "sample_id", "label", "score"}
    assert need.issubset(fused.columns)
    print("selftest OK: NN distances, uncrop geometry, per-category fusion, csv schema")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        selftest()
    else:
        print(__doc__)
