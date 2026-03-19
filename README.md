# Trust Control Center (1-Trillion-AI-Problem)

Lightweight Django app to assess and improve dataset trustworthiness for AI/ML pipelines. It provides data quality validation, governance primitives, and a multi-dimensional trust scoring engine.

## Summary

- Web dashboard to upload datasets, run validations and compute trust scores.
- Tools to define governance metrics and reconcile cross-system inconsistencies.
- Management commands and small utilities to run demos, export governance, and calculate trust in batch.

## Quick Install

```bash
git clone https://github.com/somesh-ghaturle/1-Trillion-AI-Problem.git
cd 1-Trillion-AI-Problem
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://localhost:8000/ for the dashboard and http://localhost:8000/admin/ for the Django admin.

## Important files & commands

- `manage.py` — standard Django entrypoint.
- `generate_dashboard_data.py` — local helper to populate demo/dashboard data.
- `core/utils/` — implementation of data quality, governance and trust scoring logic:
  - `data_quality_validator.py`
  - `trust_scoring.py`
  - `data_governance.py`
- Management commands (in `core/management/commands`):
  - `calc_trust.py` — calculate trust scores for sources in batch
  - `validate_data.py` — run data validation for a source or CSV
  - `export_governance.py` — export governance metrics
  - `run_demo.py` — populate demo data and run example flows

Usage examples:

```bash
# Run validation on a CSV (interactive/upload endpoint also available in UI)
python manage.py validate_data --file path/to/data.csv --source "my-source"

# Calculate trust scores for all sources
python manage.py calc_trust

# Populate demo data for the dashboard
python manage.py run_demo

# Generate dashboard/demo data script
python generate_dashboard_data.py
```

## Tests

Run the test suite with:

```bash
python -m pytest -q
```

## Project structure (short)

```
./
├─ trustsite/                # Django project settings
├─ core/                     # Main app (models, views, management commands)
│  └─ utils/                 # data_quality_validator, trust_scoring, data_governance
├─ templates/                # UI templates
├─ manage.py
└─ requirements.txt
```

## Contributing

PRs welcome. For changes to scoring logic or governance rules, include unit tests in `core/tests`.

## Contact

Open an issue in the repository for questions, feature requests or bugs.

---

If you'd like, I can further tailor this README (add screenshots, CI steps, Docker Compose, or expand command docs). Let me know which details you'd like added.
