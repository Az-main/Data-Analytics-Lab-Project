from __future__ import annotations

from pathlib import Path

import nbformat as nbf


NOTEBOOKS = [
    {
        "file": "01_preprocessing_reproducibility.ipynb",
        "title": "Notebook 01: Preprocessing and Reproducibility",
        "purpose": (
            "Create the clean project foundation: environment records, raw dataset audit, separate product/mask counts, "
            "MD5 and perceptual hashes, aspect-ratio-preserving 384x384 letterbox data, mask verification, and protocol notes."
        ),
        "stage_call": "result = run_stage01_preprocessing(lab_root=LAB_ROOT, target_size=384)",
        "imports": "from loco_project_utils import run_stage01_preprocessing",
        "outputs": [
            "02_audit_reproducibility/environment_versions.csv",
            "02_audit_reproducibility/requirements_freeze.txt",
            "02_audit_reproducibility/dataset_audit_full.csv",
            "02_audit_reproducibility/dataset_product_images_only.csv",
            "02_audit_reproducibility/dataset_masks_only.csv",
            "02_audit_reproducibility/product_image_count_summary.csv",
            "02_audit_reproducibility/mask_count_summary.csv",
            "02_audit_reproducibility/resize_letterbox_metadata.csv",
            "02_audit_reproducibility/cleaned_letterbox_verify.csv",
            "02_audit_reproducibility/image_hashes.csv",
            "02_audit_reproducibility/config_preprocessing.json",
            "02_audit_reproducibility/preprocessing_protocol.txt",
            "03_cleaned_data/loco_cleaned_letterbox_384/",
        ],
        "acceptance": [
            "All five categories show OK.",
            "Product images = 3651, masks = 1246, total PNG = 4897, corrupted = 0.",
            "Wrong-size cleaned files = 0 and non-binary masks = 0.",
            "Exact duplicate leakage candidates are saved and reported.",
        ],
    },
    {
        "file": "02_eda_cleaned_letterbox.ipynb",
        "title": "Notebook 02: EDA Recheck on Cleaned Letterbox Dataset",
        "purpose": (
            "Rerun descriptive EDA on the cleaned letterbox dataset, not on raw or square-stretched data. "
            "The test anomalies are inspected for EDA only and are not used for model tuning."
        ),
        "stage_call": "result = run_stage02_eda(lab_root=LAB_ROOT)",
        "imports": "from loco_project_utils import run_stage02_eda",
        "outputs": [
            "04_probe_results/eda_sample_grid_cleaned.png",
            "04_probe_results/eda_mask_overlay_cleaned.png",
            "04_probe_results/eda_intensity_histograms_cleaned.png",
            "04_probe_results/eda_mean_variance_cleaned.png",
            "04_probe_results/eda_edge_density_cleaned.png",
            "04_probe_results/eda_mask_area_distribution.png",
            "04_probe_results/eda_spatial_heatmap_cleaned.png",
            "04_probe_results/eda_summary_table.csv",
        ],
        "acceptance": [
            "All EDA figures are saved under 04_probe_results.",
            "EDA conclusions do not claim component counting is reliable.",
            "The notebook states test anomalies are descriptive EDA only.",
        ],
    },
    {
        "file": "03_dinov2_component_probe_archive.ipynb",
        "title": "Notebook 03: DINOv2 Component Probe Archive",
        "purpose": (
            "Archive the K-means and PCA foreground component probes. The conclusion is that patch representations are useful, "
            "but unsupervised instance extraction/counting is unreliable, so the final method avoids graph nodes and component counting."
        ),
        "stage_call": "result = run_stage03_component_probe(lab_root=LAB_ROOT, backend=FEATURE_BACKEND)",
        "imports": "from loco_project_utils import run_stage03_component_probe",
        "pre_code": "FEATURE_BACKEND = 'auto'  # use 'dinov2' to require facebook/dinov2-small; auto falls back locally if needed",
        "outputs": [
            "04_probe_results/probe_pca_rgb.png",
            "04_probe_results/probe_kmeans_segmentation.png",
            "04_probe_results/dinov2_kmeans_count_table.csv",
            "04_probe_results/improved_pca_component_probe_visual.png",
            "04_probe_results/improved_pca_component_probe_raw.csv",
            "04_probe_results/improved_pca_component_probe_summary.csv",
            "04_probe_results/component_probe_conclusion.txt",
        ],
        "acceptance": [
            "The notebook explains why component graph/GNN modeling is no longer the main method.",
            "Raw count tables and visual probe outputs are saved.",
        ],
    },
    {
        "file": "04_baseline_efficientad.ipynb",
        "title": "Notebook 04: EfficientAD Baseline",
        "purpose": (
            "Run the EfficientAD baseline stage. If Anomalib is not available, the local fallback writes clearly labeled proxy "
            "outputs so the pipeline remains reproducible; rerun with Anomalib for paper-ready EfficientAD numbers."
        ),
        "stage_call": "result = run_stage04_efficientad(lab_root=LAB_ROOT)",
        "imports": "from loco_project_utils import run_stage04_efficientad",
        "outputs": [
            "05_baselines/EfficientAD/efficientad_scores.csv",
            "05_baselines/EfficientAD/efficientad_results_per_category.csv",
            "05_baselines/EfficientAD/efficientad_results_summary.csv",
            "05_baselines/EfficientAD/efficientad_config.yaml",
            "05_baselines/EfficientAD/efficientad_logs.txt",
            "05_baselines/EfficientAD/efficientad_runtime_memory.csv",
            "05_baselines/EfficientAD/efficientad_anomaly_maps/",
        ],
        "acceptance": [
            "Train/good is the only fitting split.",
            "Logical and structural scores are reported separately.",
            "Per-image scores are saved, not only summaries.",
        ],
    },
    {
        "file": "05_baseline_patchcore.ipynb",
        "title": "Notebook 05: PatchCore Baseline",
        "purpose": (
            "Run a PatchCore-style patch memory baseline using train/good only. The notebook saves per-image scores, anomaly maps, "
            "runtime, memory-bank size, and logical/structural metrics."
        ),
        "stage_call": "result = run_stage05_patchcore(lab_root=LAB_ROOT, backend=FEATURE_BACKEND)",
        "imports": "from loco_project_utils import run_stage05_patchcore",
        "pre_code": "FEATURE_BACKEND = 'auto'  # auto uses DINOv2 if available, otherwise deterministic patch statistics",
        "outputs": [
            "05_baselines/PatchCore/patchcore_scores.csv",
            "05_baselines/PatchCore/patchcore_results_per_category.csv",
            "05_baselines/PatchCore/patchcore_results_summary.csv",
            "05_baselines/PatchCore/patchcore_config.yaml",
            "05_baselines/PatchCore/patchcore_logs.txt",
            "05_baselines/PatchCore/patchcore_runtime_memory.csv",
            "05_baselines/PatchCore/patchcore_anomaly_maps/",
        ],
        "acceptance": [
            "Runs on all five categories.",
            "Saves image-level scores for every validation/test image.",
            "Reports memory-bank size and inference time.",
        ],
    },
    {
        "file": "06_dinov2_patch_memory_baseline.ipynb",
        "title": "Notebook 06: DINOv2 Patch-Memory Baseline",
        "purpose": (
            "Implement a frozen-DINOv2 patch-memory baseline similar in spirit to PatchCore/AnomalyDINO. "
            "It is a baseline, not the project novelty."
        ),
        "stage_call": "result = run_stage06_dinov2_patchmemory(lab_root=LAB_ROOT, backend=FEATURE_BACKEND)",
        "imports": "from loco_project_utils import run_stage06_dinov2_patchmemory",
        "pre_code": "FEATURE_BACKEND = 'auto'  # set to 'dinov2' to require frozen facebook/dinov2-small",
        "outputs": [
            "06_method_results/DINOv2_PatchMemory/dinov2_patchmemory_scores.csv",
            "06_method_results/DINOv2_PatchMemory/dinov2_patchmemory_results_per_category.csv",
            "06_method_results/DINOv2_PatchMemory/dinov2_patchmemory_results_summary.csv",
            "06_method_results/DINOv2_PatchMemory/dinov2_patchmemory_runtime_memory.csv",
            "06_method_results/DINOv2_PatchMemory/dinov2_patchmemory_config.json",
            "06_method_results/DINOv2_PatchMemory/dinov2_patchmemory_anomaly_maps/",
        ],
        "acceptance": [
            "Produces per-image scores and patch anomaly maps.",
            "Reports memory size and inference time.",
            "Does not claim novelty beyond baseline status.",
        ],
    },
    {
        "file": "07_grid_aware_patch_composition.ipynb",
        "title": "Notebook 07: Grid-Aware Patch-Composition Method",
        "purpose": (
            "Main proposed method: preserve approximate patch location by comparing each patch to normal memories from the same "
            "coarse spatial region. This models patch composition without component extraction."
        ),
        "stage_call": "result = run_stage07_gridaware(lab_root=LAB_ROOT, backend=FEATURE_BACKEND, region_size=6)",
        "imports": "from loco_project_utils import run_stage07_gridaware",
        "pre_code": "FEATURE_BACKEND = 'auto'\nREGION_SIZE = 6",
        "outputs": [
            "06_method_results/GridAware_DINOv2/gridaware_scores.csv",
            "06_method_results/GridAware_DINOv2/gridaware_results_per_category.csv",
            "06_method_results/GridAware_DINOv2/gridaware_results_summary.csv",
            "06_method_results/GridAware_DINOv2/gridaware_runtime_memory.csv",
            "06_method_results/GridAware_DINOv2/gridaware_config.json",
            "06_method_results/GridAware_DINOv2/gridaware_ablation_topk.csv",
            "06_method_results/GridAware_DINOv2/gridaware_ablation_region_size.csv",
            "06_method_results/GridAware_DINOv2/gridaware_anomaly_maps/",
        ],
        "acceptance": [
            "Compares or records exact/coarse region choices via ablation files.",
            "Uses validation/good policy for model-selection notes.",
            "Saves per-image scores and maps.",
        ],
    },
    {
        "file": "08_composition_histogram_method.ipynb",
        "title": "Notebook 08: Composition-Histogram Method",
        "purpose": (
            "Build a global composition model from patch visual words. The method avoids segmentation, masks, instance extraction, "
            "and component counting."
        ),
        "stage_call": "result = run_stage08_composition_histogram(lab_root=LAB_ROOT, backend=FEATURE_BACKEND, k_selected=32)",
        "imports": "from loco_project_utils import run_stage08_composition_histogram",
        "pre_code": "FEATURE_BACKEND = 'auto'\nK_SELECTED = 32",
        "outputs": [
            "06_method_results/CompositionHistogram/composition_hist_scores.csv",
            "06_method_results/CompositionHistogram/composition_hist_results_per_category.csv",
            "06_method_results/CompositionHistogram/composition_hist_results_summary.csv",
            "06_method_results/CompositionHistogram/composition_hist_ablation_k.csv",
            "06_method_results/CompositionHistogram/composition_hist_config.json",
            "06_method_results/CompositionHistogram/composition_hist_visualizations/",
        ],
        "acceptance": [
            "Reports K ablation.",
            "Reports scoring model columns.",
            "Saves one histogram visualization per category.",
        ],
    },
    {
        "file": "09_fusion_experiments.ipynb",
        "title": "Notebook 09: Fusion Experiments",
        "purpose": (
            "Fuse method scores after validation/good z-normalization. Raw scores are not multiplied or combined directly."
        ),
        "stage_call": "result = run_stage09_fusion(lab_root=LAB_ROOT)",
        "imports": "from loco_project_utils import run_stage09_fusion",
        "outputs": [
            "06_method_results/Fusion/fusion_scores.csv",
            "06_method_results/Fusion/fusion_results_per_category.csv",
            "06_method_results/Fusion/fusion_results_summary.csv",
            "06_method_results/Fusion/fusion_ablation.csv",
            "06_method_results/Fusion/fusion_config.json",
        ],
        "acceptance": [
            "Fusion uses validation/good statistics only.",
            "Fusion table includes every rule tested.",
            "Best fusion is selected without test-label tuning.",
        ],
    },
    {
        "file": "10_full_evaluation_tables.ipynb",
        "title": "Notebook 10: Full Evaluation Tables",
        "purpose": (
            "Compile the final method comparison tables, per-category metrics, ablations, efficiency rows, and all method scores."
        ),
        "stage_call": "result = run_stage10_final_tables(lab_root=LAB_ROOT)",
        "imports": "from loco_project_utils import run_stage10_final_tables",
        "outputs": [
            "06_method_results/Final_Evaluation/main_results_table.csv",
            "06_method_results/Final_Evaluation/per_category_results_table.csv",
            "06_method_results/Final_Evaluation/ablation_table.csv",
            "06_method_results/Final_Evaluation/efficiency_table.csv",
            "06_method_results/Final_Evaluation/final_scores_all_methods.csv",
        ],
        "acceptance": [
            "All methods use the same test split and labels.",
            "Logical and structural metrics are reported separately.",
            "External literature numbers are not mixed with reproduced rows.",
        ],
    },
    {
        "file": "11_qualitative_failure_analysis.ipynb",
        "title": "Notebook 11: Qualitative Failure Analysis",
        "purpose": (
            "Create qualitative success/failure figures and category-level observations. This includes logical and structural "
            "failure cases when available."
        ),
        "stage_call": "result = run_stage11_qualitative(lab_root=LAB_ROOT)",
        "imports": "from loco_project_utils import run_stage11_qualitative",
        "outputs": [
            "06_method_results/Qualitative/qualitative_success_cases.png",
            "06_method_results/Qualitative/qualitative_failure_cases.png",
            "06_method_results/Qualitative/method_comparison_maps.png",
            "06_method_results/Qualitative/category_failure_analysis.csv",
            "06_method_results/Qualitative/failure_case_notes.txt",
        ],
        "acceptance": [
            "Includes logical and structural anomalies when present in score files.",
            "Includes category-level observations for all five categories.",
            "Does not cherry-pick only successful examples.",
        ],
    },
    {
        "file": "12_paper_figures_export.ipynb",
        "title": "Notebook 12: Paper Figures and Export",
        "purpose": (
            "Generate final paper-ready figures and an export manifest/package for sharing the project outputs."
        ),
        "stage_call": "result = run_stage12_paper_exports(lab_root=LAB_ROOT)",
        "imports": "from loco_project_utils import run_stage12_paper_exports",
        "outputs": [
            "07_paper_draft/figures/figure_1_pipeline_overview.png",
            "07_paper_draft/figures/figure_2_dataset_examples.png",
            "07_paper_draft/figures/figure_3_component_probe_failure.png",
            "07_paper_draft/figures/figure_4_method_comparison.png",
            "07_paper_draft/figures/figure_5_failure_cases.png",
            "07_paper_draft/figures/figure_6_speed_accuracy_tradeoff.png",
            "08_exports/final_project_outputs_manifest.txt",
            "08_exports/Project_A_LOCO_AD_outputs.zip",
        ],
        "acceptance": [
            "All figures render clearly at publication size.",
            "The manifest lists generated outputs and paths.",
            "No raw dataset files are moved or deleted.",
        ],
    },
]


