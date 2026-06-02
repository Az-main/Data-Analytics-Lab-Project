const fs=require('fs'),path=require('path');
const D=require('/tmp/node_modules/docx');
const {Document,Packer,Paragraph,TextRun,Table,TableRow,TableCell,ImageRun,AlignmentType,
 HeadingLevel,BorderStyle,WidthType,ShadingType,PageNumber,Header,Footer,ExternalHyperlink}=D;
const ROOT=path.resolve(__dirname,'..');
const data=JSON.parse(fs.readFileSync(path.join(__dirname,'dashboard_data.json')));
const FIG=path.join(ROOT,'07_paper_draft','figures');
const PR=ROOT;

const order=["Fusion (max)","Fusion (mean)","Region-Aware Patch Memory","Fusion (rank-avg)","Composition Histogram (BoVW)","Global Image-Stat Detector","Patch-Stat Memory (NN)"];
const main=order.map(m=>data.main.find(r=>r.method===m)).filter(Boolean);
const f3=x=>(x==null||isNaN(x))?'—':x.toFixed(3);

const border={style:BorderStyle.SINGLE,size:1,color:"BBBBBB"};
const borders={top:border,bottom:border,left:border,right:border};
const cell=(t,w,{head=false,bold=false,al=AlignmentType.RIGHT}={})=>new TableCell({borders,width:{size:w,type:WidthType.DXA},
 shading:{fill:head?"D6E2F3":"FFFFFF",type:ShadingType.CLEAR},margins:{top:60,bottom:60,left:110,right:110},
 children:[new Paragraph({alignment:al,children:[new TextRun({text:String(t),bold:head||bold,size:19})]})]});

// main results table
const mc=[3360,1500,1500,1500,1500];
const headRow=new TableRow({children:[cell("Method",mc[0],{head:true,al:AlignmentType.LEFT}),
 cell("Logical",mc[1],{head:true}),cell("Structural",mc[2],{head:true}),cell("Overall",mc[3],{head:true}),cell("F1 (overall)",mc[4],{head:true})]});
const bodyRows=main.map((r,i)=>new TableRow({children:[
 cell(r.method,mc[0],{al:AlignmentType.LEFT,bold:i===0}),cell(f3(r.logical),mc[1]),cell(f3(r.structural),mc[2]),
 cell(f3(r.overall),mc[3],{bold:i===0}),cell(f3(r.f1_overall),mc[4])]}));
const resultsTable=new Table({width:{size:9360,type:WidthType.DXA},columnWidths:mc,rows:[headRow,...bodyRows]});

// dataset table
const totals={train:0,validation:0,test:0};data.counts.forEach(r=>{['train','validation','test'].forEach(k=>totals[k]+=(r[k]||0));});
const dc=[3360,2000,2000,2000];
const dHead=new TableRow({children:[cell("Category",dc[0],{head:true,al:AlignmentType.LEFT}),cell("Train (good)",dc[1],{head:true}),cell("Validation (good)",dc[2],{head:true}),cell("Test",dc[3],{head:true})]});
const dBody=data.counts.map(r=>new TableRow({children:[cell(r.category,dc[0],{al:AlignmentType.LEFT}),cell(r.train||0,dc[1]),cell(r.validation||0,dc[2]),cell(r.test||0,dc[3])]}));
const dTot=new TableRow({children:[cell("Total",dc[0],{bold:true,al:AlignmentType.LEFT}),cell(totals.train,dc[1],{bold:true}),cell(totals.validation,dc[2],{bold:true}),cell(totals.test,dc[3],{bold:true})]});
const dataTable=new Table({width:{size:9360,type:WidthType.DXA},columnWidths:dc,rows:[dHead,...dBody,dTot]});

const img=(file,w,h,desc)=>new Paragraph({alignment:AlignmentType.CENTER,spacing:{before:120,after:60},
 children:[new ImageRun({type:"png",data:fs.readFileSync(file),transformation:{width:w,height:h},
 altText:{title:desc,description:desc,name:desc}})]});
const cap=t=>new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:160},children:[new TextRun({text:t,italics:true,size:18,color:"555555"})]});
const H1=t=>new Paragraph({heading:HeadingLevel.HEADING_1,children:[new TextRun(t)]});
const H2=t=>new Paragraph({heading:HeadingLevel.HEADING_2,children:[new TextRun(t)]});
const P=(t,opt={})=>new Paragraph({spacing:{after:120},alignment:opt.j?AlignmentType.JUSTIFIED:AlignmentType.LEFT,children:[new TextRun({text:t,size:22})]});
const bullet=t=>new Paragraph({numbering:{reference:"b",level:0},spacing:{after:60},children:[new TextRun({text:t,size:22})]});
const ref=(n,t)=>new Paragraph({spacing:{after:60},children:[new TextRun({text:`[${n}] `,bold:true,size:19}),new TextRun({text:t,size:19})]});

