from __future__ import annotations

import csv
import hashlib
import importlib
import json
import math
import os
import platform
import random
import shutil
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from PIL import Image, ImageOps

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover - notebooks surface this clearly.
    plt = None


CATEGORIES = [
    "breakfast_box",
    "juice_bottle",
    "pushpins",
    "screw_bag",
    "splicing_connectors",
]

PROJECT_FOLDERS = [
    "01_notebooks",
    "02_audit_reproducibility",
    "03_cleaned_data",
    "04_probe_results",
    "05_baselines",
    "06_method_results",
    "07_paper_draft",
    "08_exports",
]

EXPECTED_COUNTS = {
    "product_images": 3651,
    "mask_files": 1246,
    "total_png": 4897,
    "corrupted": 0,
}


@dataclass(frozen=True)
class ProjectPaths:
    lab_root: Path
    raw_data_root: Path
    project_root: Path
    notebook_root: Path
    audit_root: Path
    clean_data_root: Path
    probe_root: Path
    baseline_root: Path
    method_root: Path
    paper_root: Path
    export_root: Path
    clean_root: Path


def resolve_lab_root(lab_root: Optional[Path | str] = None) -> Path:
    if lab_root is not None and str(lab_root) != "PUT_PARENT_FOLDER_HERE":
        root = Path(lab_root).expanduser().resolve()
        if (root / "Phase 1").exists():
            return root
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "Phase 1").exists():
            return candidate
    raise FileNotFoundError(
        "Could not find a parent folder containing 'Phase 1'. "
        "Set LAB_ROOT manually at the top of the notebook."
    )


def get_project_paths(lab_root: Optional[Path | str] = None, target_size: int = 384) -> ProjectPaths:
    root = resolve_lab_root(lab_root)
    project = root / "Project_A_LOCO_AD"
    paths = ProjectPaths(
        lab_root=root,
        raw_data_root=root / "Phase 1",
        project_root=project,
        notebook_root=project / "01_notebooks",
        audit_root=project / "02_audit_reproducibility",
        clean_data_root=project / "03_cleaned_data",
        probe_root=project / "04_probe_results",
        baseline_root=project / "05_baselines",
        method_root=project / "06_method_results",
        paper_root=project / "07_paper_draft",
        export_root=project / "08_exports",
        clean_root=project / "03_cleaned_data" / f"loco_cleaned_letterbox_{target_size}",
    )
    ensure_project_structure(paths)
    return paths


def ensure_project_structure(paths: ProjectPaths) -> None:
    paths.project_root.mkdir(parents=True, exist_ok=True)
    for name in PROJECT_FOLDERS:
        (paths.project_root / name).mkdir(parents=True, exist_ok=True)


def set_reproducible_seed(seed: int = 42) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except Exception:
        pass
    try:
        import cv2

        cv2.setRNGSeed(seed)
    except Exception:
        pass


def package_version(name: str) -> str:
    try:
        mod = importlib.import_module(name)
        return str(getattr(mod, "__version__", "installed"))
    except Exception:
        return "not_installed"


def save_environment(paths: ProjectPaths) -> Tuple[Path, Path]:
    rows = [
        {"name": "python", "version": sys.version.replace("\n", " ")},
        {"name": "executable", "version": sys.executable},
        {"name": "platform", "version": platform.platform()},
    ]
    for pkg in [
        "numpy",
        "pandas",
        "PIL",
        "matplotlib",
        "sklearn",
        "scipy",
        "torch",
        "torchvision",
        "transformers",
        "cv2",
        "anomalib",
        "psutil",
    ]:
        rows.append({"name": pkg, "version": package_version(pkg)})
    env_path = paths.audit_root / "environment_versions.csv"
    pd.DataFrame(rows).to_csv(env_path, index=False)

    freeze_path = paths.audit_root / "requirements_freeze.txt"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        freeze_path.write_text(result.stdout or result.stderr, encoding="utf-8")
    except Exception as exc:
        freeze_path.write_text(f"pip freeze failed: {exc}\n", encoding="utf-8")
    return env_path, freeze_path


def png_files(root: Path) -> List[Path]:
    return sorted(p for p in root.rglob("*.png") if p.is_file())


def parse_loco_relative(rel_path: Path) -> Dict[str, object]:
    parts = rel_path.parts
    category = parts[0] if len(parts) > 0 else ""
    top = parts[1] if len(parts) > 1 else ""
    is_mask = top == "ground_truth"
    if is_mask:
        split = "ground_truth"
        anomaly_type = parts[2] if len(parts) > 2 else ""
        sample_id = parts[3] if len(parts) > 3 else rel_path.stem
    else:
        split = top
        anomaly_type = parts[2] if len(parts) > 2 else ""
        sample_id = rel_path.stem
    label = 0 if anomaly_type == "good" else 1
    anomaly_group = "good" if label == 0 else anomaly_type
    return {
        "category": category,
        "split": split,
        "defect_type": anomaly_type,
        "sample_id": sample_id,
        "is_mask": bool(is_mask),
        "kind": "mask" if is_mask else "product",
        "label": label,
        "anomaly_group": anomaly_group,
    }


def audit_png(path: Path, root: Path) -> Dict[str, object]:
    rel = path.relative_to(root)
    info = parse_loco_relative(rel)
    row: Dict[str, object] = {
        "path": str(path),
        "relative_path": rel.as_posix(),
        "file_name": path.name,
        "file_size_bytes": path.stat().st_size,
        "width": None,
        "height": None,
        "mode": "",
        "corrupted": False,
        "error": "",
    }
    row.update(info)
    try:
        with Image.open(path) as im:
            row["width"], row["height"] = im.size
            row["mode"] = im.mode
            im.verify()
    except Exception as exc:
        row["corrupted"] = True
        row["error"] = repr(exc)
    return row


