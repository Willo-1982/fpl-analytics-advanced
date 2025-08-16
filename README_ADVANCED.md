# Advanced Update Pack — Minutes Model + Opponent Strength

This pack upgrades the projection engine to include:
- Heuristic **expected minutes model** (availability, form, popularity, position)
- **Opponent strength adjustment** using team attack/defence ratings and fixture FDR ease
- Clean-sheet probability proxy via logistic on (team_def - opp_att) and ease
- Still writes **Next 1 / 3 / 5** projections and captaincy

## Apply
1) Unzip into your repo root (replace `pipeline/compute_phase3.py`).
2) Commit & push:
```
git add pipeline/compute_phase3.py
git commit -m "EP engine: minutes model + opponent-strength adjustment"
git push
```
3) Run workflow (Actions → Nightly Refresh → Run workflow)
4) Local run:
```
git pull
.\.venv\Scripts\Activate.ps1
python pipeline\compute_phase3.py
streamlit run app\app.py
```

## Notes
- Uses FPL team strengths if available; falls back to neutral values otherwise.
- Minutes model is heuristic and safe; you can later replace with a learned model.
