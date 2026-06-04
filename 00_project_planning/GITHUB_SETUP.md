# Push this project to GitHub, then clone on your laptop

## ⚠️ First: delete the stray `.git` folder
A broken/empty `.git/` folder may exist in this project (a tool created it but couldn't finish). **Delete it before doing anything**, then start fresh:
- **Windows (PowerShell), inside the project folder:** `Remove-Item -Recurse -Force .git`
- **Windows (File Explorer):** enable "Hidden items" (View menu), delete the `.git` folder.
- **Mac/Linux:** `rm -rf .git`

## What gets uploaded
`.gitignore` already excludes the big/regenerable stuff, so the repo is ~65 MB (not 519 MB):
- ❌ excluded: `03_cleaned_data/` (452 MB, regenerable), `08_exports/*.zip`, `__pycache__`, the raw `Phase 1/` dataset (it lives outside this folder — never commit it).
- ✅ included: all code/notebooks, configs, small result CSVs, the **dashboard**, the **report (.docx/.pdf)**, and all the `.md` docs.

---

## Option A — GitHub Desktop (easiest, no command line)
1. Install **GitHub Desktop**, sign in.
2. **File → Add local repository →** select this `Project_A_LOCO_AD` folder. (If it says "not a git repository", click **"create a repository"** — it will respect `.gitignore`.)
3. Enter a commit summary (e.g. "Initial commit"), click **Commit to main**.
4. Click **Publish repository** (uncheck "keep private" only if you want it public — see license note below).
5. On your **laptop**: **File → Clone repository →** pick it, or use the command in Option B step 6.

## Option B — Command line
Run inside the project folder (after deleting `.git`):
```bash
git init
git add -A
git commit -m "Initial commit: LOCO anomaly detection (dashboard, report, docs)"
git branch -M main
# create an empty repo on github.com first (no README), copy its URL, then:
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```
On your **laptop**:
```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
```

---

## After cloning on the laptop
- The **dashboard** (`09_dashboard/dashboard.html`) and **report** (`07_paper_draft/*.pdf/.docx`) work immediately — images are embedded; no data needed.
- To **re-run the pipeline**, you must restore the data (it wasn't uploaded):
  1. Download MVTec LOCO AD from https://www.mvtec.com/company/research/datasets/mvtec-loco into a sibling `Phase 1/` folder.
  2. Run `01_notebooks/01_preprocessing_reproducibility.ipynb` to regenerate `03_cleaned_data/`.
- Open `CONTEXT.md` in Claude Code and say "read CONTEXT.md and continue."

## ⚖️ License note
MVTec LOCO AD is licensed for **non-commercial research** and its redistribution is restricted. Keeping the dataset out of the repo (as configured) avoids any license issue. Your **code and results** are yours to share. If you make the repo public, consider adding a `LICENSE` for your own code and a line crediting MVTec for the dataset.
