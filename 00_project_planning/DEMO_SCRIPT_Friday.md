# Friday Presentation — Demo Script & Q&A Prep
**Project A: LOCO Anomaly Inspector** (MVTec LOCO logical & structural anomaly detection)

> Goal: a confident ~2-minute live demo of the dashboard + a 1-minute framing, and ready answers to the hard questions. Total speaking time ~4–5 min.

---

## 0. One-sentence pitch (memorize this)
> "We built an interactive, fully-reproducible system that detects **both** local defects and **logical** rule-violations on industrial products, trained only on good images — and it **explains every decision** instead of just giving a score."

---

## 1. Framing (≈60 sec, before opening the dashboard)
1. **The problem.** "Factories need to catch defects automatically, but real defects are rare and hard to label — so we learn what *normal* looks like and flag anything different."
2. **The twist.** "MVTec LOCO is special because it has two kinds of defect: **structural** (a scratch or dent — locally visible) and **logical** (a missing fruit, an extra pushpin — every part looks fine, but the *composition* is wrong). Logical anomalies are the hard part."
3. **What we deliver.** "An offline dashboard, four complementary detectors with a fusion stage, decision-relevant EDA, and a leakage-audited reproducible pipeline."

---

## 2. Live dashboard demo (≈2 min)
Open `09_dashboard/dashboard.html` (double-click). Drive it tab by tab:

| Tab | What to say (≈20 sec each) |
|---|---|
| **Overview** | "Five product categories, 3,651 images, trained only on defect-free samples. Our best model — a fusion of detectors — reaches 0.74 overall AUROC." |
| **EDA** | "We kept only the analysis that *informs the model*: mask overlays, the normal mean/variance, and this **spatial anomaly heatmap** — which is exactly why we built a *region-aware* detector." |
| **Leaderboard** | "Four detectors. The region-aware memory wins on **structural**; the composition histogram is stronger on **logical**. Because they're complementary, **fusing them beats any single one** — that's the two-branch idea behind the state of the art." |
| **Explainability** | "This is the part judges remember: for any image we show the original, the ground-truth defect region, and the model's decision — score vs. threshold, pass ✓ or fail ✗. It's an *inspectable* decision, not a black box." |
| **Per-category** | "Drill-down per product. Note we report logical and structural **separately**, as the benchmark requires — and we're honest about where it struggles, e.g. splicing connectors." |

**Close the demo:** "Everything you saw is in a single offline HTML file — no install, no internet."

---

## 3. The honesty slide / the differentiator (≈45 sec)
Say this *before* anyone asks — it turns your biggest caveat into your strongest point:
> "We want to be upfront: these numbers come from **reproducible handcrafted features, not a pretrained deep network**, so we named each method for what it actually computes. That's a deliberate choice for transparency — and the architecture is built so that switching to **DINOv2** features is a one-line change that we expect to push results into the 0.85–0.90 range, near GCAD/EfficientAD. Our contribution is **rigor, reproducibility, and explainability**, not chasing a leaderboard number."

Why this wins: most student projects quietly overstate their models. Naming the gap *first* signals you understand the field and your own work better than the competition.

---

## 4. Anticipated faculty questions — and your answers

**Q: "Is this really PatchCore / DINOv2?"**
> "No — and we say so explicitly. These are honest handcrafted baselines named for what they compute. The DINOv2 upgrade is a documented next step that plugs into the same pipeline."

**Q: "Why is the accuracy only ~0.74? State of the art is 0.95+."**
> "Because we used lightweight handcrafted features for full reproducibility on any machine. The 0.95 methods (CSAD, SALAD) use foundation-model component segmentation and heavy training. With DINOv2 features in the same architecture we'd expect ~0.85–0.90. We chose to ship something transparent and correct over something we couldn't fully audit."

**Q: "What's a logical anomaly again, concretely?"**
> "A breakfast box where every item is fine individually, but one fruit is missing — locally normal, globally wrong. That's why we need a *composition* detector, not just a local one."

**Q: "How do you avoid cheating / data leakage?"**
> "We fit only on good training images, set the threshold on a separate validation-good split, and never touch test labels for tuning. We also hash every image to detect duplicates across splits — none were found."

**Q: "What would you do next?"**
> "Three things: swap in DINOv2 features, add the official localization metric (sPRO), and run multiple seeds for confidence intervals."

**Q: "How is the dashboard built / can it run anywhere?"**
> "It's a self-contained HTML page with all images and results embedded — it opens offline in any browser, no server or install."

---

## 5. Pre-demo checklist (do this Thursday night)
- [ ] Double-click `dashboard.html` → confirms it opens in your browser, all tabs work, images show.
- [ ] Open `Project_A_LOCO_Report_Product.docx` → confirm it looks right; **Save As → PDF** for a clean copy.
- [ ] Have the report PDF open in a second tab as backup.
- [ ] Know your one-sentence pitch (Section 0) cold.
- [ ] If presenting on a different machine: copy the whole project folder; the dashboard + report need no data or internet.
- [ ] Have the slide deck open in presenter view.

---

## 6. If something breaks
- Dashboard won't open → right-click `dashboard.html` → Open with → Chrome/Edge.
- Images missing → you're viewing a cached/old copy; re-open the file from `09_dashboard/`.
- Projector resolution issues → zoom the browser (Ctrl + / Ctrl -).
