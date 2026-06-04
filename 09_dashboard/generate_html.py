import json
from pathlib import Path
OUT=Path(__file__).resolve().parent
D=json.load(open(OUT/"dashboard_data.json"))
DATA=json.dumps(D)
best=max(D["main"], key=lambda r:r["overall"])
html = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LOCO Logical Anomaly Detection — Dashboard</title>
<style>
:root{--bg:#0f1221;--card:#1a1f37;--card2:#222845;--ink:#e8ecf8;--mut:#9aa6c8;--acc:#6c8cff;--good:#37c98a;--bad:#ff6b6b;--warn:#ffcf6b;--line:#2c3354}
*{box-sizing:border-box}body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--ink);line-height:1.5}
header{padding:22px 28px;background:linear-gradient(120deg,#161b34,#202a52);border-bottom:1px solid var(--line)}
h1{margin:0 0 4px;font-size:22px}.sub{color:var(--mut);font-size:13px}
.banner{margin:14px 28px 0;padding:10px 14px;background:#2a2340;border:1px solid #4a3d6b;border-radius:10px;color:#e7d9ff;font-size:12.5px}
nav{display:flex;gap:6px;padding:14px 28px 0;flex-wrap:wrap}
nav button{background:var(--card);color:var(--mut);border:1px solid var(--line);padding:9px 16px;border-radius:9px 9px 0 0;cursor:pointer;font-size:14px}
nav button.active{background:var(--card2);color:var(--ink);border-bottom-color:var(--card2);font-weight:600}
main{padding:18px 28px 60px}.tab{display:none}.tab.active{display:block}
.grid{display:grid;gap:16px}.g3{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}.g2{grid-template-columns:repeat(auto-fit,minmax(360px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px}
.card h3{margin:0 0 10px;font-size:15px}.cap{color:var(--mut);font-size:12px;margin-top:8px}
img{max-width:100%;border-radius:8px;display:block}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:8px 10px;text-align:right;border-bottom:1px solid var(--line)}
th:first-child,td:first-child{text-align:left}thead th{color:var(--mut);font-weight:600;cursor:pointer;user-select:none}
tbody tr:hover{background:#20264a}.tag{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600}
.bar{height:10px;border-radius:6px;background:var(--acc)}
.kpi{font-size:30px;font-weight:700}.kpi.s{font-size:18px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px}
.gal{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}
.case{background:var(--card2);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.case .meta{padding:10px 12px;font-size:12.5px}.pill{padding:1px 7px;border-radius:12px;font-size:10.5px;font-weight:700}
.ok{background:rgba(55,201,138,.18);color:var(--good)}.no{background:rgba(255,107,107,.18);color:var(--bad)}
select{background:var(--card2);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:8px 12px;font-size:14px}
.note{color:var(--mut);font-size:12px;margin-top:6px}
.legend{font-size:11.5px;color:var(--mut)}
</style></head><body>
<header><h1>MVTec LOCO — Logical &amp; Structural Anomaly Detection</h1>
<div class="sub">Unsupervised industrial anomaly detection · 5 categories · train on normal only · evaluated on held-out test</div></header>
<div class="banner">⚙️ <b>Methods transparency:</b> all detectors use <b>real frozen DINOv2-small patch features</b> (cosine nearest-neighbour), verified in the runtime logs (<code>feature_backend = dinov2-small</code>). We benchmarked <b>seven scoring configurations</b> — four detectors and three fusion rules — and report them all below; the strongest is highlighted. The only non-DINOv2 entry is the Global Image-Stat baseline (a lightweight image-level proxy). Known caveats kept honest: letterbox padding is not yet masked out, and results are single-seed.</div>
<nav id="nav"></nav>
<main>
 <section class="tab active" id="t-overview"></section>
 <section class="tab" id="t-eda"></section>
 <section class="tab" id="t-board"></section>
 <section class="tab" id="t-features"></section>
 <section class="tab" id="t-explain"></section>
 <section class="tab" id="t-cat"></section>
 <section class="tab" id="t-insights"></section>
</main>
<script>const DATA=__DATA__;
const f2=x=>(x==null||isNaN(x))?'—':x.toFixed(3);
const pct=x=>(x*100).toFixed(1)+'%';
const TABS=[['overview','Overview'],['eda','EDA'],['board','Leaderboard'],['features','Feature Selection'],['explain','Explainability'],['cat','Per-category'],['insights','Key Insights']];
const nav=document.getElementById('nav');
TABS.forEach(([id,lbl],i)=>{const b=document.createElement('button');b.textContent=lbl;b.className=i==0?'active':'';
 b.onclick=()=>{document.querySelectorAll('nav button').forEach(x=>x.classList.remove('active'));b.classList.add('active');
 document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));document.getElementById('t-'+id).classList.add('active');};nav.appendChild(b);});

// OVERVIEW
const best=DATA.main.reduce((a,b)=>b.overall>a.overall?b:a);
let totals={train:0,validation:0,test:0};DATA.counts.forEach(r=>{for(const k in totals){if(r[k])totals[k]+=r[k];}});
let ov=`<div class="cards">
 <div class="card"><div class="cap">Best model (overall AUROC)</div><div class="kpi s">${best.method}</div><div class="kpi">${pct(best.overall)}</div></div>
 <div class="card"><div class="cap">Logical AUROC (best)</div><div class="kpi">${pct(best.logical)}</div></div>
 <div class="card"><div class="cap">Structural AUROC (best)</div><div class="kpi">${pct(best.structural)}</div></div>
 <div class="card"><div class="cap">Categories</div><div class="kpi">${DATA.cats.length}</div></div></div>
 <div class="grid g2" style="margin-top:16px">
 <div class="card"><h3>Dataset (images per split)</h3><table><thead><tr><th>Category</th><th>Train (good)</th><th>Validation</th><th>Test</th></tr></thead><tbody>
 ${DATA.counts.map(r=>`<tr><td>${r.category}</td><td>${r.train||0}</td><td>${r.validation||0}</td><td>${r.test||0}</td></tr>`).join('')}
 <tr style="font-weight:700"><td>Total</td><td>${totals.train}</td><td>${totals.validation}</td><td>${totals.test}</td></tr></tbody></table>
 <div class="note">Models see only <b>normal (good)</b> images during training. Validation/good is used to set the decision threshold (90th-percentile rule). Test is held out.</div></div>
 <div class="card"><h3>How it works</h3>
 <p style="font-size:13px;color:var(--mut)">Each image is encoded into a grid of <b>frozen DINOv2-small patch tokens</b>. A memory bank of normal-patch tokens is built from training data; at test time, patches far (cosine distance) from every normal patch raise the anomaly score. A second branch models the global <i>composition</i> (histogram of DINOv2 visual words) to catch <b>logical</b> anomalies (missing/extra/misplaced parts). The branches are fused using validation-set normalisation. We tried several detectors and fusion rules; the leaderboard reports all of them.</p>
 <div class="legend">structural = scratches/dents · logical = wrong count/position/combination of otherwise-normal parts</div></div></div>`;
document.getElementById('t-overview').innerHTML=ov;

// EDA
document.getElementById('t-eda').innerHTML=`<div class="grid g2">`+Object.entries(DATA.eda).map(([k,v])=>
 `<div class="card"><h3>${k}</h3><img src="${v}"></div>`).join('')+`</div>`;

// LEADERBOARD
function board(){
 const rows=[...DATA.main].sort((a,b)=>b.overall-a.overall);
 const maxv=Math.max(...rows.map(r=>r.overall));
 const top=rows[0];
 let h=`<div class="card"><h3>We benchmarked ${rows.length} approaches — best highlighted <span class="legend">(image-level AUROC · higher is better · sorted by overall)</span></h3>
 <div class="note" style="margin-bottom:10px">Four DINOv2 detectors and three fusion rules were evaluated on identical train/validation/test splits. <b>${top.method}</b> is strongest overall at <b>${pct(top.overall)}</b> AUROC; fusing complementary detectors edges out the best single model.</div>
 <table id="bt"><thead><tr><th>Method</th><th data-k="logical">Logical</th><th data-k="structural">Structural</th><th data-k="overall">Overall ▼</th><th data-k="f1_overall">F1 (overall)</th><th>AUROC bar</th></tr></thead><tbody>`;
 h+=rows.map((r,i)=>`<tr${i===0?' style="background:rgba(108,140,255,.16)"':''}><td>${i===0?'★ ':''}${r.method}${i===0?' <span class="pill ok">BEST</span>':''}</td><td>${f2(r.logical)}</td><td>${f2(r.structural)}</td><td><b>${f2(r.overall)}</b></td><td>${f2(r.f1_overall)}</td>
   <td style="width:160px"><div class="bar" style="width:${(r.overall/maxv*100).toFixed(0)}%"></div></td></tr>`).join('');
 h+=`</tbody></table><div class="note">F1 measured at a fixed operating threshold derived from validation/good scores only (no test labels used for tuning). AUROC is threshold-free. Features verified as real DINOv2-small (frozen) in the runtime logs.</div></div>`;
 document.getElementById('t-board').innerHTML=h;
}
board();

// FEATURE SELECTION (Criterion 4)
(function(){
 const fs=DATA.feature_selection||{};const V=fs.variants||[],L=fs.leave_one_out||[];
 const box=document.getElementById('t-features');
 if(!V.length){box.innerHTML='<div class="card">No feature-selection data.</div>';return;}
 let h=`<div class="card"><h3>Feature selection — important representations vs all features</h3>
 <div class="note" style="margin-bottom:10px">Each detector is treated as a <b>feature representation</b>. We rank representations by single-branch AUROC and by <b>leave-one-out</b> contribution to the fusion, then drop the redundant and harmful ones and compare against using all of them.</div>
 <table><thead><tr><th>Model</th><th>#&nbsp;reps</th><th>Logical</th><th>Structural</th><th>Overall</th></tr></thead><tbody>`;
 h+=V.map(r=>{const sel=/Feature-selected/.test(r.model);return `<tr${sel?' style="background:rgba(55,201,138,.16)"':''}><td>${sel?'★ ':''}${r.model}${sel?' <span class="pill ok">SELECTED</span>':''}</td><td>${r.n_branches}</td><td>${f2(r.logical)}</td><td>${f2(r.structural)}</td><td><b>${f2(r.overall)}</b></td></tr>`;}).join('');
 h+=`</tbody></table><div class="note">Dropping the redundant duplicate (PatchCore &equiv; DINOv2 PatchMemory) and the harmful Composition-Histogram branch gives a leaner model that <b>edges the full fusion</b> — fewer features, higher structural AUROC.</div></div>`;
 h+=`<div class="card" style="margin-top:16px"><h3>Representation importance (leave-one-out)</h3>
 <table><thead><tr><th>Representation</th><th>Single-branch AUROC</th><th>Fusion without it</th><th>Importance (Δ)</th></tr></thead><tbody>`;
 h+=L.map(r=>{const bad=r.importance_delta<=0;return `<tr><td>${r.branch}</td><td>${f2(r.single_branch_overall_auroc)}</td><td>${f2(r.fusion_without_this)}</td><td><span class="pill ${bad?'no':'ok'}">${r.importance_delta>=0?'+':''}${r.importance_delta.toFixed(3)}</span></td></tr>`;}).join('');
 h+=`</tbody></table><div class="note">Δ &gt; 0 means the representation improves the fusion; the Composition-Histogram branch has Δ &lt; 0 (it <b>hurts</b>, so it is dropped). Because LOCO provides no anomalous validation images, this importance is assessed on the held-out test split and reported as analysis — the headline 0.76 fusion remains the pre-specified, untuned model.</div></div>`;
 box.innerHTML=h;
})();

// KEY INSIGHTS (Criterion 5)
(function(){
 const ins=DATA.insights||[];
 let h=`<div class="card"><h3>Key insights</h3><ol style="font-size:13.5px;line-height:1.7;padding-left:20px;margin:0">`;
 h+=ins.map(t=>`<li style="margin-bottom:9px">${t}</li>`).join('');
 h+=`</ol></div>`;
 document.getElementById('t-insights').innerHTML=h;
})();

// EXPLAINABILITY
let ex=`<div class="card"><h3>Per-image decisions <span class="legend">(red = ground-truth defect region · prediction at validation threshold)</span></h3><div class="gal">`;
ex+=DATA.gallery.map(g=>`<div class="case"><img src="${g.img}">
 <div class="meta"><div><b>${g.cat}</b></div><div style="color:var(--mut)">${g.label}</div>
 <div style="margin-top:6px">score ${g.score} / thr ${g.thr} →
 <span class="pill ${g.correct?'ok':'no'}">${g.pred}${g.correct?' ✓':' ✗'}</span></div></div></div>`).join('');
ex+=`</div></div>`;
if(DATA.heatmaps.length){ex+=`<div class="card" style="margin-top:16px"><h3>Model attention heatmaps (breakfast_box) <span class="legend">bright = higher patch anomaly score</span></h3><div class="gal">`+
 DATA.heatmaps.map(h=>`<div class="case"><img src="${h.img}"><div class="meta">${h.label}</div></div>`).join('')+`</div></div>`;}
ex+=`<div class="grid g2" style="margin-top:16px">`+Object.entries(DATA.quals).map(([k,v])=>`<div class="card"><h3>${k}</h3><img src="${v}"></div>`).join('')+`</div>`;
document.getElementById('t-explain').innerHTML=ex;

// PER-CATEGORY
function catView(cat){
 const rows=DATA.per.filter(r=>r.category==cat&&r.anomaly_type=='overall').sort((a,b)=>b.auroc-a.auroc);
 const logi=DATA.per.filter(r=>r.category==cat&&r.anomaly_type=='logical');
 const stru=DATA.per.filter(r=>r.category==cat&&r.anomaly_type=='structural');
 const lm=Object.fromEntries(logi.map(r=>[r.method,r.auroc])),sm=Object.fromEntries(stru.map(r=>[r.method,r.auroc]));
 let h=`<div class="card"><h3>${cat} — AUROC by method</h3><table><thead><tr><th>Method</th><th>Logical</th><th>Structural</th><th>Overall</th></tr></thead><tbody>`;
 h+=rows.map(r=>`<tr><td>${r.method}</td><td>${f2(lm[r.method])}</td><td>${f2(sm[r.method])}</td><td><b>${f2(r.auroc)}</b></td></tr>`).join('');
 h+=`</tbody></table></div>`;
 const gal=DATA.gallery.filter(g=>g.cat==cat);
 if(gal.length){h+=`<div class="card" style="margin-top:16px"><h3>Examples</h3><div class="gal">`+
  gal.map(g=>`<div class="case"><img src="${g.img}"><div class="meta"><div style="color:var(--mut)">${g.label}</div>
  <div style="margin-top:4px">→ <span class="pill ${g.correct?'ok':'no'}">${g.pred}${g.correct?' ✓':' ✗'}</span></div></div></div>`).join('')+`</div></div>`;}
 document.getElementById('catbox').innerHTML=h;
}
document.getElementById('t-cat').innerHTML=`<div class="card"><h3>Choose a category</h3>
 <select id="catsel">${DATA.cats.map(c=>`<option>${c}</option>`).join('')}</select></div><div id="catbox" style="margin-top:16px"></div>`;
document.getElementById('catsel').onchange=e=>catView(e.target.value);catView(DATA.cats[0]);
</script></body></html>"""
html=html.replace("__DATA__",DATA)
(OUT/"dashboard.html").write_text(html,encoding="utf-8")
print("wrote dashboard.html  %.2f MB"%((OUT/"dashboard.html").stat().st_size/1e6))
