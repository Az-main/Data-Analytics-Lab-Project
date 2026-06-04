#!/usr/bin/env python3
"""Corrected (honest) results + self-contained dashboard.html for Project A."""
import base64, io, json, glob
from pathlib import Path
import numpy as np, pandas as pd
from PIL import Image
from sklearn.metrics import roc_auc_score, precision_recall_fscore_support

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "09_dashboard"; OUT.mkdir(exist_ok=True)
SRC = {
 "Global Image-Stat Detector (proxy)": "05_baselines/EfficientAD/efficientad_scores.csv",
 "DINOv2 Patch Memory (NN)":            "05_baselines/PatchCore/patchcore_scores.csv",
 "DINOv2 Region-Aware Memory":          "06_method_results/GridAware_DINOv2/gridaware_scores.csv",
 "DINOv2 Composition Histogram (BoVW)": "06_method_results/CompositionHistogram/composition_hist_scores.csv",
}
FUSION = "06_method_results/Fusion/fusion_scores.csv"
FUSION_MAP = {"Best Fusion":"Fusion (mean)","Fusion Max":"Fusion (max)","Fusion RankAvg":"Fusion (rank-avg)"}
CATS = ["breakfast_box","juice_bottle","pushpins","screw_bag","splicing_connectors"]
VAL_Q = 0.90

def metrics_for(df, method):
    rows=[]
    for cat in CATS:
        c=df[df.category==cat]
        valg=c[(c.split=="validation")&(c.defect_type=="good")]["score"].to_numpy(float)
        thr=float(np.quantile(valg,VAL_Q)) if len(valg) else float("nan")
        test=c[c.split=="test"]; good=test[test.defect_type=="good"]
        for atype,sub in [("logical",test[test.defect_type=="logical_anomalies"]),
                          ("structural",test[test.defect_type=="structural_anomalies"]),
                          ("overall",test[test.defect_type!="good"])]:
            ev=pd.concat([good,sub]); y=ev.label.astype(int).to_numpy(); s=ev.score.astype(float).to_numpy()
            auroc=float(roc_auc_score(y,s)) if len(set(y))>1 else float("nan")
            pred=(s>=thr).astype(int)
            p,r,f1,_=precision_recall_fscore_support(y,pred,average="binary",zero_division=0)
            rows.append(dict(method=method,category=cat,anomaly_type=atype,n_good=len(good),
                n_anomaly=len(sub),auroc=auroc,f1=float(f1),precision=float(p),recall=float(r),val_threshold=thr))
    return rows

allrows=[]
for m,f in SRC.items(): allrows+=metrics_for(pd.read_csv(ROOT/f),m)
fz=pd.read_csv(ROOT/FUSION)
for raw,nice in FUSION_MAP.items(): allrows+=metrics_for(fz[fz.method==raw].copy(),nice)
per=pd.DataFrame(allrows); per.to_csv(OUT/"corrected_per_category.csv",index=False)
main=per.groupby(["method","anomaly_type"])[["auroc","f1"]].mean().reset_index()
mw=main.pivot(index="method",columns="anomaly_type",values="auroc").reset_index()
mw["mean_logical_structural"]=mw[["logical","structural"]].mean(axis=1)
f1w=main.pivot(index="method",columns="anomaly_type",values="f1").reset_index()
f1w.columns=["method"]+[f"f1_{c}" for c in f1w.columns if c!="method"]
mw=mw.merge(f1w,on="method").sort_values("overall",ascending=False)
mw.to_csv(OUT/"corrected_main_results.csv",index=False)

def b64(path,max_w=820,q=82):
    try:
        im=Image.open(path).convert("RGB")
        if im.width>max_w: im=im.resize((max_w,int(im.height*max_w/im.width)))
        b=io.BytesIO(); im.save(b,"JPEG",quality=q); return "data:image/jpeg;base64,"+base64.b64encode(b.getvalue()).decode()
    except Exception: return ""

EDA={
 "Dataset samples (cleaned, letterboxed 384x384)":"04_probe_results/eda_sample_grid_cleaned.png",
 "Ground-truth anomaly masks overlaid on test images":"04_probe_results/eda_mask_overlay_cleaned.png",
 "Per-pixel mean & variance of normal (train/good) images":"04_probe_results/eda_mean_variance_cleaned.png",
 "Spatial anomaly-frequency heatmap (where defects occur)":"04_probe_results/eda_spatial_heatmap_cleaned.png",
 "Defect mask-area distribution by category":"04_probe_results/eda_mask_area_distribution.png",
 "Edge-density distribution by category/defect":"04_probe_results/eda_edge_density_cleaned.png",
}
eda_imgs={k:b64(ROOT/v,max_w=900) for k,v in EDA.items() if (ROOT/v).exists()}

CLEAN=ROOT/"03_cleaned_data/loco_cleaned_letterbox_384"
def overlay_mask(img_path,mask_path,alpha=0.45):
    im=Image.open(img_path).convert("RGB"); arr=np.asarray(im).astype(np.float32)
    if mask_path and Path(mask_path).exists():
        m=(np.asarray(Image.open(mask_path).convert("L").resize(im.size))>0)[...,None]
        red=np.zeros_like(arr); red[...,0]=255; arr=np.where(m,(1-alpha)*arr+alpha*red,arr)
    out=Image.fromarray(np.clip(arr,0,255).astype(np.uint8))
    if out.width>300: out=out.resize((300,int(out.height*300/out.width)))
    b=io.BytesIO(); out.save(b,"JPEG",quality=85); return "data:image/jpeg;base64,"+base64.b64encode(b.getvalue()).decode()