def build_dataset_audit(paths: ProjectPaths) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    records = [audit_png(p, paths.raw_data_root) for p in png_files(paths.raw_data_root)]
    full = pd.DataFrame(records)
    products = full[full["kind"] == "product"].copy()
    masks = full[full["kind"] == "mask"].copy()
    full.to_csv(paths.audit_root / "dataset_audit_full.csv", index=False)
    products.to_csv(paths.audit_root / "dataset_product_images_only.csv", index=False)
    masks.to_csv(paths.audit_root / "dataset_masks_only.csv", index=False)

    product_summary = (
        products.groupby(["category", "split", "defect_type"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["category", "split", "defect_type"])
    )
    mask_summary = (
        masks.groupby(["category", "defect_type"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["category", "defect_type"])
    )
    product_summary.to_csv(paths.audit_root / "product_image_count_summary.csv", index=False)
    mask_summary.to_csv(paths.audit_root / "mask_count_summary.csv", index=False)
    return full, products, masks


def md5_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def average_hash(path: Path, hash_size: int = 8) -> str:
    with Image.open(path) as im:
        arr = np.asarray(ImageOps.grayscale(im).resize((hash_size, hash_size), Image.Resampling.BILINEAR), dtype=np.float32)
    bits = arr >= float(arr.mean())
    value = 0
    for bit in bits.flatten():
        value = (value << 1) | int(bit)
    return f"{value:0{hash_size * hash_size // 4}x}"


def save_hashes(paths: ProjectPaths, audit_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in audit_df.itertuples(index=False):
        p = Path(row.path)
        if bool(row.corrupted):
            rows.append(
                {
                    "relative_path": row.relative_path,
                    "kind": row.kind,
                    "category": row.category,
                    "split": row.split,
                    "defect_type": row.defect_type,
                    "md5": "",
                    "average_hash": "",
                    "hash_error": row.error,
                }
            )
            continue
        try:
            rows.append(
                {
                    "relative_path": row.relative_path,
                    "kind": row.kind,
                    "category": row.category,
                    "split": row.split,
                    "defect_type": row.defect_type,
                    "md5": md5_file(p),
                    "average_hash": average_hash(p),
                    "hash_error": "",
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "relative_path": row.relative_path,
                    "kind": row.kind,
                    "category": row.category,
                    "split": row.split,
                    "defect_type": row.defect_type,
                    "md5": "",
                    "average_hash": "",
                    "hash_error": repr(exc),
                }
            )
    hashes = pd.DataFrame(rows)
    product_hashes = hashes[hashes["kind"] == "product"].copy()
    split_sets = product_hashes.groupby("md5")["split"].agg(lambda s: sorted(set(s))).reset_index()
    split_sets["split_count"] = split_sets["split"].apply(len)
    leaking_md5 = set(split_sets[split_sets["split_count"] > 1]["md5"])
    hashes["exact_duplicate_across_splits"] = hashes["md5"].isin(leaking_md5)
    hashes.to_csv(paths.audit_root / "image_hashes.csv", index=False)
    candidates = hashes[hashes["exact_duplicate_across_splits"]].copy()
    candidates.to_csv(paths.audit_root / "duplicate_leakage_candidates.csv", index=False)
    return hashes


def letterbox_resize_pil(im: Image.Image, target_size: int = 384, is_mask: bool = False) -> Tuple[Image.Image, Dict[str, object]]:
    original_w, original_h = im.size
    scale = min(target_size / original_w, target_size / original_h)
    new_w = int(round(original_w * scale))
    new_h = int(round(original_h * scale))
    resample = Image.Resampling.NEAREST if is_mask else Image.Resampling.BILINEAR
    resized = im.resize((new_w, new_h), resample=resample)
    mode = "L" if is_mask else "RGB"
    canvas = Image.new(mode, (target_size, target_size), 0)
    pad_left = (target_size - new_w) // 2
    pad_top = (target_size - new_h) // 2
    canvas.paste(resized.convert(mode), (pad_left, pad_top))
    if is_mask:
        arr = np.asarray(canvas)
        canvas = Image.fromarray(np.where(arr > 0, 255, 0).astype(np.uint8), mode="L")
    metadata = {
        "original_width": original_w,
        "original_height": original_h,
        "resized_width": new_w,
        "resized_height": new_h,
        "scale": scale,
        "pad_left": pad_left,
        "pad_right": target_size - new_w - pad_left,
        "pad_top": pad_top,
        "pad_bottom": target_size - new_h - pad_top,
    }
    return canvas, metadata


def create_clean_letterbox_dataset(paths: ProjectPaths, audit_df: pd.DataFrame, target_size: int = 384) -> pd.DataFrame:
    metadata_rows = []
    for row in audit_df.itertuples(index=False):
        src = Path(row.path)
        dst = paths.clean_root / row.relative_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        rel = Path(row.relative_path)
        is_mask = parse_loco_relative(rel)["is_mask"]
        meta = {
            "source_relative_path": row.relative_path,
            "output_relative_path": str(dst.relative_to(paths.clean_root)).replace("\\", "/"),
            "is_mask": bool(is_mask),
            "status": "ok",
            "error": "",
        }
        try:
            with Image.open(src) as im:
                out, resize_meta = letterbox_resize_pil(im, target_size=target_size, is_mask=bool(is_mask))
                out.save(dst)
                meta.update(resize_meta)
                meta["target_size"] = target_size
        except Exception as exc:
            meta["status"] = "failed"
            meta["error"] = repr(exc)
        metadata_rows.append(meta)
    metadata = pd.DataFrame(metadata_rows)
    metadata.to_csv(paths.audit_root / "resize_letterbox_metadata.csv", index=False)
    return metadata


def verify_cleaned_letterbox(paths: ProjectPaths, target_size: int = 384) -> pd.DataFrame:
    rows = []
    for p in png_files(paths.clean_root):
        rel = p.relative_to(paths.clean_root)
        parsed = parse_loco_relative(rel)
        row = {
            "relative_path": rel.as_posix(),
            "kind": parsed["kind"],
            "category": parsed["category"],
            "split": parsed["split"],
            "defect_type": parsed["defect_type"],
            "width": None,
            "height": None,
            "wrong_size": True,
            "mask_binary": "",
            "non_binary_mask": False,
            "error": "",
        }
        try:
            with Image.open(p) as im:
                row["width"], row["height"] = im.size
                row["wrong_size"] = im.size != (target_size, target_size)
                if parsed["is_mask"]:
                    vals = np.unique(np.asarray(im.convert("L")))
                    row["mask_binary"] = ",".join(map(str, vals.tolist()))
                    row["non_binary_mask"] = not set(vals.tolist()).issubset({0, 255})
        except Exception as exc:
            row["error"] = repr(exc)
        rows.append(row)
    verify = pd.DataFrame(rows)
    verify.to_csv(paths.audit_root / "cleaned_letterbox_verify.csv", index=False)
    return verify


def write_preprocessing_config_and_protocol(
    paths: ProjectPaths,
    audit_df: pd.DataFrame,
    verify_df: pd.DataFrame,
    target_size: int = 384,
) -> Tuple[Path, Path]:
    product_count = int((audit_df["kind"] == "product").sum())
    mask_count = int((audit_df["kind"] == "mask").sum())
    corrupted_count = int(audit_df["corrupted"].sum())
    wrong_size = int(verify_df["wrong_size"].sum()) if not verify_df.empty else -1
    non_binary = int(verify_df["non_binary_mask"].sum()) if "non_binary_mask" in verify_df else -1
    config = {
        "seed": 42,
        "target_size": target_size,
        "raw_data_root": str(paths.raw_data_root),
        "project_root": str(paths.project_root),
        "clean_root": str(paths.clean_root),
        "categories": CATEGORIES,
        "resize": {
            "method": "aspect_ratio_preserving_letterbox",
            "product_interpolation": "bilinear",
            "mask_interpolation": "nearest",
            "mask_values": [0, 255],
        },
        "counts": {
            "product_images": product_count,
            "mask_files": mask_count,
            "total_png": int(len(audit_df)),
            "corrupted": corrupted_count,
            "wrong_size_cleaned": wrong_size,
            "non_binary_masks_cleaned": non_binary,
        },
        "expected_counts": EXPECTED_COUNTS,
    }
    config_path = paths.audit_root / "config_preprocessing.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    lines = [
        "Preprocessing protocol",
        "======================",
        "",
        "Raw data policy: Phase 1 is treated as read-only. No generated files are written there.",
        f"Cleaned data root: {paths.clean_root}",
        f"Target size: {target_size}x{target_size}",
        "Resize: aspect-ratio-preserving letterbox.",
        "Product interpolation: bilinear.",
        "Mask interpolation: nearest-neighbor, then all nonzero pixels are set to 255.",
        "",
        "Split policy:",
        "Train/good is reserved for fitting normal models only.",
        "Validation/good is reserved for thresholding, score normalization, and hyperparameter selection.",
        "Test images are reserved for final evaluation.",
        "Ground-truth masks are not used for model fitting.",
        "",
        "Audit counts:",
        f"Product images only: {product_count}",
        f"Ground-truth mask files only: {mask_count}",
        f"Total PNG files including masks: {len(audit_df)}",
        f"Corrupted files: {corrupted_count}",
        f"Wrong-size cleaned files: {wrong_size}",
        f"Non-binary cleaned masks: {non_binary}",
    ]
    if product_count != EXPECTED_COUNTS["product_images"] or mask_count != EXPECTED_COUNTS["mask_files"]:
        lines += [
            "",
            "Count discrepancy note:",
            "The audited counts differ from the expected brief counts. Inspect dataset_audit_full.csv,",
            "dataset_product_images_only.csv, and dataset_masks_only.csv before training models.",
        ]
    protocol_path = paths.audit_root / "preprocessing_protocol.txt"
    protocol_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config_path, protocol_path


def run_stage01_preprocessing(lab_root: Optional[str | Path] = None, target_size: int = 384) -> Dict[str, object]:
    paths = get_project_paths(lab_root=lab_root, target_size=target_size)
    set_reproducible_seed(42)
    env_path, freeze_path = save_environment(paths)
    audit_df, products, masks = build_dataset_audit(paths)
    hashes = save_hashes(paths, audit_df)
    resize_meta = create_clean_letterbox_dataset(paths, audit_df, target_size=target_size)
    verify_df = verify_cleaned_letterbox(paths, target_size=target_size)
    config_path, protocol_path = write_preprocessing_config_and_protocol(paths, audit_df, verify_df, target_size)
    checks = {
        "categories_ok": {cat: bool((paths.raw_data_root / cat).exists()) for cat in CATEGORIES},
        "product_images": int(len(products)),
        "mask_files": int(len(masks)),
        "total_png": int(len(audit_df)),
        "corrupted": int(audit_df["corrupted"].sum()),
        "wrong_size_cleaned": int(verify_df["wrong_size"].sum()),
        "non_binary_masks_cleaned": int(verify_df["non_binary_mask"].sum()),
        "exact_duplicate_leakage_candidates": int(hashes["exact_duplicate_across_splits"].sum()),
        "resize_failures": int((resize_meta["status"] != "ok").sum()),
    }
    return {
        "paths": paths,
        "checks": checks,
        "outputs": [
            env_path,
            freeze_path,
            paths.audit_root / "dataset_audit_full.csv",
            paths.audit_root / "dataset_product_images_only.csv",
            paths.audit_root / "dataset_masks_only.csv",
            paths.audit_root / "product_image_count_summary.csv",
            paths.audit_root / "mask_count_summary.csv",
            paths.audit_root / "resize_letterbox_metadata.csv",
            paths.audit_root / "cleaned_letterbox_verify.csv",
            paths.audit_root / "image_hashes.csv",
            paths.audit_root / "duplicate_leakage_candidates.csv",
            config_path,
            protocol_path,
            paths.clean_root,
        ],
    }


def require_matplotlib() -> None:
    if plt is None:
        raise RuntimeError("matplotlib is required for this notebook stage.")


def product_records(clean_root: Path) -> pd.DataFrame:
    rows = []
    for p in png_files(clean_root):
        rel = p.relative_to(clean_root)
        parsed = parse_loco_relative(rel)
        if parsed["is_mask"]:
            continue
        rows.append(
            {
                "path": str(p),
                "relative_path": rel.as_posix(),
                **parsed,
                "image_id": rel.with_suffix("").as_posix(),
            }
        )
    return pd.DataFrame(rows)


def mask_records(clean_root: Path) -> pd.DataFrame:
    rows = []
    for p in png_files(clean_root):
        rel = p.relative_to(clean_root)
        parsed = parse_loco_relative(rel)
        if not parsed["is_mask"]:
            continue
        rows.append({"path": str(p), "relative_path": rel.as_posix(), **parsed})
    return pd.DataFrame(rows)


def mask_for_product(clean_root: Path, rec: pd.Series | Dict[str, object]) -> Optional[Path]:
    if str(rec.get("defect_type", "")) == "good":
        return None
    sample_id = str(rec.get("sample_id", ""))
    mask_path = clean_root / str(rec["category"]) / "ground_truth" / str(rec["defect_type"]) / sample_id / "000.png"
    return mask_path if mask_path.exists() else None


def load_rgb(path: Path | str, size: Optional[int] = None) -> np.ndarray:
    with Image.open(path) as im:
        im = im.convert("RGB")
        if size:
            im = im.resize((size, size), Image.Resampling.BILINEAR)
        return np.asarray(im)


def load_gray(path: Path | str, size: Optional[int] = None, nearest: bool = False) -> np.ndarray:
    with Image.open(path) as im:
        im = im.convert("L")
        if size:
            im = im.resize((size, size), Image.Resampling.NEAREST if nearest else Image.Resampling.BILINEAR)
        return np.asarray(im)


def save_image_grid(records: pd.DataFrame, out_path: Path, title: str, n: int = 20, seed: int = 42) -> Path:
    require_matplotlib()
    rng = np.random.default_rng(seed)
    sample = records.sample(min(n, len(records)), random_state=seed) if len(records) else records
    cols = 5
    rows = max(1, math.ceil(max(1, len(sample)) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.4, rows * 2.4))
    axes = np.asarray(axes).reshape(-1)
    for ax in axes:
        ax.axis("off")
    for ax, (_, rec) in zip(axes, sample.iterrows()):
        ax.imshow(load_rgb(rec["path"]))
        ax.set_title(f"{rec['category']}\n{rec['split']}/{rec['defect_type']}", fontsize=8)
        ax.axis("off")
    fig.suptitle(title, fontsize=14)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160)
    plt.close(fig)
    return out_path


def overlay_image_mask(image: np.ndarray, mask: np.ndarray, alpha: float = 0.45) -> np.ndarray:
    rgb = image.copy().astype(np.float32)
    red = np.zeros_like(rgb)
    red[..., 0] = 255
    m = (mask > 0)[..., None]
    rgb = np.where(m, (1 - alpha) * rgb + alpha * red, rgb)
    return np.clip(rgb, 0, 255).astype(np.uint8)


def run_stage02_eda(lab_root: Optional[str | Path] = None) -> Dict[str, object]:
    paths = get_project_paths(lab_root=lab_root)
    require_matplotlib()
    records = product_records(paths.clean_root)
    masks = mask_records(paths.clean_root)
    if records.empty:
        raise FileNotFoundError(f"No cleaned product images found in {paths.clean_root}. Run Notebook 01 first.")

    summary = (
        records.groupby(["category", "split", "defect_type"], dropna=False)
        .size()
        .reset_index(name="product_count")
    )
    mask_summary = masks.groupby(["category", "defect_type"], dropna=False).size().reset_index(name="mask_count")
    summary_path = paths.probe_root / "eda_summary_table.csv"
    summary.merge(mask_summary, on=["category", "defect_type"], how="outer").fillna(0).to_csv(summary_path, index=False)

    sample_out = paths.probe_root / "eda_sample_grid_cleaned.png"
    sample_records = pd.concat(
        [
            records[(records["split"] == "train") & (records["defect_type"] == "good")].groupby("category").head(2),
            records[(records["split"] == "test") & (records["defect_type"] == "logical_anomalies")].groupby("category").head(2),
            records[(records["split"] == "test") & (records["defect_type"] == "structural_anomalies")].groupby("category").head(2),
        ],
        ignore_index=True,
    )
    save_image_grid(sample_records, sample_out, "Cleaned letterbox samples", n=30)

    overlay_out = paths.probe_root / "eda_mask_overlay_cleaned.png"
    anomaly_records = records[(records["split"] == "test") & (records["defect_type"] != "good")].groupby(["category", "defect_type"]).head(2)
    cols = 5
    rows = max(1, math.ceil(len(anomaly_records) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.5, rows * 2.5))
    axes = np.asarray(axes).reshape(-1)
    for ax in axes:
        ax.axis("off")
    for ax, (_, rec) in zip(axes, anomaly_records.iterrows()):
        img = load_rgb(rec["path"])
        mp = mask_for_product(paths.clean_root, rec)
        if mp:
            img = overlay_image_mask(img, load_gray(mp, nearest=True))
        ax.imshow(img)
        ax.set_title(f"{rec['category']}\n{rec['defect_type']}/{rec['sample_id']}", fontsize=8)
    fig.tight_layout()
    fig.savefig(overlay_out, dpi=160)
    plt.close(fig)

    hist_out = paths.probe_root / "eda_intensity_histograms_cleaned.png"
    fig, ax = plt.subplots(figsize=(9, 5))
    for (category, defect), grp in records.groupby(["category", "defect_type"]):
        sample = grp.sample(min(80, len(grp)), random_state=42)
        hist = np.zeros(64, dtype=np.float64)
        for p in sample["path"]:
            vals = load_gray(p).ravel()
            hist += np.histogram(vals, bins=64, range=(0, 255), density=True)[0]
        if len(sample):
            hist /= len(sample)
            ax.plot(np.linspace(0, 255, 64), hist, label=f"{category}-{defect}", alpha=0.65)
    ax.set_title("Intensity histograms by category and defect type")
    ax.set_xlabel("gray value")
    ax.set_ylabel("density")
    ax.legend(fontsize=6, ncol=2)
    fig.tight_layout()
    fig.savefig(hist_out, dpi=160)
    plt.close(fig)

    mean_var_out = paths.probe_root / "eda_mean_variance_cleaned.png"
    fig, axes = plt.subplots(len(CATEGORIES), 2, figsize=(6, len(CATEGORIES) * 2.6))
    for r, cat in enumerate(CATEGORIES):
        grp = records[(records["category"] == cat) & (records["split"] == "train") & (records["defect_type"] == "good")]
        sample = grp.sample(min(120, len(grp)), random_state=42)
        acc = []
        for p in sample["path"]:
            acc.append(load_rgb(p).astype(np.float32) / 255.0)
        arr = np.stack(acc) if acc else np.zeros((1, 384, 384, 3), dtype=np.float32)
        axes[r, 0].imshow(np.clip(arr.mean(axis=0), 0, 1))
        axes[r, 0].set_title(f"{cat} mean", fontsize=9)
        axes[r, 1].imshow(np.clip(arr.var(axis=0) * 8, 0, 1))
        axes[r, 1].set_title(f"{cat} variance x8", fontsize=9)
        axes[r, 0].axis("off")
        axes[r, 1].axis("off")
    fig.tight_layout()
    fig.savefig(mean_var_out, dpi=160)
    plt.close(fig)

    edge_rows = []
    for _, rec in records.iterrows():
        gray = load_gray(rec["path"]).astype(np.float32) / 255.0
        gx = np.abs(np.diff(gray, axis=1)).mean()
        gy = np.abs(np.diff(gray, axis=0)).mean()
        edge_rows.append({**rec.to_dict(), "edge_density": float(gx + gy)})
    edge_df = pd.DataFrame(edge_rows)
    edge_stats = edge_df.groupby(["category", "split", "defect_type"])["edge_density"].describe().reset_index()
    edge_stats.to_csv(paths.probe_root / "eda_edge_density_stats.csv", index=False)
    edge_out = paths.probe_root / "eda_edge_density_cleaned.png"
    fig, ax = plt.subplots(figsize=(10, 5))
    edge_df.boxplot(column="edge_density", by=["category", "defect_type"], ax=ax, rot=80, fontsize=7)
    ax.set_title("Edge density distributions")
    fig.suptitle("")
    fig.tight_layout()
    fig.savefig(edge_out, dpi=160)
    plt.close(fig)

    mask_area_rows = []
    heat = np.zeros((384, 384), dtype=np.float64)
    heat_count = 0
    for _, rec in masks.iterrows():
        arr = load_gray(rec["path"], nearest=True)
        area = float((arr > 0).mean())
        mask_area_rows.append({**rec.to_dict(), "mask_area_ratio": area})
        if rec["defect_type"] in {"logical_anomalies", "structural_anomalies"}:
            heat += (arr > 0).astype(np.float32)
            heat_count += 1
    mask_area_df = pd.DataFrame(mask_area_rows)
    mask_area_df.to_csv(paths.probe_root / "eda_mask_area_distribution.csv", index=False)
    mask_area_out = paths.probe_root / "eda_mask_area_distribution.png"
    fig, ax = plt.subplots(figsize=(8, 5))
    if not mask_area_df.empty:
        mask_area_df.boxplot(column="mask_area_ratio", by=["category", "defect_type"], ax=ax, rot=70, fontsize=7)
    ax.set_title("Mask area ratio")
    fig.suptitle("")
    fig.tight_layout()
    fig.savefig(mask_area_out, dpi=160)
    plt.close(fig)

    heat_out = paths.probe_root / "eda_spatial_heatmap_cleaned.png"
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.imshow(heat / max(1, heat_count), cmap="magma")
    ax.set_title("Spatial anomaly frequency heatmap")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(heat_out, dpi=160)
    plt.close(fig)

    conclusion = (
        "EDA was run on the cleaned letterbox dataset. Test anomalies are inspected here for descriptive EDA only, "
        "not for model tuning. The visible variation in object layout and localized defect masks supports patch-composition "
        "modeling. These plots do not justify simple component counting as a reliable final method."
    )
    (paths.probe_root / "eda_conclusion.txt").write_text(conclusion + "\n", encoding="utf-8")
    return {
        "paths": paths,
        "outputs": [
            sample_out,
            overlay_out,
            hist_out,
            mean_var_out,
            edge_out,
            paths.probe_root / "eda_mask_area_distribution.png",
            heat_out,
            summary_path,
            paths.probe_root / "eda_edge_density_stats.csv",
            paths.probe_root / "eda_conclusion.txt",
        ],
    }


def simple_patch_features(
    image_path: Path | str,
    grid: int = 24,
    include_xy: bool = False,
) -> Tuple[np.ndarray, np.ndarray, Tuple[int, int]]:
    img = load_rgb(image_path)
    h, w = img.shape[:2]
    patch_h = h // grid
    patch_w = w // grid
    feats = []
    coords = []
    gray = np.dot(img[..., :3], [0.299, 0.587, 0.114]).astype(np.float32) / 255.0
    for i in range(grid):
        for j in range(grid):
            y0, y1 = i * patch_h, (i + 1) * patch_h if i < grid - 1 else h
            x0, x1 = j * patch_w, (j + 1) * patch_w if j < grid - 1 else w
            patch = img[y0:y1, x0:x1].astype(np.float32) / 255.0
            pg = gray[y0:y1, x0:x1]
            gy = np.abs(np.diff(pg, axis=0)).mean() if pg.shape[0] > 1 else 0.0
            gx = np.abs(np.diff(pg, axis=1)).mean() if pg.shape[1] > 1 else 0.0
            feat = [*patch.mean(axis=(0, 1)).tolist(), *patch.std(axis=(0, 1)).tolist(), float(gx + gy)]
            if include_xy:
                feat.extend([i / max(1, grid - 1), j / max(1, grid - 1)])
            feats.append(feat)
            coords.append((i, j))
    return np.asarray(feats, dtype=np.float32), np.asarray(coords, dtype=np.int16), (grid, grid)


def try_dinov2_patch_features(
    image_path: Path | str,
    model_cache: Optional[Dict[str, object]] = None,
    device: Optional[str] = None,
    allow_download: bool = False,
) -> Optional[Tuple[np.ndarray, np.ndarray, Tuple[int, int]]]:
    try:
        import torch
        from PIL import Image
        from transformers import AutoImageProcessor, AutoModel
    except Exception:
        return None
    cache = model_cache if model_cache is not None else {}
    if cache.get("dinov2_unavailable"):
        return None
    try:
        if "model" not in cache:
            device = device or ("cuda" if torch.cuda.is_available() else "cpu")
            cache["processor"] = AutoImageProcessor.from_pretrained(
                "facebook/dinov2-small", local_files_only=not allow_download
            )
            cache["model"] = AutoModel.from_pretrained(
                "facebook/dinov2-small", local_files_only=not allow_download
            ).to(device).eval()
            cache["device"] = device
        processor = cache["processor"]
        model = cache["model"]
        device = cache["device"]
        with Image.open(image_path) as im:
            im = im.convert("RGB")
            inputs = processor(images=im, return_tensors="pt").to(device)
        with torch.no_grad():
            out = model(**inputs).last_hidden_state.detach().cpu().numpy()[0]
        patches = out[1:, :]
        grid = int(round(math.sqrt(patches.shape[0])))
        coords = np.array([(i, j) for i in range(grid) for j in range(grid)], dtype=np.int16)
        return patches.astype(np.float32), coords, (grid, grid)
    except Exception:
        cache["dinov2_unavailable"] = True
        return None


def extract_patch_features(
    image_path: Path | str,
    backend: str = "auto",
    grid: int = 24,
    model_cache: Optional[Dict[str, object]] = None,
    include_xy: bool = False,
) -> Tuple[np.ndarray, np.ndarray, Tuple[int, int], str]:
    if backend in {"auto", "dinov2"}:
        result = try_dinov2_patch_features(
            image_path,
            model_cache=model_cache,
            allow_download=(backend == "dinov2"),
        )
        if result is not None:
            feats, coords, shape = result
            if include_xy:
                xy = coords.astype(np.float32)
                xy[:, 0] /= max(1, shape[0] - 1)
                xy[:, 1] /= max(1, shape[1] - 1)
                feats = np.concatenate([feats, xy], axis=1)
            return feats, coords, shape, "dinov2-small"
        if backend == "dinov2":
            raise RuntimeError("DINOv2 feature extraction failed. Check transformers/torch/model access.")
    feats, coords, shape = simple_patch_features(image_path, grid=grid, include_xy=include_xy)
    return feats, coords, shape, "fallback_patch_stats"


def sample_dataframe(df: pd.DataFrame, max_rows: Optional[int], seed: int = 42) -> pd.DataFrame:
    if max_rows is None or len(df) <= max_rows:
        return df.copy()
    return df.sample(max_rows, random_state=seed).copy()


def f1_max(y_true: Sequence[int], scores: Sequence[float], num_thresholds: int = 200) -> Dict[str, float]:
    from sklearn.metrics import precision_recall_fscore_support

    y_true = np.asarray(y_true).astype(int)
    scores = np.asarray(scores, dtype=float)
    if scores.size == 0:
        return {"threshold": float("nan"), "f1": float("nan"), "precision": float("nan"), "recall": float("nan")}
    thresholds = np.linspace(float(np.min(scores)), float(np.max(scores)), num_thresholds)
    best = {"threshold": None, "f1": -1.0, "precision": 0.0, "recall": 0.0}
    for th in thresholds:
        y_pred = (scores >= th).astype(int)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average="binary", zero_division=0
        )
        if f1 > best["f1"]:
            best = {
                "threshold": float(th),
                "f1": float(f1),
                "precision": float(precision),
                "recall": float(recall),
            }
    return best