PATH_SETUP = r"""
from pathlib import Path
import sys

CURRENT_DIR = Path.cwd().resolve()

# Edit this one variable when moving between local execution and Colab.
LAB_ROOT = Path("PUT_PARENT_FOLDER_HERE")
if str(LAB_ROOT) == "PUT_PARENT_FOLDER_HERE":
    for candidate in [CURRENT_DIR, *CURRENT_DIR.parents]:
        if (candidate / "Phase 1").exists():
            LAB_ROOT = candidate
            break
    else:
        raise FileNotFoundError("Set LAB_ROOT to the parent folder containing 'Phase 1' and 'Project_A_LOCO_AD'.")

RAW_DATA_ROOT = LAB_ROOT / "Phase 1"
PROJECT_ROOT = LAB_ROOT / "Project_A_LOCO_AD"

NOTEBOOK_ROOT = PROJECT_ROOT / "01_notebooks"
AUDIT_ROOT = PROJECT_ROOT / "02_audit_reproducibility"
CLEAN_DATA_ROOT = PROJECT_ROOT / "03_cleaned_data"
PROBE_ROOT = PROJECT_ROOT / "04_probe_results"
BASELINE_ROOT = PROJECT_ROOT / "05_baselines"
METHOD_ROOT = PROJECT_ROOT / "06_method_results"
PAPER_ROOT = PROJECT_ROOT / "07_paper_draft"
EXPORT_ROOT = PROJECT_ROOT / "08_exports"

for folder in [NOTEBOOK_ROOT, AUDIT_ROOT, CLEAN_DATA_ROOT, PROBE_ROOT, BASELINE_ROOT, METHOD_ROOT, PAPER_ROOT, EXPORT_ROOT]:
    folder.mkdir(parents=True, exist_ok=True)

if str(NOTEBOOK_ROOT) not in sys.path:
    sys.path.insert(0, str(NOTEBOOK_ROOT))

CATEGORIES = ["breakfast_box", "juice_bottle", "pushpins", "screw_bag", "splicing_connectors"]
for cat in CATEGORIES:
    print(cat, "OK" if (RAW_DATA_ROOT / cat).exists() else "MISSING")
"""


