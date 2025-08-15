
# FPL Analytics — Advanced (with scrapers + nightly CI)

This bundle includes:
- Real **Understat** and **FBref** xG/xA scrapers (Phase 2)
- Full pipeline Phases 1–3
- Streamlit app (Picks, Captaincy, Fixtures, Team Planner + chips, Exports)
- GitHub Actions **nightly refresh** workflow (builds projections, uploads artifacts)

## Quickstart (local)
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

python pipeline/fetch_fpl_data.py all
python pipeline/ingest_xgxa.py --season 2024           # provider from configs/config.toml
python pipeline/compute_phase3.py --next_n 5

streamlit run app/app.py
```

## GitHub Actions (nightly)
- Workflow: `.github/workflows/nightly.yml`
- Runs daily at 04:30 UTC (adjust cron as needed) and on manual dispatch.
- Steps: install deps → fetch data → ingest xG/xA → compute projections → upload `data/cache` as artifact.
- Optional: commit `data/cache` back to repo if you provide `GH_PAT` secret and set `PUSH_BACK=true`.

### Required GitHub secrets (optional for push-back)
- `GH_PAT`: a classic token or fine-grained PAT with `repo` scope (to push to the same repo).

### Optional environment variables
- `PUSH_BACK` (bool string): `"true"` to git-commit `data/cache` back to default branch.