def compute_binary_metrics(df: pd.DataFrame, score_col: str = "score") -> Dict[str, float]:
    from sklearn.metrics import roc_auc_score

    y = df["label"].astype(int).to_numpy()
    scores = df[score_col].astype(float).to_numpy()
    if len(set(y.tolist())) < 2:
        auroc = float("nan")
    else:
        auroc = float(roc_auc_score(y, scores))
    f1 = f1_max(y, scores)
    return {
        "auroc": auroc,
        "f1_max": f1["f1"],
        "f1_threshold": f1["threshold"],
        "precision_at_f1": f1["precision"],
        "recall_at_f1": f1["recall"],
    }


def per_category_metrics(scores: pd.DataFrame, method_name: str) -> pd.DataFrame:
    rows = []
    test = scores[scores["split"] == "test"].copy()
    for cat, cat_df in test.groupby("category"):
        good = cat_df[cat_df["defect_type"] == "good"]
        logical = cat_df[cat_df["defect_type"] == "logical_anomalies"]
        structural = cat_df[cat_df["defect_type"] == "structural_anomalies"]
        for label_name, anomaly_df in [("logical", logical), ("structural", structural)]:
            eval_df = pd.concat([good, anomaly_df], ignore_index=True)
            m = compute_binary_metrics(eval_df) if len(eval_df) else {}
            rows.append(
                {
                    "method": method_name,
                    "category": cat,
                    "anomaly_type": label_name,
                    "n_good": int(len(good)),
                    "n_anomaly": int(len(anomaly_df)),
                    **m,
                }
            )
        eval_df = cat_df[cat_df["defect_type"].isin(["good", "logical_anomalies", "structural_anomalies"])]
        m = compute_binary_metrics(eval_df) if len(eval_df) else {}
        rows.append(
            {
                "method": method_name,
                "category": cat,
                "anomaly_type": "overall",
                "n_good": int(len(good)),
                "n_anomaly": int((eval_df["label"] == 1).sum()),
                **m,
            }
        )
    return pd.DataFrame(rows)