const doc=new Document({
 styles:{default:{document:{run:{font:"Calibri",size:22}}},paragraphStyles:[
  {id:"Heading1",name:"Heading 1",basedOn:"Normal",next:"Normal",quickFormat:true,run:{size:28,bold:true,color:"1F3864",font:"Calibri"},paragraph:{spacing:{before:240,after:120},outlineLevel:0}},
  {id:"Heading2",name:"Heading 2",basedOn:"Normal",next:"Normal",quickFormat:true,run:{size:24,bold:true,color:"2E5496",font:"Calibri"},paragraph:{spacing:{before:160,after:80},outlineLevel:1}}]},
 numbering:{config:[{reference:"b",levels:[{level:0,format:D.LevelFormat.BULLET,text:"•",alignment:AlignmentType.LEFT,style:{paragraph:{indent:{left:540,hanging:260}}}}]}]},
 sections:[{
  properties:{page:{size:{width:12240,height:15840},margin:{top:1180,right:1440,bottom:1180,left:1440}}},
  footers:{default:new Footer({children:[new Paragraph({alignment:AlignmentType.CENTER,children:[new TextRun({text:"Project A — MVTec LOCO Anomaly Detection   |   Page ",size:16,color:"888888"}),new TextRun({children:[PageNumber.CURRENT],size:16,color:"888888"})]})]})},
  children:[
   new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:40},children:[new TextRun({text:"A Lightweight, Reproducible Two-Branch Baseline for Logical and Structural Anomaly Detection on MVTec LOCO",bold:true,size:30,color:"1F3864"})]}),
   new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:160},children:[new TextRun({text:"Data Analytics Lab — Project A Technical Report",size:20,color:"666666"})]}),

   H1("Abstract"),
   P("We study unsupervised detection of logical and structural anomalies on the MVTec LOCO AD benchmark, where models are trained only on defect-free images and must flag both local defects (scratches, dents) and logical violations (missing, extra, or misplaced components). We implement a fully reproducible pipeline: a leakage-audited preprocessing stage, exploratory analysis, four anomaly scorers, and a validation-normalised fusion. To keep the study honest and lightweight, all detectors operate on reproducible handcrafted patch descriptors rather than pretrained backbones. Our best fusion reaches an overall image-level AUROC of 0.74 (0.71 logical / 0.78 structural), establishing a transparent baseline; we analyse failure modes per category and document a clear DINOv2 upgrade path expected to close most of the gap to the published state of the art (0.95+).",{j:true}),

   H1("1. Introduction"),
   P("Industrial visual inspection increasingly relies on anomaly detection trained without labelled defects, because defects are rare and diverse. MVTec LOCO AD [1] is the standard benchmark for this setting and is distinctive in that it separates two anomaly families. Structural anomalies are local texture/shape defects, while logical anomalies preserve locally-normal appearance but violate global rules — e.g. a breakfast box missing a fruit, or pushpins in the wrong count. Logical anomalies are hard precisely because every local patch can look normal; only the global composition is wrong [1]. This project builds an end-to-end, reproducible system that (i) audits and cleans the data, (ii) surfaces only decision-relevant EDA, (iii) scores anomalies with complementary models, and (iv) presents results in an interactive dashboard with a short report.",{j:true}),

   H1("2. Dataset and Preprocessing"),
   P("MVTec LOCO AD contains five categories. Each provides defect-free training images, a held-out validation set of defect-free images, and a test set mixing good, logical, and structural images with pixel ground-truth masks. We never use anomalous images or masks during fitting.",{j:true}),
   dataTable,
   cap("Table 1. Image counts per category and split. Models fit on Train(good) only; Validation(good) sets the decision threshold; Test is held out for evaluation."),
   P("Preprocessing emphasises reproducibility and leakage safety: (a) the raw dataset is treated as read-only; (b) every image is resized to 384×384 with aspect-ratio-preserving letterboxing (bilinear for images, nearest-neighbour + re-binarisation for masks); (c) we compute MD5 and average-hash fingerprints to detect duplicate leakage across splits (none found); (d) environment versions and a full dependency freeze are stored. Audit totals: 3,651 product images and 1,246 mask files, 0 corrupted, 0 wrong-size after cleaning.",{j:true}),
   img(path.join(PR,'04_probe_results','eda_mask_overlay_cleaned.png'),430,344,"Anomaly mask overlays"),
   cap("Figure 1. Representative test images with ground-truth anomaly regions overlaid (red). Logical anomalies often have large, diffuse masks; structural anomalies are localised."),

   H1("3. Methods"),
   P("Each image is divided into a grid of patches; every patch is described by a compact handcrafted feature (per-channel colour mean and standard deviation plus local edge density). We deliberately use these reproducible descriptors — not a pretrained network — so the entire pipeline runs deterministically on any machine and provides an honest lower bound. Four scorers are evaluated:",{j:true}),
   bullet("Patch-Stat Memory (NN): a PatchCore-style memory bank of normal patch descriptors; an image scores high if its patches are far (nearest-neighbour distance) from all normal patches. Sensitive to local/structural defects."),
   bullet("Region-Aware Patch Memory: the memory is conditioned on coarse spatial regions, so a patch is compared only to normal patches from the same location — adding weak global/positional awareness for logical cues."),
   bullet("Composition Histogram (BoVW): patches are quantised into visual words (k-means); the image-level word histogram is scored by Mahalanobis distance to the normal distribution. Directly targets logical anomalies via global composition."),
   bullet("Global Image-Stat Detector: a single global descriptor scored by normalised distance to the normal mean — a fast image-level baseline."),
   P("Fusion: each scorer is z-normalised using validation/good scores only, then combined. We report mean, max, and rank-average fusion. All thresholds and normalisation statistics are derived from validation data; no test labels are used for any tuning.",{j:true}),

   H1("4. Results"),
   P("Table 2 reports image-level AUROC (threshold-free) and F1 at a fixed validation-derived operating point (the 90th percentile of validation/good scores). Logical and structural anomalies are scored separately, as the benchmark requires.",{j:true}),
   resultsTable,
   cap("Table 2. Image-level AUROC and F1 by method, averaged across the five categories. Best overall in bold. Fusion of complementary scorers outperforms any single model."),
   P("Three findings stand out. First, fusion helps: combining a local memory scorer with a global composition scorer beats either alone, confirming the two-branch intuition behind GCAD [1] and recent SOTA. Second, the Region-Aware memory achieves the best structural AUROC (0.81), while the Composition Histogram is comparatively stronger on logical cues — the two are complementary. Third, absolute scores (~0.74 overall) are modest because the handcrafted descriptors carry little semantic information; this is expected and motivates the upgrade path below.",{j:true}),
   img(path.join(PR,'06_method_results','Qualitative','qualitative_success_cases.png'),420,308,"Qualitative success cases"),
   cap("Figure 2. Qualitative cases (image · ground-truth mask · decision). The detector correctly flags many anomalies but struggles where colour/edge statistics resemble normal images."),

   H1("5. Discussion, Limitations and Upgrade Path"),
   P("This report is deliberately transparent about scope. The detectors use handcrafted patch statistics, not pretrained backbones, so method names describe the actual computation (e.g. 'Patch-Stat Memory', not 'PatchCore'). The single most impactful improvement is to replace the descriptors with frozen DINOv2 patch tokens [4] while keeping the identical two-branch + fusion architecture; on this benchmark, foundation-model features are the dominant driver of accuracy and are expected to lift results substantially toward GCAD/EfficientAD territory (0.83–0.90) [1,3]. Component-segmentation methods such as CSAD [2] and SALAD [5] reach 0.95–0.96 by explicitly modelling object parts. Other limitations: results are single-seed, and we report image-level AUROC only; the official LOCO localisation metric (sPRO/AUPRO) and multi-seed confidence intervals are planned next.",{j:true}),
   P("Honest positioning vs. the state of the art: our goal is a lightweight, fully reproducible, well-audited baseline with clear failure analysis and an interactive dashboard — not to beat component-segmentation SOTA. The reproducibility package (read-only raw policy, hashing-based leakage detection, letterbox metadata, environment capture) is itself a contribution that many published pipelines lack.",{j:true}),

   H1("6. Reproducibility"),
   P("Fixed seeds (Python/NumPy/Torch); deterministic preprocessing with saved per-image resize metadata; MD5 + average-hash leakage audit across splits; environment and dependency freeze; per-method JSON configs; and a single manifest/zip export. The interactive dashboard (dashboard.html) presents the EDA, leaderboard, and per-image explainability used in this report and opens in any browser with no installation.",{j:true}),

   H1("References"),
   ref(1,"Bergmann, Batzner, Fauser, Sattlegger, Steger. Beyond Dents and Scratches: Logical Constraints in Unsupervised Anomaly Detection and Localization (MVTec LOCO AD; GCAD). IJCV, 2022."),
   ref(2,"Hsieh et al. CSAD: Unsupervised Component Segmentation for Logical Anomaly Detection. BMVC, 2024. (95.3% AUROC)"),
   ref(3,"Batzner et al. EfficientAD: Accurate Visual Anomaly Detection at Millisecond-Level Latencies. WACV, 2024."),
   ref(4,"Damm et al. AnomalyDINO: Boosting Patch-based Few-shot Anomaly Detection with DINOv2. WACV, 2025."),
   ref(5,"Fučka et al. SALAD: Semantics-Aware Logical Anomaly Detection. ICCV, 2025. (96.1% AUROC)"),
  ]
 }]
});
Packer.toBuffer(doc).then(b=>{fs.writeFileSync(path.join(ROOT,'07_paper_draft','Project_A_LOCO_Report.docx'),b);console.log("wrote Project_A_LOCO_Report.docx",b.length,"bytes");});