def md_list(items):
    return "\n".join(f"- `{item}`" for item in items)


def build_notebook(spec: dict) -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
    }
    nb.cells = [
        nbf.v4.new_markdown_cell(f"# {spec['title']}\n\n{spec['purpose']}"),
        nbf.v4.new_markdown_cell(
            "## Path Setup\n\n"
            "This cell is local/Colab adaptable. Change only `LAB_ROOT` if automatic detection does not find the parent folder."
        ),
        nbf.v4.new_code_cell(PATH_SETUP.strip()),
        nbf.v4.new_markdown_cell("## Required Outputs\n\n" + md_list(spec["outputs"])),
        nbf.v4.new_markdown_cell("## Acceptance Checks\n\n" + "\n".join(f"- {item}" for item in spec["acceptance"])),
        nbf.v4.new_code_cell("from loco_project_utils import set_reproducible_seed\nset_reproducible_seed(42)"),
    ]
    if spec.get("pre_code"):
        nb.cells.append(nbf.v4.new_code_cell(spec["pre_code"]))
    nb.cells.extend(
        [
            nbf.v4.new_code_cell(spec["imports"]),
            nbf.v4.new_markdown_cell("## Run Stage\n\nRun this cell to generate the notebook outputs."),
            nbf.v4.new_code_cell(spec["stage_call"]),
            nbf.v4.new_markdown_cell("## Outputs Saved\n\nThe cell below lists the concrete files created by this run."),
            nbf.v4.new_code_cell(
                "from pathlib import Path\n"
                "print('Outputs saved:')\n"
                "for out in result.get('outputs', []):\n"
                "    p = Path(out)\n"
                "    print('-', p)\n"
                "if 'checks' in result:\n"
                "    print('\\nAcceptance check values:')\n"
                "    for key, value in result['checks'].items():\n"
                "        print(f'{key}: {value}')"
            ),
            nbf.v4.new_markdown_cell(
                "## Notes\n\n"
                "Training or fitting uses `train/good` only. `validation/good` is reserved for calibration, threshold selection, "
                "or hyperparameter selection. Test data is used for final evaluation only. Ground-truth masks are used only "
                "for localization evaluation or visualization."
            ),
        ]
    )
    return nb


def main() -> None:
    root = Path(__file__).resolve().parent
    for spec in NOTEBOOKS:
        nb = build_notebook(spec)
        nbf.write(nb, root / spec["file"])
        print(root / spec["file"])


if __name__ == "__main__":
    main()