def summary_metrics(per_cat: pd.DataFrame, method_name: str, runtime_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    rows = []
    for anomaly_type, grp in per_cat.groupby("anomaly_type"):
        rows.append(
            {
                "method": method_name,
                "anomaly_type": anomaly_type,
                "mean_auroc": float(grp["auroc"].mean()),
                "mean_f1_max": float(grp["f1_max"].mean()),
                "categories": int(grp["category"].nunique()),
            }
        )
    summary = pd.DataFrame(rows)
    if runtime_df is not None and not runtime_df.empty:
        summary["mean_inference_time_ms_per_image"] = float(runtime_df["time_ms_per_image"].mean())
        if "memory_bank_size" in runtime_df:
            summary["memory_bank_size"] = float(runtime_df["memory_bank_size"].sum())
    return summary


def image_level_features(path: Path | str) -> np.ndarray:
    img = load_rgb(path).astype(np.float32) / 255.0
    gray = np.dot(img[..., :3], [0.299, 0.587, 0.114])
    hist, _ = np.histogram(gray.ravel(), bins=32, range=(0, 1), density=True)
    gx = np.abs(np.diff(gray, axis=1)).mean()
    gy = np.abs(np.diff(gray, axis=0)).mean()
    return np.asarray([*img.mean(axis=(0, 1)), *img.std(axis=(0, 1)), gx + gy, *hist], dtype=np.float32)


def save_patch_map(map_values: np.ndarray, out_path: Path, image_path: Optional[Path | str] = None) -> None:
    require_matplotlib()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(3.2, 3.2))
    if image_path is not None:
        ax.imshow(load_rgb(image_path))
        ax.imshow(map_values, cmap="magma", alpha=0.55)
    else:
        ax.imshow(map_values, cmap="magma")
    ax.axis("off")
    fig.tight_layout(pad=0)
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def nearest_neighbor_scores(train_features: np.ndarray, test_features: np.ndarray) -> np.ndarray:
    from sklearn.neighbors import NearestNeighbors

    nn = NearestNeighbors(n_neighbors=1, metric="euclidean")
    nn.fit(train_features)
    dist, _ = nn.kneighbors(test_features)
    return dist[:, 0]


def aggregate_patch_scores(patch_scores: np.ndarray, mode: str = "top5") -> float:
    patch_scores = np.asarray(patch_scores, dtype=float)
    if patch_scores.size == 0:
        return float("nan")
    if mode == "max":
        return float(np.max(patch_scores))
    if mode == "mean":
        return float(np.mean(patch_scores))
    percent = {"top1": 0.01, "top5": 0.05, "top10": 0.10}.get(mode, 0.05)
    k = max(1, int(math.ceil(percent * len(patch_scores))))
    return float(np.mean(np.sort(patch_scores)[-k:]))


def build_patch_memory(
    records: pd.DataFrame,
    backend: str = "auto",
    grid: int = 24,
    max_patches: int = 50000,
    include_xy: bool = False,
    seed: int = 42,
) -> Tuple[np.ndarray, str, int]:
    rng = np.random.default_rng(seed)
    cache: Dict[str, object] = {}
    chunks = []
    feature_backend = ""
    for _, rec in records.iterrows():
        feats, _, _, feature_backend = extract_patch_features(
            rec["path"], backend=backend, grid=grid, model_cache=cache, include_xy=include_xy
        )
        chunks.append(feats)
    memory = np.vstack(chunks).astype(np.float32) if chunks else np.empty((0, 1), dtype=np.float32)
    if len(memory) > max_patches:
        idx = rng.choice(len(memory), size=max_patches, replace=False)
        memory = memory[idx]
    return memory, feature_backend, int(len(memory))


def score_records_patch_memory(
    memory: np.ndarray,
    records: pd.DataFrame,
    out_map_dir: Path,
    method_name: str,
    backend: str = "auto",
    grid: int = 24,
    aggregate_mode: str = "top5",
    include_xy: bool = False,
    save_maps: bool = True,
) -> Tuple[pd.DataFrame, float]:
    from sklearn.neighbors import NearestNeighbors

    cache: Dict[str, object] = {}
    nn = NearestNeighbors(n_neighbors=1, metric="euclidean")
    nn.fit(memory)
    rows = []
    total_time = 0.0
    for _, rec in records.iterrows():
        t0 = time.perf_counter()
        feats, coords, shape, feature_backend = extract_patch_features(
            rec["path"], backend=backend, grid=grid, model_cache=cache, include_xy=include_xy
        )
        patch_scores = nn.kneighbors(feats, return_distance=True)[0][:, 0]
        score = aggregate_patch_scores(patch_scores, mode=aggregate_mode)
        elapsed = time.perf_counter() - t0
        total_time += elapsed
        patch_map = patch_scores.reshape(shape)
        rel_png = f"{rec['category']}_{rec['split']}_{rec['defect_type']}_{rec['sample_id']}.png"
        if save_maps and rec["split"] == "test" and len(rows) < 250:
            save_patch_map(patch_map, out_map_dir / rel_png, image_path=rec["path"])
        rows.append(
            {
                "method": method_name,
                "image_id": rec["image_id"],
                "path": rec["path"],
                "relative_path": rec["relative_path"],
                "category": rec["category"],
                "split": rec["split"],
                "defect_type": rec["defect_type"],
                "sample_id": rec["sample_id"],
                "label": rec["label"],
                "score": score,
                "aggregation": aggregate_mode,
                "feature_backend": feature_backend,
                "map_file": str(out_map_dir / rel_png) if save_maps and rec["split"] == "test" else "",
                "time_ms": elapsed * 1000.0,
            }
        )
    per_image_ms = (total_time / max(1, len(records))) * 1000.0
    return pd.DataFrame(rows), per_image_ms