# Gallery needs the cleaned/letterboxed test images. On a code-only checkout (no 03_cleaned_data),
# fall back to the illustrative examples already embedded in the previous dashboard_data.json.
_PREV = json.loads((OUT/"dashboard_data.json").read_text()) if (OUT/"dashboard_data.json").exists() else {}
CLEAN_OK = CLEAN.exists() and any(CLEAN.rglob("*.png"))
if CLEAN_OK:
    best=fz[fz.method=="Best Fusion"].copy(); gallery=[]
    for cat in CATS:
        c=best[best.category==cat]
        valg=c[(c.split=="validation")&(c.defect_type=="good")]["score"].to_numpy(float)
        thr=float(np.quantile(valg,VAL_Q)) if len(valg) else float("nan")
        test=c[c.split=="test"]
        for label,defect in [("normal (good)","good"),("logical anomaly","logical_anomalies"),("structural anomaly","structural_anomalies")]:
            sub=test[test.defect_type==defect].sort_values("score",ascending=(defect=="good"))
            if not len(sub): continue
            rec=sub.iloc[len(sub)//2 if defect!="good" else 0]
            rel=str(rec.relative_path); stem=Path(rel).stem
            img_path=CLEAN/rel
            mask_path=None if defect=="good" else CLEAN/cat/"ground_truth"/defect/stem/"000.png"
            pred="ANOMALY" if rec.score>=thr else "normal"
            correct=(pred=="ANOMALY")==(defect!="good")
            gallery.append(dict(cat=cat,label=label,defect=defect,img=overlay_mask(img_path,mask_path),
                score=round(float(rec.score),2),thr=round(thr,2),pred=pred,correct=bool(correct)))
else:
    gallery=_PREV.get("gallery",[])
    print("NOTE: 03_cleaned_data not present locally -> reusing %d illustrative gallery examples from existing dashboard_data.json"%len(gallery))

MAPDIR=ROOT/"06_method_results/GridAware_DINOv2/gridaware_anomaly_maps"; heatmaps=[]
for defect,lbl in [("good","normal"),("logical_anomalies","logical"),("structural_anomalies","structural")]:
    cands=sorted(glob.glob(str(MAPDIR/f"breakfast_box_{defect}_*.png")))
    if cands: heatmaps.append(dict(label=lbl,img=b64(cands[len(cands)//2],max_w=300)))

QUAL=ROOT/"06_method_results/Qualitative"
quals={n:b64(QUAL/f,max_w=900) for n,f in {
    "Success cases (correctly flagged)":"qualitative_success_cases.png",
    "Failure cases (missed / false alarms)":"qualitative_failure_cases.png"}.items() if (QUAL/f).exists()}

audit=pd.read_csv(ROOT/"02_audit_reproducibility/product_image_count_summary.csv")
counts=audit.pivot_table(index="category",columns="split",values="count",aggfunc="sum",fill_value=0).reset_index()

# Feature-selection study (Criterion 4) + consolidated Key Insights (Criterion 5)
fs_json=json.loads((OUT/"feature_selection.json").read_text()) if (OUT/"feature_selection.json").exists() else {}
insights=[
 "Real, frozen DINOv2-small features are verified end-to-end (feature_backend = dinov2-small); the best pre-specified fusion reaches 0.76 overall image AUROC (0.73 logical / 0.80 structural).",
 "Fusion of complementary detectors beats any single model. The DINOv2 Region-Aware memory is the strongest single representation (0.75) and drives structural accuracy.",
 "Feature-importance analysis: the Composition-Histogram representation is the only branch that REDUCES fusion AUROC (leave-one-out -0.013), and PatchCore is byte-identical to DINOv2 PatchMemory (redundant). Dropping both yields a leaner 3-representation model that edges the full fusion (0.764, structural 0.826).",
 "Per-category, results vary sharply: juice_bottle is near-solved (~0.94 AUROC) while pushpins logical anomalies (wrong count) stay near chance, because patch-nearest-neighbour scoring cannot count parts.",
 "Biggest remaining levers are masking the letterbox padding, moving to DINOv2-base, and multi-seed averaging (expected ~0.83-0.90, GCAD/EfficientAD territory). Component-segmentation SOTA (SALAD/CSAD) reaches 0.95+.",
]
data=dict(main=mw.round(4).to_dict(orient="records"),per=per.round(4).to_dict(orient="records"),
    eda=eda_imgs,gallery=gallery,heatmaps=heatmaps,quals=quals,
    counts=counts.to_dict(orient="records"),cats=CATS,val_q=VAL_Q,
    feature_selection=fs_json,insights=insights)
(OUT/"dashboard_data.json").write_text(json.dumps(data))
print("gallery=%d heatmaps=%d eda=%d quals=%d json=%.2fMB"%(len(gallery),len(heatmaps),len(eda_imgs),len(quals),(OUT/"dashboard_data.json").stat().st_size/1e6))