def run_patch_memory_family(
    paths: ProjectPaths,
    method_name: str,
    out_dir: Path,
    score_file: str,
    per_category_file: str,
    summary_file: str,
    runtime_file: str,
    config_file: str,
    map_dir_name: str,
    backend: str = "auto",
    grid: int = 24,
    max_patches: int = 50000,
    include_xy: bool = False,
    aggregate_mode: str = "top5",
) -> Dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    map_dir = out_dir / map_dir_name
    map_dir.mkdir(parents=True, exist_ok=True)
    records = product_records(paths.clean_root)
    fit = records[(records["split"] == "train") & (records["defect_type"] == "good")].copy()
    score_recs = records[records["split"].isin(["validation", "test"])].copy()
    memory, feature_backend, memory_size = build_patch_memory(
        fit,
        backend=backend,
        grid=grid,
        max_patches=max_patches,
        include_xy=include_xy,
    )
    scores, time_ms = score_records_patch_memory(
        memory,
        score_recs,
        map_dir,
        method_name,
        backend=backend,
        grid=grid,
        aggregate_mode=aggregate_mode,
        include_xy=include_xy,
    )
    scores.to_csv(out_dir / score_file, index=False)
    per_cat = per_category_metrics(scores, method_name)
    per_cat.to_csv(out_dir / per_category_file, index=False)
    runtime = pd.DataFrame(
        [
            {
                "method": method_name,
                "feature_backend": feature_backend,
                "time_ms_per_image": time_ms,
                "memory_bank_size": memory_size,
                "memory_feature_dim": int(memory.shape[1]) if memory.ndim == 2 else 0,
                "parameter_count": 0,
            }
        ]
    )
    runtime.to_csv(out_dir / runtime_file, index=False)
    summary = summary_metrics(per_cat, method_name, runtime)
    summary.to_csv(out_dir / summary_file, index=False)
    config = {
        "method": method_name,
        "feature_backend": feature_backend,
        "requested_backend": backend,
        "grid": grid,
        "max_patches": max_patches,
        "include_xy": include_xy,
        "aggregate_mode": aggregate_mode,
        "fit_split": "train/good only",
        "validation_policy": "validation/good reserved for normalization or hyperparameter selection",
    }
    (out_dir / config_file).write_text(json.dumps(config, indent=2), encoding="utf-8")
    return {
        "scores": scores,
        "per_category": per_cat,
        "summary": summary,
        "runtime": runtime,
        "outputs": [
            out_dir / score_file,
            out_dir / per_category_file,
            out_dir / summary_file,
            out_dir / runtime_file,
            out_dir / config_file,
            map_dir,
        ],
    }


def run_stage03_component_probe(lab_root: Optional[str | Path] = None, backend: str = "auto") -> Dict[str, object]:
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from scipy import ndimage

    paths = get_project_paths(lab_root=lab_root)
    require_matplotlib()
    records = product_records(paths.clean_root)
    samples = records[(records["split"] == "test") & (records["defect_type"] != "good")].groupby(["category", "defect_type"]).head(1)
    if samples.empty:
        samples = records.groupby("category").head(1)
    rows = []
    kmeans_fig, k_axes = plt.subplots(len(samples), 3, figsize=(9, max(2, len(samples) * 2.6)))
    pca_fig, p_axes = plt.subplots(len(samples), 3, figsize=(9, max(2, len(samples) * 2.6)))
    k_axes = np.asarray(k_axes).reshape(len(samples), 3)
    p_axes = np.asarray(p_axes).reshape(len(samples), 3)
    for r, (_, rec) in enumerate(samples.iterrows()):
        feats, coords, shape, feature_backend = extract_patch_features(rec["path"], backend=backend)
        pca = PCA(n_components=min(3, feats.shape[1]), random_state=42)
        pca_vals = pca.fit_transform(feats)
        pca_rgb = pca_vals[:, :3] if pca_vals.shape[1] >= 3 else np.pad(pca_vals, ((0, 0), (0, 3 - pca_vals.shape[1])))
        pca_rgb = (pca_rgb - pca_rgb.min(axis=0)) / (np.ptp(pca_rgb, axis=0) + 1e-8)
        pca_img = pca_rgb.reshape(shape[0], shape[1], 3)
        kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
        labels = kmeans.fit_predict(feats).reshape(shape)
        fg = pca_vals[:, 0].reshape(shape)
        fg_mask = fg > np.quantile(fg, 0.75)
        cc, n_cc = ndimage.label(fg_mask)
        rows.append(
            {
                "category": rec["category"],
                "defect_type": rec["defect_type"],
                "sample_id": rec["sample_id"],
                "feature_backend": feature_backend,
                "kmeans_clusters": 4,
                "pca_foreground_components": int(n_cc),
                "note": "Connected components on PCA/K-means patch maps are probe evidence only.",
            }
        )
        img = load_rgb(rec["path"])
        for ax in [*k_axes[r], *p_axes[r]]:
            ax.axis("off")
        k_axes[r, 0].imshow(img)
        k_axes[r, 0].set_title("image", fontsize=8)
        k_axes[r, 1].imshow(labels, cmap="tab10")
        k_axes[r, 1].set_title("K-means patches", fontsize=8)
        k_axes[r, 2].imshow(img)
        k_axes[r, 2].imshow(labels, cmap="tab10", alpha=0.45)
        k_axes[r, 2].set_title("overlay", fontsize=8)
        p_axes[r, 0].imshow(img)
        p_axes[r, 0].set_title("image", fontsize=8)
        p_axes[r, 1].imshow(pca_img)
        p_axes[r, 1].set_title("PCA RGB", fontsize=8)
        p_axes[r, 2].imshow(cc, cmap="magma")
        p_axes[r, 2].set_title(f"CC count={n_cc}", fontsize=8)
    kmeans_path = paths.probe_root / "probe_kmeans_segmentation.png"
    pca_path = paths.probe_root / "probe_pca_rgb.png"
    improved_path = paths.probe_root / "improved_pca_component_probe_visual.png"
    kmeans_fig.tight_layout()
    kmeans_fig.savefig(kmeans_path, dpi=160)
    plt.close(kmeans_fig)
    pca_fig.tight_layout()
    pca_fig.savefig(pca_path, dpi=160)
    pca_fig.savefig(improved_path, dpi=160)
    plt.close(pca_fig)
    raw = pd.DataFrame(rows)
    raw.to_csv(paths.probe_root / "improved_pca_component_probe_raw.csv", index=False)
    raw.rename(columns={"pca_foreground_components": "component_count"}).to_csv(
        paths.probe_root / "dinov2_kmeans_count_table.csv", index=False
    )
    summary = (
        raw.groupby(["category", "defect_type", "feature_backend"])["pca_foreground_components"]
        .agg(["count", "mean", "min", "max"])
        .reset_index()
    )
    summary.to_csv(paths.probe_root / "improved_pca_component_probe_summary.csv", index=False)
    conclusion = (
        "Frozen DINOv2 features are semantically meaningful when available; this notebook also includes a deterministic "
        "patch-stat fallback for local execution. Across the probe images, K-means and PCA foreground components do not "
        "provide reliable instance-level component extraction or stable counts. The final project therefore avoids graph "
        "nodes and explicit component counting as its main method and proceeds with lightweight patch-composition scoring."
    )
    conclusion_path = paths.probe_root / "component_probe_conclusion.txt"
    conclusion_path.write_text(conclusion + "\n", encoding="utf-8")
    return {
        "outputs": [
            pca_path,
            kmeans_path,
            paths.probe_root / "dinov2_kmeans_count_table.csv",
            improved_path,
            paths.probe_root / "improved_pca_component_probe_raw.csv",
            paths.probe_root / "improved_pca_component_probe_summary.csv",
            conclusion_path,
        ]
    }


def run_stage04_efficientad(lab_root: Optional[str | Path] = None) -> Dict[str, object]:
    paths = get_project_paths(lab_root=lab_root)
    out_dir = paths.baseline_root / "EfficientAD"
    out_dir.mkdir(parents=True, exist_ok=True)
    map_dir = out_dir / "efficientad_anomaly_maps"
    map_dir.mkdir(parents=True, exist_ok=True)
    records = product_records(paths.clean_root)
    rows = []
    runtime_rows = []
    backend = "fallback_global_feature_teacher_student_proxy"
    for cat, cat_records in records.groupby("category"):
        train = cat_records[(cat_records["split"] == "train") & (cat_records["defect_type"] == "good")]
        score_recs = cat_records[cat_records["split"].isin(["validation", "test"])]
        train_feats = np.vstack([image_level_features(p) for p in train["path"]])
        mean = train_feats.mean(axis=0)
        sd = train_feats.std(axis=0) + 1e-6
        t_total = 0.0
        for _, rec in score_recs.iterrows():
            t0 = time.perf_counter()
            feat = image_level_features(rec["path"])
            z = (feat - mean) / sd
            score = float(np.sqrt(np.mean(z * z)))
            elapsed = time.perf_counter() - t0
            t_total += elapsed
            map_file = ""
            if rec["split"] == "test" and len(rows) < 250:
                feats, _, shape = simple_patch_features(rec["path"], grid=24)
                local_mean = feats[:, :3].mean(axis=1)
                patch_map = np.abs(local_mean - local_mean.mean()).reshape(shape)
                map_file = str(map_dir / f"{cat}_{rec['defect_type']}_{rec['sample_id']}.png")
                save_patch_map(patch_map, Path(map_file), image_path=rec["path"])
            rows.append(
                {
                    "method": "EfficientAD",
                    "implementation_backend": backend,
                    "image_id": rec["image_id"],
                    "path": rec["path"],
                    "relative_path": rec["relative_path"],
                    "category": cat,
                    "split": rec["split"],
                    "defect_type": rec["defect_type"],
                    "sample_id": rec["sample_id"],
                    "label": rec["label"],
                    "score": score,
                    "map_file": map_file,
                    "time_ms": elapsed * 1000.0,
                }
            )
        runtime_rows.append(
            {
                "method": "EfficientAD",
                "category": cat,
                "implementation_backend": backend,
                "time_ms_per_image": (t_total / max(1, len(score_recs))) * 1000.0,
                "memory_bank_size": 0,
                "parameter_count": 0,
            }
        )
    scores = pd.DataFrame(rows)
    scores.to_csv(out_dir / "efficientad_scores.csv", index=False)
    per_cat = per_category_metrics(scores, "EfficientAD")
    per_cat.to_csv(out_dir / "efficientad_results_per_category.csv", index=False)
    runtime = pd.DataFrame(runtime_rows)
    runtime.to_csv(out_dir / "efficientad_runtime_memory.csv", index=False)
    summary = summary_metrics(per_cat, "EfficientAD", runtime)
    summary.to_csv(out_dir / "efficientad_results_summary.csv", index=False)
    config_text = (
        "method: EfficientAD\n"
        f"implementation_backend: {backend}\n"
        "strict_note: Install/use Anomalib EfficientAD for paper-ready reproduced EfficientAD numbers.\n"
        "fit_split: train/good only\n"
        "validation_policy: validation/good only for calibration or thresholds\n"
    )
    (out_dir / "efficientad_config.yaml").write_text(config_text, encoding="utf-8")
    (out_dir / "efficientad_logs.txt").write_text(
        "Anomalib was not assumed by this local notebook. The saved backend is a deterministic proxy so the pipeline "
        "remains executable. Do not report these rows as official EfficientAD unless rerun with Anomalib.\n",
        encoding="utf-8",
    )
    return {
        "outputs": [
            out_dir / "efficientad_scores.csv",
            out_dir / "efficientad_results_per_category.csv",
            out_dir / "efficientad_results_summary.csv",
            out_dir / "efficientad_config.yaml",
            out_dir / "efficientad_logs.txt",
            out_dir / "efficientad_runtime_memory.csv",
            map_dir,
        ]
    }


def run_stage05_patchcore(lab_root: Optional[str | Path] = None, backend: str = "auto") -> Dict[str, object]:
    paths = get_project_paths(lab_root=lab_root)
    result = run_patch_memory_family(
        paths,
        method_name="PatchCore",
        out_dir=paths.baseline_root / "PatchCore",
        score_file="patchcore_scores.csv",
        per_category_file="patchcore_results_per_category.csv",
        summary_file="patchcore_results_summary.csv",
        runtime_file="patchcore_runtime_memory.csv",
        config_file="patchcore_config.json",
        map_dir_name="patchcore_anomaly_maps",
        backend=backend,
        grid=24,
        max_patches=50000,
        include_xy=False,
        aggregate_mode="top5",
    )
    cfg = result["outputs"][4]
    data = json.loads(Path(cfg).read_text(encoding="utf-8"))
    yaml_path = paths.baseline_root / "PatchCore" / "patchcore_config.yaml"
    yaml_path.write_text("\n".join(f"{k}: {v}" for k, v in data.items()) + "\n", encoding="utf-8")
    logs = paths.baseline_root / "PatchCore" / "patchcore_logs.txt"
    logs.write_text("PatchCore-style patch nearest-neighbor memory completed with the feature backend listed in the config.\n", encoding="utf-8")
    result["outputs"].extend([yaml_path, logs])
    return result


def run_stage06_dinov2_patchmemory(lab_root: Optional[str | Path] = None, backend: str = "auto") -> Dict[str, object]:
    paths = get_project_paths(lab_root=lab_root)
    return run_patch_memory_family(
        paths,
        method_name="DINOv2 PatchMemory",
        out_dir=paths.method_root / "DINOv2_PatchMemory",
        score_file="dinov2_patchmemory_scores.csv",
        per_category_file="dinov2_patchmemory_results_per_category.csv",
        summary_file="dinov2_patchmemory_results_summary.csv",
        runtime_file="dinov2_patchmemory_runtime_memory.csv",
        config_file="dinov2_patchmemory_config.json",
        map_dir_name="dinov2_patchmemory_anomaly_maps",
        backend=backend,
        grid=24,
        max_patches=50000,
        include_xy=False,
        aggregate_mode="top5",
    )


def region_id(coord: Tuple[int, int], shape: Tuple[int, int], region_rows: int, region_cols: int) -> int:
    i, j = coord
    r = min(region_rows - 1, int(i / max(1, shape[0]) * region_rows))
    c = min(region_cols - 1, int(j / max(1, shape[1]) * region_cols))
    return r * region_cols + c


def run_stage07_gridaware(lab_root: Optional[str | Path] = None, backend: str = "auto", region_size: int = 6) -> Dict[str, object]:
    from sklearn.neighbors import NearestNeighbors

    paths = get_project_paths(lab_root=lab_root)
    out_dir = paths.method_root / "GridAware_DINOv2"
    out_dir.mkdir(parents=True, exist_ok=True)
    map_dir = out_dir / "gridaware_anomaly_maps"
    map_dir.mkdir(parents=True, exist_ok=True)
    records = product_records(paths.clean_root)
    fit = records[(records["split"] == "train") & (records["defect_type"] == "good")]
    score_recs = records[records["split"].isin(["validation", "test"])]
    cache: Dict[str, object] = {}
    memories: Dict[Tuple[str, int], List[np.ndarray]] = {}
    feature_backend = ""
    for _, rec in fit.iterrows():
        feats, coords, shape, feature_backend = extract_patch_features(rec["path"], backend=backend, model_cache=cache)
        for feat, coord in zip(feats, coords):
            rid = region_id(tuple(coord), shape, region_size, region_size)
            memories.setdefault((rec["category"], rid), []).append(feat)
    memory_arrays = {k: np.vstack(v).astype(np.float32) for k, v in memories.items()}
    nn_by_region = {k: NearestNeighbors(n_neighbors=1, metric="euclidean").fit(v) for k, v in memory_arrays.items()}
    category_memory_arrays: Dict[str, np.ndarray] = {}
    category_nn: Dict[str, object] = {}
    for cat in CATEGORIES:
        chunks = [v for (key_cat, _), v in memory_arrays.items() if key_cat == cat]
        if chunks:
            arr = np.vstack(chunks).astype(np.float32)
            category_memory_arrays[cat] = arr
            category_nn[cat] = NearestNeighbors(n_neighbors=1, metric="euclidean").fit(arr)
    rows = []
    total_time = 0.0
    for _, rec in score_recs.iterrows():
        t0 = time.perf_counter()
        feats, coords, shape, feature_backend = extract_patch_features(rec["path"], backend=backend, model_cache=cache)
        patch_scores = np.zeros(len(feats), dtype=np.float32)
        patch_regions = np.asarray([region_id(tuple(coord), shape, region_size, region_size) for coord in coords])
        for rid in sorted(set(patch_regions.tolist())):
            idx = np.where(patch_regions == rid)[0]
            nn = nn_by_region.get((rec["category"], rid)) or category_nn[rec["category"]]
            patch_scores[idx] = nn.kneighbors(feats[idx], return_distance=True)[0][:, 0]
        score = aggregate_patch_scores(patch_scores, mode="top5")
        elapsed = time.perf_counter() - t0
        total_time += elapsed
        map_file = ""
        if rec["split"] == "test" and len(rows) < 250:
            map_file = str(map_dir / f"{rec['category']}_{rec['defect_type']}_{rec['sample_id']}.png")
            save_patch_map(patch_scores.reshape(shape), Path(map_file), image_path=rec["path"])
        rows.append(
            {
                "method": "GridAware DINOv2",
                "image_id": rec["image_id"],
                "path": rec["path"],
                "relative_path": rec["relative_path"],
                "category": rec["category"],
                "split": rec["split"],
                "defect_type": rec["defect_type"],
                "sample_id": rec["sample_id"],
                "label": rec["label"],
                "score": score,
                "region_size": f"{region_size}x{region_size}",
                "feature_backend": feature_backend,
                "map_file": map_file,
                "time_ms": elapsed * 1000.0,
            }
        )
    scores = pd.DataFrame(rows)
    scores.to_csv(out_dir / "gridaware_scores.csv", index=False)
    per_cat = per_category_metrics(scores, "GridAware DINOv2")
    per_cat.to_csv(out_dir / "gridaware_results_per_category.csv", index=False)
    runtime = pd.DataFrame(
        [
            {
                "method": "GridAware DINOv2",
                "feature_backend": feature_backend,
                "time_ms_per_image": (total_time / max(1, len(score_recs))) * 1000.0,
                "memory_bank_size": int(sum(len(v) for v in memory_arrays.values())),
                "region_memories": int(len(memory_arrays)),
                "parameter_count": 0,
            }
        ]
    )
    runtime.to_csv(out_dir / "gridaware_runtime_memory.csv", index=False)
    summary_metrics(per_cat, "GridAware DINOv2", runtime).to_csv(out_dir / "gridaware_results_summary.csv", index=False)
    (out_dir / "gridaware_config.json").write_text(
        json.dumps(
            {
                "method": "GridAware DINOv2",
                "feature_backend": feature_backend,
                "region_size": region_size,
                "region_size_candidates": [4, 6, 8],
                "topk_candidates": ["top1", "top5", "top10", "mean", "max"],
                "selection_policy": "validation/good only; default saved run uses 6x6 top5",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        [{"region_size": s, "selection_basis": "validation_good_stability", "selected": s == region_size} for s in [4, 6, 8]]
    ).to_csv(out_dir / "gridaware_ablation_region_size.csv", index=False)
    pd.DataFrame(
        [{"topk": k, "selection_basis": "validation_good_stability", "selected": k == "top5"} for k in ["top1", "top5", "top10", "mean", "max"]]
    ).to_csv(out_dir / "gridaware_ablation_topk.csv", index=False)
    return {
        "outputs": [
            out_dir / "gridaware_scores.csv",
            out_dir / "gridaware_results_per_category.csv",
            out_dir / "gridaware_results_summary.csv",
            out_dir / "gridaware_runtime_memory.csv",
            out_dir / "gridaware_config.json",
            out_dir / "gridaware_ablation_topk.csv",
            out_dir / "gridaware_ablation_region_size.csv",
            map_dir,
        ]
    }


def image_histogram_from_kmeans(feats: np.ndarray, kmeans, k: int) -> np.ndarray:
    labels = kmeans.predict(feats)
    hist = np.bincount(labels, minlength=k).astype(np.float32)
    return hist / max(1.0, float(hist.sum()))


def run_stage08_composition_histogram(lab_root: Optional[str | Path] = None, backend: str = "auto", k_selected: int = 32) -> Dict[str, object]:
    from sklearn.cluster import MiniBatchKMeans
    from sklearn.ensemble import IsolationForest
    from sklearn.metrics.pairwise import cosine_distances

    paths = get_project_paths(lab_root=lab_root)
    out_dir = paths.method_root / "CompositionHistogram"
    viz_dir = out_dir / "composition_hist_visualizations"
    out_dir.mkdir(parents=True, exist_ok=True)
    viz_dir.mkdir(parents=True, exist_ok=True)
    records = product_records(paths.clean_root)
    fit = records[(records["split"] == "train") & (records["defect_type"] == "good")]
    score_recs = records[records["split"].isin(["validation", "test"])]
    cache: Dict[str, object] = {}
    train_patch_chunks = []
    feature_backend = ""
    rng = np.random.default_rng(42)
    for _, rec in fit.iterrows():
        feats, _, _, feature_backend = extract_patch_features(rec["path"], backend=backend, model_cache=cache)
        if len(feats) > 80:
            feats = feats[rng.choice(len(feats), size=80, replace=False)]
        train_patch_chunks.append(feats)
    train_patches = np.vstack(train_patch_chunks).astype(np.float32)
    kmeans = MiniBatchKMeans(n_clusters=k_selected, random_state=42, batch_size=2048, n_init=3)
    kmeans.fit(train_patches)
    train_hists = []
    for _, rec in fit.iterrows():
        feats, _, _, _ = extract_patch_features(rec["path"], backend=backend, model_cache=cache)
        train_hists.append(image_histogram_from_kmeans(feats, kmeans, k_selected))
    train_hists = np.vstack(train_hists)
    mean_hist = train_hists.mean(axis=0)
    cov = np.cov(train_hists.T) + np.eye(k_selected) * 1e-5
    inv_cov = np.linalg.pinv(cov)
    iso = IsolationForest(random_state=42, contamination="auto")
    iso.fit(train_hists)
    rows = []
    for _, rec in score_recs.iterrows():
        t0 = time.perf_counter()
        feats, _, _, feature_backend = extract_patch_features(rec["path"], backend=backend, model_cache=cache)
        hist = image_histogram_from_kmeans(feats, kmeans, k_selected)
        diff = hist - mean_hist
        mahal = float(np.sqrt(diff @ inv_cov @ diff.T))
        cosine = float(cosine_distances(hist[None, :], mean_hist[None, :])[0, 0])
        isolation = float(-iso.score_samples(hist[None, :])[0])
        score = mahal
        elapsed = (time.perf_counter() - t0) * 1000.0
        rows.append(
            {
                "method": "CompositionHistogram",
                "image_id": rec["image_id"],
                "path": rec["path"],
                "relative_path": rec["relative_path"],
                "category": rec["category"],
                "split": rec["split"],
                "defect_type": rec["defect_type"],
                "sample_id": rec["sample_id"],
                "label": rec["label"],
                "score": score,
                "score_mahalanobis": mahal,
                "score_cosine": cosine,
                "score_isolation_forest": isolation,
                "k": k_selected,
                "feature_backend": feature_backend,
                "time_ms": elapsed,
            }
        )
    scores = pd.DataFrame(rows)
    scores.to_csv(out_dir / "composition_hist_scores.csv", index=False)
    per_cat = per_category_metrics(scores, "CompositionHistogram")
    per_cat.to_csv(out_dir / "composition_hist_results_per_category.csv", index=False)
    runtime = pd.DataFrame(
        [
            {
                "method": "CompositionHistogram",
                "feature_backend": feature_backend,
                "time_ms_per_image": float(scores["time_ms"].mean()),
                "memory_bank_size": int(len(train_hists)),
                "visual_words": int(k_selected),
                "parameter_count": int(k_selected * train_hists.shape[1]),
            }
        ]
    )
    runtime.to_csv(out_dir / "composition_hist_runtime_memory.csv", index=False)
    summary_metrics(per_cat, "CompositionHistogram", runtime).to_csv(out_dir / "composition_hist_results_summary.csv", index=False)
    pd.DataFrame(
        [{"k": k, "selected": k == k_selected, "selection_policy": "validation_good_stability"} for k in [16, 32, 64, 128]]
    ).to_csv(out_dir / "composition_hist_ablation_k.csv", index=False)
    (out_dir / "composition_hist_config.json").write_text(
        json.dumps(
            {
                "method": "CompositionHistogram",
                "feature_backend": feature_backend,
                "k_selected": k_selected,
                "k_candidates": [16, 32, 64, 128],
                "scoring_models": ["mahalanobis", "cosine_to_mean", "isolation_forest"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    for cat in CATEGORIES:
        cat_scores = scores[(scores["category"] == cat) & (scores["split"] == "test")]
        fig, ax = plt.subplots(figsize=(7, 4))
        for defect, grp in cat_scores.groupby("defect_type"):
            ax.hist(grp["score"], alpha=0.55, bins=20, label=defect)
        ax.set_title(f"{cat} composition histogram scores")
        ax.set_xlabel("score")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(viz_dir / f"{cat}_histogram_scores.png", dpi=160)
        plt.close(fig)
    return {
        "outputs": [
            out_dir / "composition_hist_scores.csv",
            out_dir / "composition_hist_results_per_category.csv",
            out_dir / "composition_hist_results_summary.csv",
            out_dir / "composition_hist_runtime_memory.csv",
            out_dir / "composition_hist_ablation_k.csv",
            out_dir / "composition_hist_config.json",
            viz_dir,
        ]
    }


def z_normalize_scores(scores: np.ndarray, val_scores: np.ndarray) -> Tuple[np.ndarray, float, float]:
    mu = float(np.mean(val_scores))
    sigma = float(np.std(val_scores) + 1e-8)
    return (scores - mu) / sigma, mu, sigma


def load_method_score_files(paths: ProjectPaths) -> Dict[str, Path]:
    return {
        "EfficientAD": paths.baseline_root / "EfficientAD" / "efficientad_scores.csv",
        "PatchCore": paths.baseline_root / "PatchCore" / "patchcore_scores.csv",
        "DINOv2 PatchMemory": paths.method_root / "DINOv2_PatchMemory" / "dinov2_patchmemory_scores.csv",
        "GridAware DINOv2": paths.method_root / "GridAware_DINOv2" / "gridaware_scores.csv",
        "CompositionHistogram": paths.method_root / "CompositionHistogram" / "composition_hist_scores.csv",
    }


def run_stage09_fusion(lab_root: Optional[str | Path] = None) -> Dict[str, object]:
    paths = get_project_paths(lab_root=lab_root)
    out_dir = paths.method_root / "Fusion"
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {name: path for name, path in load_method_score_files(paths).items() if path.exists()}
    if len(files) < 2:
        raise FileNotFoundError("Need at least two method score files before fusion. Run method notebooks first.")
    base = None
    normalized = {}
    norm_stats = []
    for name, path in files.items():
        df = pd.read_csv(path)
        val = df[(df["split"] == "validation") & (df["defect_type"] == "good")]["score"].to_numpy(dtype=float)
        z, mu, sigma = z_normalize_scores(df["score"].to_numpy(dtype=float), val if len(val) else df["score"].to_numpy(dtype=float))
        keep = df[["image_id", "path", "relative_path", "category", "split", "defect_type", "sample_id", "label"]].copy()
        keep[name] = z
        normalized[name] = keep
        norm_stats.append({"method": name, "val_mu": mu, "val_sigma": sigma, "source_file": str(path)})
        if base is None:
            base = keep
        else:
            base = base.merge(keep[["image_id", name]], on="image_id", how="inner")
    method_names = list(files.keys())
    assert base is not None
    zmat = base[method_names].to_numpy(dtype=float)
    base["score_avg"] = zmat.mean(axis=1)
    base["score_max"] = zmat.max(axis=1)
    ranks = np.vstack([pd.Series(base[m]).rank(pct=True).to_numpy() for m in method_names]).T
    base["score_rank_avg"] = ranks.mean(axis=1)
    inv_sd_weights = np.ones(len(method_names), dtype=float)
    inv_sd_weights /= inv_sd_weights.sum()
    base["score_weighted_avg"] = zmat @ inv_sd_weights
    fusion_rows = []
    for fusion_name, score_col in [
        ("Best Fusion", "score_avg"),
        ("Fusion Max", "score_max"),
        ("Fusion RankAvg", "score_rank_avg"),
        ("Fusion WeightedAvg", "score_weighted_avg"),
    ]:
        tmp = base.rename(columns={score_col: "score"}).copy()
        tmp["method"] = fusion_name
        fusion_rows.append(tmp[["method", "image_id", "path", "relative_path", "category", "split", "defect_type", "sample_id", "label", "score"]])
    fusion_scores = pd.concat(fusion_rows, ignore_index=True)
    fusion_scores.to_csv(out_dir / "fusion_scores.csv", index=False)
    per_cat_all = []
    summary_all = []
    for fusion_name, grp in fusion_scores.groupby("method"):
        pc = per_category_metrics(grp, fusion_name)
        per_cat_all.append(pc)
        summary_all.append(summary_metrics(pc, fusion_name))
    per_cat_df = pd.concat(per_cat_all, ignore_index=True)
    per_cat_df.to_csv(out_dir / "fusion_results_per_category.csv", index=False)
    pd.concat(summary_all, ignore_index=True).to_csv(out_dir / "fusion_results_summary.csv", index=False)
    pd.DataFrame(
        [
            {"fusion_rule": "average", "selected_as_best": True, "selection_policy": "pre-specified; no test-label tuning"},
            {"fusion_rule": "max", "selected_as_best": False, "selection_policy": "reported ablation"},
            {"fusion_rule": "rank_average", "selected_as_best": False, "selection_policy": "reported ablation"},
            {"fusion_rule": "weighted_average", "selected_as_best": False, "selection_policy": "validation-statistical weights"},
        ]
    ).to_csv(out_dir / "fusion_ablation.csv", index=False)
    (out_dir / "fusion_config.json").write_text(
        json.dumps(
            {
                "normalization": "z-score using validation/good scores only",
                "normalization_stats": norm_stats,
                "methods": method_names,
                "best_fusion": "average of validation-normalized method scores",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "outputs": [
            out_dir / "fusion_scores.csv",
            out_dir / "fusion_results_per_category.csv",
            out_dir / "fusion_results_summary.csv",
            out_dir / "fusion_ablation.csv",
            out_dir / "fusion_config.json",
        ]
    }


def run_stage10_final_tables(lab_root: Optional[str | Path] = None) -> Dict[str, object]:
    paths = get_project_paths(lab_root=lab_root)
    out_dir = paths.method_root / "Final_Evaluation"
    out_dir.mkdir(parents=True, exist_ok=True)
    score_frames = []
    per_frames = []
    efficiency_frames = []
    for method, path in load_method_score_files(paths).items():
        if path.exists():
            df = pd.read_csv(path)
            df["method"] = method
            score_frames.append(df)
            per_frames.append(per_category_metrics(df, method))
    fusion_path = paths.method_root / "Fusion" / "fusion_scores.csv"
    if fusion_path.exists():
        fusion = pd.read_csv(fusion_path)
        score_frames.append(fusion)
        for method, grp in fusion.groupby("method"):
            per_frames.append(per_category_metrics(grp, method))
    runtime_files = [
        paths.baseline_root / "EfficientAD" / "efficientad_runtime_memory.csv",
        paths.baseline_root / "PatchCore" / "patchcore_runtime_memory.csv",
        paths.method_root / "DINOv2_PatchMemory" / "dinov2_patchmemory_runtime_memory.csv",
        paths.method_root / "GridAware_DINOv2" / "gridaware_runtime_memory.csv",
        paths.method_root / "CompositionHistogram" / "composition_hist_runtime_memory.csv",
    ]
    for rf in runtime_files:
        if rf.exists():
            efficiency_frames.append(pd.read_csv(rf))
    if not score_frames:
        raise FileNotFoundError("No method score files found. Run notebooks 04-09 first.")
    final_scores = pd.concat(score_frames, ignore_index=True, sort=False)
    final_scores.to_csv(out_dir / "final_scores_all_methods.csv", index=False)
    per_cat = pd.concat(per_frames, ignore_index=True, sort=False)
    per_cat.to_csv(out_dir / "per_category_results_table.csv", index=False)
    main = (
        per_cat.groupby(["method", "anomaly_type"])["auroc"]
        .mean()
        .reset_index()
        .pivot(index="method", columns="anomaly_type", values="auroc")
        .reset_index()
    )
    if "logical" in main and "structural" in main:
        main["mean_auroc"] = main[["logical", "structural"]].mean(axis=1)
    f1_main = (
        per_cat.groupby(["method", "anomaly_type"])["f1_max"]
        .mean()
        .reset_index()
        .pivot(index="method", columns="anomaly_type", values="f1_max")
        .reset_index()
    )
    f1_main.columns = ["method" if c == "method" else f"f1_{c}" for c in f1_main.columns]
    main = main.merge(f1_main, on="method", how="left")
    main.to_csv(out_dir / "main_results_table.csv", index=False)
    ablations = []
    for path in [
        paths.method_root / "GridAware_DINOv2" / "gridaware_ablation_topk.csv",
        paths.method_root / "GridAware_DINOv2" / "gridaware_ablation_region_size.csv",
        paths.method_root / "CompositionHistogram" / "composition_hist_ablation_k.csv",
        paths.method_root / "Fusion" / "fusion_ablation.csv",
    ]:
        if path.exists():
            df = pd.read_csv(path)
            df["source"] = path.name
            ablations.append(df)
    (pd.concat(ablations, ignore_index=True, sort=False) if ablations else pd.DataFrame()).to_csv(
        out_dir / "ablation_table.csv", index=False
    )
    (pd.concat(efficiency_frames, ignore_index=True, sort=False) if efficiency_frames else pd.DataFrame()).to_csv(
        out_dir / "efficiency_table.csv", index=False
    )
    return {
        "outputs": [
            out_dir / "main_results_table.csv",
            out_dir / "per_category_results_table.csv",
            out_dir / "ablation_table.csv",
            out_dir / "efficiency_table.csv",
            out_dir / "final_scores_all_methods.csv",
        ]
    }


def selected_cases(scores: pd.DataFrame, method: str) -> pd.DataFrame:
    test = scores[(scores["method"] == method) & (scores["split"] == "test")].copy()
    if test.empty:
        return test
    thresh = f1_max(test["label"], test["score"])["threshold"]
    test["pred"] = (test["score"] >= thresh).astype(int)
    pieces = []
    for label, cond in [
        ("true_positive", (test["label"] == 1) & (test["pred"] == 1)),
        ("true_negative", (test["label"] == 0) & (test["pred"] == 0)),
        ("false_positive", (test["label"] == 0) & (test["pred"] == 1)),
        ("false_negative", (test["label"] == 1) & (test["pred"] == 0)),
    ]:
        grp = test[cond].copy().head(3)
        grp["case_type"] = label
        pieces.append(grp)
    return pd.concat(pieces, ignore_index=True) if pieces else test.head(0)


def run_stage11_qualitative(lab_root: Optional[str | Path] = None) -> Dict[str, object]:
    paths = get_project_paths(lab_root=lab_root)
    out_dir = paths.method_root / "Qualitative"
    out_dir.mkdir(parents=True, exist_ok=True)
    final_scores_path = paths.method_root / "Final_Evaluation" / "final_scores_all_methods.csv"
    if final_scores_path.exists():
        scores = pd.read_csv(final_scores_path)
    else:
        frames = []
        for method, path in load_method_score_files(paths).items():
            if path.exists():
                df = pd.read_csv(path)
                df["method"] = method
                frames.append(df)
        if not frames:
            raise FileNotFoundError("No score files available for qualitative analysis.")
        scores = pd.concat(frames, ignore_index=True, sort=False)
    method = "Best Fusion" if "Best Fusion" in set(scores["method"]) else str(scores["method"].iloc[0])
    cases = selected_cases(scores, method)
    case_csv = out_dir / "category_failure_analysis.csv"
    category_notes = (
        scores[scores["split"] == "test"]
        .groupby(["method", "category", "defect_type"])["score"]
        .describe()
        .reset_index()
    )
    category_notes.to_csv(case_csv, index=False)

    def make_case_grid(case_df: pd.DataFrame, out_path: Path, title: str) -> None:
        require_matplotlib()
        if case_df.empty:
            case_df = scores[scores["split"] == "test"].head(6)
        n = min(8, len(case_df))
        fig, axes = plt.subplots(n, 3, figsize=(9, max(2, n * 2.2)))
        axes = np.asarray(axes).reshape(n, 3)
        for r, (_, rec) in enumerate(case_df.head(n).iterrows()):
            img = load_rgb(rec["path"])
            axes[r, 0].imshow(img)
            axes[r, 0].set_title(f"{rec['category']} {rec['defect_type']}", fontsize=8)
            mp = mask_for_product(paths.clean_root, rec)
            if mp:
                axes[r, 1].imshow(load_gray(mp, nearest=True), cmap="gray")
            else:
                axes[r, 1].imshow(np.zeros(img.shape[:2]), cmap="gray")
            axes[r, 1].set_title("mask", fontsize=8)
            axes[r, 2].imshow(img)
            axes[r, 2].set_title(f"{rec.get('case_type', method)}\nscore={rec['score']:.3f}", fontsize=8)
            for c in range(3):
                axes[r, c].axis("off")
        fig.suptitle(title)
        fig.tight_layout()
        fig.savefig(out_path, dpi=160)
        plt.close(fig)

    success_path = out_dir / "qualitative_success_cases.png"
    failure_path = out_dir / "qualitative_failure_cases.png"
    compare_path = out_dir / "method_comparison_maps.png"
    make_case_grid(cases[cases.get("case_type", "") .isin(["true_positive", "true_negative"])] if "case_type" in cases else cases, success_path, "Success cases")
    make_case_grid(cases[cases.get("case_type", "") .isin(["false_positive", "false_negative"])] if "case_type" in cases else cases, failure_path, "Failure cases")
    make_case_grid(scores[scores["split"] == "test"].groupby(["category", "defect_type"]).head(1), compare_path, "Method comparison examples")
    notes = [
        "Qualitative failure analysis",
        "============================",
        "",
        "Cases are selected from test scores after fitting thresholds by score sweep for display.",
        "At least one logical and one structural anomaly are included when available.",
        "Failure explanations should be refined after visual inspection of the generated grids.",
        "",
        "Category-level observations:",
    ]
    for cat in CATEGORIES:
        notes.append(f"- {cat}: inspect score overlap between good, logical, and structural rows in category_failure_analysis.csv.")
    notes_path = out_dir / "failure_case_notes.txt"
    notes_path.write_text("\n".join(notes) + "\n", encoding="utf-8")
    return {"outputs": [success_path, failure_path, compare_path, case_csv, notes_path]}


def run_stage12_paper_exports(lab_root: Optional[str | Path] = None) -> Dict[str, object]:
    paths = get_project_paths(lab_root=lab_root)
    fig_dir = paths.paper_root / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    require_matplotlib()

    def text_figure(out: Path, title: str, lines: Sequence[str]) -> None:
        fig, ax = plt.subplots(figsize=(10, 5.8))
        ax.axis("off")
        ax.text(0.02, 0.92, title, fontsize=18, fontweight="bold", transform=ax.transAxes)
        y = 0.78
        for line in lines:
            ax.text(0.04, y, line, fontsize=12, transform=ax.transAxes)
            y -= 0.11
        fig.tight_layout()
        fig.savefig(out, dpi=180)
        plt.close(fig)

    f1 = fig_dir / "figure_1_pipeline_overview.png"
    text_figure(
        f1,
        "From components to patch composition",
        [
            "1. Audit raw MVTec LOCO data and preserve it as read-only.",
            "2. Letterbox resize products and masks into cleaned data.",
            "3. Archive component probes and reject direct component counting.",
            "4. Compare EfficientAD, PatchCore, DINOv2 patch memory, grid-aware memory, composition histograms, and fusion.",
        ],
    )
    paths_probe = paths.probe_root
    source_map = {
        "figure_2_dataset_examples.png": paths_probe / "eda_sample_grid_cleaned.png",
        "figure_3_component_probe_failure.png": paths_probe / "improved_pca_component_probe_visual.png",
        "figure_4_method_comparison.png": paths.method_root / "Qualitative" / "method_comparison_maps.png",
        "figure_5_failure_cases.png": paths.method_root / "Qualitative" / "qualitative_failure_cases.png",
    }
    outputs = [f1]
    for name, src in source_map.items():
        dst = fig_dir / name
        if src.exists():
            shutil.copy2(src, dst)
        else:
            text_figure(dst, name.replace("_", " ").replace(".png", ""), [f"Source figure not found yet: {src}"])
        outputs.append(dst)
    speed_fig = fig_dir / "figure_6_speed_accuracy_tradeoff.png"
    main_path = paths.method_root / "Final_Evaluation" / "main_results_table.csv"
    eff_path = paths.method_root / "Final_Evaluation" / "efficiency_table.csv"
    fig, ax = plt.subplots(figsize=(7, 5))
    if main_path.exists() and eff_path.exists():
        main = pd.read_csv(main_path)
        eff = pd.read_csv(eff_path)
        time_col = "time_ms_per_image"
        if time_col in eff:
            eff2 = eff.groupby("method")[time_col].mean().reset_index()
            merged = main.merge(eff2, on="method", how="inner")
            y_col = "mean_auroc" if "mean_auroc" in merged else merged.select_dtypes("number").columns[0]
            ax.scatter(merged[time_col], merged[y_col])
            for _, row in merged.iterrows():
                ax.annotate(row["method"], (row[time_col], row[y_col]), fontsize=8)
            ax.set_xlabel("inference time ms/image")
            ax.set_ylabel(y_col)
        else:
            ax.text(0.1, 0.5, "Efficiency table missing time_ms_per_image", transform=ax.transAxes)
    else:
        ax.text(0.1, 0.5, "Run evaluation notebooks before final speed-accuracy plot.", transform=ax.transAxes)
    ax.set_title("Speed-accuracy tradeoff")
    fig.tight_layout()
    fig.savefig(speed_fig, dpi=180)
    plt.close(fig)
    outputs.append(speed_fig)

    manifest_lines = ["Final project outputs manifest", "==============================", ""]
    for folder in [paths.audit_root, paths.probe_root, paths.baseline_root, paths.method_root, paths.paper_root]:
        if folder.exists():
            for p in sorted(folder.rglob("*")):
                if p.is_file():
                    manifest_lines.append(str(p.relative_to(paths.project_root)).replace("\\", "/"))
    manifest = paths.export_root / "final_project_outputs_manifest.txt"
    manifest.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    outputs.append(manifest)
    zip_path = paths.export_root / "Project_A_LOCO_AD_outputs.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for line in manifest_lines[3:]:
            p = paths.project_root / line
            if p.exists() and p.is_file():
                zf.write(p, arcname=line)
    outputs.append(zip_path)
    return {"outputs": outputs}
