# Trust Control Center — The $1 Trillion AI Problem

> **When "revenue" means different things in Snowflake, Tableau, and Salesforce, every AI model trained on that data is wrong.**

A Django-based platform that detects, visualizes, and resolves cross-source metric inconsistencies — the root cause of unreliable AI predictions that costs enterprises over **$1 trillion annually**.

Built around the [Open Semantic Interchange (OSI)](https://venturebeat.com/ai/the-usd1-trillion-ai-problem-why-snowflake-tableau-and-blackrock-are-giving) initiative by Snowflake, Salesforce, dbt Labs, BlackRock, and 15+ other companies.

**Live demo:** <https://trust-control-center.onrender.com> (read-only, sample data; free tier, so the first load can take about a minute to wake)

---

<div align="center">
  <img src="dashboard-screenshot.png" alt="Trust Control Center Dashboard" width="100%" />
</div>

---

## The Problem

Enterprise data is fragmented across dozens of systems. The same business metric — "revenue", "customer count", "churn rate" — is defined and calculated differently in each one:

| System | "Total Revenue" Formula | Issue |
| ------ | ---------------------- | ----- |
| Snowflake DWH | `SUM(amount) WHERE status = 'completed'` | Canonical definition |
| Tableau Cloud | `SUM(amount) WHERE status IN ('completed', 'pending')` | Includes pending — overstates by ~12% |
| PostgreSQL | `SUM(charge_amount) WHERE payment_status = 'succeeded'` | Uses net amount (excludes tax) |
| Salesforce CRM | `SUM(Opportunity.Amount) WHERE Stage = 'Closed Won'` | Opportunity-based, not payment-based |

When AI/ML models train on data with these silent inconsistencies, they produce unreliable predictions. Teams make decisions based on conflicting numbers. This is the **$1 Trillion AI Problem**.

---

## How It Works

```mermaid
flowchart LR
    subgraph Sources["Enterprise Data Sources"]
        SF["Snowflake DWH"]
        TB["Tableau Cloud"]
        PG["PostgreSQL"]
        CRM["Salesforce CRM"]
        SP["Stripe Payments"]
    end

    subgraph TCC["Trust Control Center"]
        GOV["Governance Metrics<br/>Canonical Definitions"]
        SEM["Semantic Mappings<br/>Per-Source Definitions"]
        REC["Reconciliation Engine<br/>Cross-Source Comparison"]
        TS["Trust Scoring<br/>6-Dimension Analysis"]
        VAL["Data Validation<br/>Quality Checks"]
    end

    subgraph Output["Outputs"]
        OSI["OSI Export<br/>Vendor-Neutral JSON"]
        DASH["Dashboard<br/>Real-Time Visibility"]
        AI["AI-Ready Data<br/>Trusted Predictions"]
    end

    SF --> SEM
    TB --> SEM
    PG --> SEM
    CRM --> SEM
    SP --> SEM

    GOV --> REC
    SEM --> REC

    SF --> VAL
    PG --> VAL

    VAL --> TS
    REC --> TS

    REC --> DASH
    TS --> DASH
    REC --> OSI
    TS --> AI
```

---

## Architecture

```mermaid
flowchart TB
    subgraph Frontend["Frontend"]
        TMPL["Django Templates<br/>Dark/Light UI, search & filters"]
        CJS["Chart.js<br/>Health trend, distributions"]
    end

    subgraph Backend["Django + DRF (gunicorn)"]
        DV["Views & REST API<br/>token auth, roles, rate limits"]
        RE["Reconciliation Engine<br/>SQL-aware diff (sqlglot)"]
        INS["Insights<br/>anomalies, 7-day outlook"]
        IMP["Importers<br/>dbt YAML, CSV, OSI"]
        EXP["Exports<br/>CSV / Excel / Parquet"]
        MON["/healthz & /metrics"]
    end

    subgraph Async["Background"]
        REDIS["Redis<br/>broker + shared cache"]
        WORKER["Celery worker<br/>reconciliation runs"]
        ALERT["Alerts<br/>webhook (Slack) / email"]
    end

    subgraph Data["Data"]
        DB["PostgreSQL / SQLite"]
    end

    subgraph Ops["Monitoring (opt-in)"]
        PROM["Prometheus"] --> GRAF["Grafana dashboard"]
    end

    TMPL --> DV
    CJS --> TMPL
    DV --> RE
    DV --> INS
    DV --> IMP
    DV --> EXP
    DV --> REDIS
    REDIS --> WORKER
    WORKER --> RE
    WORKER --> ALERT
    RE --> DB
    DV --> DB
    PROM --> MON
```

---

## Data Model

```mermaid
erDiagram
    DataSource ||--o{ ValidationResult : validates
    DataSource ||--o{ TrustScore : scores
    DataSource ||--o{ SemanticDefinition : defines
    DataSource ||--o{ DataLineage : "flows from"
    DataSource ||--o{ DataLineage : "flows to"

    GovernanceMetric ||--o{ SemanticDefinition : "mapped by"
    GovernanceMetric ||--o{ ReconciliationRun : reconciles

    DataSource {
        string name
        string source_type
        string connector
        boolean is_active
    }

    GovernanceMetric {
        string name
        string display_name
        text formula
        string data_type
        string category
        string owner
    }

    SemanticDefinition {
        string local_name
        text local_formula
        text local_description
        boolean is_consistent
        text consistency_notes
    }

    ReconciliationRun {
        string status
        int total_sources
        int consistent_sources
        float consistency_score
        json divergences
        json recommendations
    }

    TrustScore {
        float overall_score
        string trust_level
        float completeness_score
        float accuracy_score
        float consistency_score
        float timeliness_score
        float validity_score
        float uniqueness_score
    }

    ValidationResult {
        float quality_score
        boolean passed
        int total_rules
        int passed_rules
        int failed_rules
    }

    DataLineage {
        string flow_type
        string schedule
        text description
    }
```

---

## Reconciliation Flow

```mermaid
flowchart TD
    START["Run Reconciliation"] --> FETCH["Fetch All Governance Metrics"]
    FETCH --> LOOP["For Each Metric"]

    LOOP --> GET_DEFS["Get Semantic Definitions<br/>from All Sources"]
    GET_DEFS --> CANONICAL["Compare Against<br/>Canonical Formula"]
    GET_DEFS --> PAIRWISE["Pairwise Comparison<br/>Between Sources"]

    CANONICAL --> PARSE{"Parse as SQL<br/>(sqlglot)"}
    PAIRWISE --> PARSE

    PARSE -->|"parses"| STRUCT["Compare Structure<br/>measure expression +<br/>set of WHERE conditions"]
    PARSE -->|"doesn't parse"| SIM["Fallback: Text Similarity<br/>SequenceMatcher, threshold 0.85"]

    STRUCT -->|"identical"| CONSISTENT["Mark Consistent"]
    STRUCT -->|"different"| DIVERGENT["Flag Divergence"]
    SIM -->|"ratio >= 0.85"| CONSISTENT
    SIM -->|"ratio < 0.85"| DIVERGENT

    DIVERGENT --> TYPE{"Divergence Type"}
    TYPE -->|"Measure mismatch"| CRIT["Severity: CRITICAL"]
    TYPE -->|"Naming difference"| MED["Severity: MEDIUM"]
    TYPE -->|"Filter mismatch"| HIGH["Severity: HIGH"]
    TYPE -->|"Column mapping"| MED

    CONSISTENT --> SCORE["Calculate Consistency Score<br/>consistent_sources / total * 100"]
    CRIT --> SCORE
    MED --> SCORE
    HIGH --> SCORE

    SCORE --> SAVE["Save ReconciliationRun<br/>Update SemanticDefinition Flags"]
    SAVE --> RECS["Generate Recommendations"]
```

---

## Trust Scoring Dimensions

```mermaid
flowchart LR
    subgraph Dimensions["6 Trust Dimensions"]
        C["Completeness<br/>Missing values and null fields"]
        A["Accuracy<br/>Value correctness"]
        CO["Consistency<br/>Cross-system matching"]
        T["Timeliness<br/>Data freshness"]
        V["Validity<br/>Business rule compliance"]
        U["Uniqueness<br/>Duplicate detection"]
    end

    subgraph Levels["Trust Levels"]
        VER["Verified 90-100%"]
        HI["High 75-89%"]
        MID["Medium 60-74%"]
        LO["Low 40-59%"]
        UN["Untrusted 0-39%"]
    end

    C --> CALC["Weighted Average"]
    A --> CALC
    CO --> CALC
    T --> CALC
    V --> CALC
    U --> CALC

    CALC --> SCORE["Overall Trust Score"]
    SCORE --> VER
    SCORE --> HI
    SCORE --> MID
    SCORE --> LO
    SCORE --> UN
```

---

## Features

### Cross-Source Metric Reconciliation

- Define canonical governance metrics (the single source of truth)
- Map how each metric is implemented in every data source (semantic definitions)
- Run automated reconciliation to detect formula, naming, filter, and column mapping divergences
- SQL-aware comparison: formulas are parsed with [sqlglot](https://github.com/tobymao/sqlglot), so formatting and condition order don't matter, but real differences are named precisely — e.g. *"Tableau Cloud filter on `status` also includes 'pending'"*. Formulas that aren't valid SQL fall back to text similarity
- Get severity-rated divergences with actionable recommendations

### dbt Semantic Layer Import

- Read metric definitions straight from a dbt project's semantic-layer YAML (`semantic_models` + `metrics`, dbt ≤1.11 and 1.12+ layouts). No warehouse connection or dbt install needed.
- Each dbt metric is rendered as a formula (measures, aggregations, filters; `{{ Dimension('order__status') }}` resolves to the dimension's real SQL) and stored as the mapping for the governance metric with the same name
- Reconciliation then compares dbt against every other source, e.g. *"dbt Semantic Layer filter on `status` also includes 'refunded'"*
- Import from **Semantic Mappings → Import from dbt** (upload YAML) or the command line:

```bash
python manage.py import_dbt path/to/dbt_project            # or --dry-run, --source "Prod dbt"
python manage.py import_dbt examples/dbt_project           # bundled example: 2 matches, 3 divergences, 3 unmatched
```

Ratio metrics are compared as `numerator / denominator`; derived, cumulative and conversion metrics are imported with a note about what is compared.

### Trust Scoring (6 Dimensions)

- **Completeness** — Missing values, null fields, required columns
- **Accuracy** — Outlier detection, value range validation
- **Consistency** — Cross-system matching, format standardization
- **Timeliness** — Data freshness, update frequency
- **Validity** — Business rule compliance, referential integrity
- **Uniqueness** — Duplicate row detection, key uniqueness

### Data Lineage Tracking

- Map data flows between enterprise systems (ETL, replication, streaming, API sync)
- Track which metrics flow through which pipelines
- Identify where inconsistencies are introduced in the data supply chain

### OSI-Compatible Export/Import

- Export your entire semantic model as vendor-neutral JSON
- Import OSI specs from other teams or tools
- Based on the Open Semantic Interchange standard by Snowflake, Salesforce, dbt Labs, BlackRock, and 15+ companies

### Data Quality Validation

- Upload CSV files for automated quality checks
- Null detection, type validation, range checks, uniqueness analysis
- Historical validation tracking per data source

### Anomaly Detection & 7-Day Outlook

- Flags when a source's latest trust or quality score drops well below **its own** recent history (2σ, at least 5 points)
- Projects each daily health series 7 days ahead from its least-squares trend
- On the dashboard and at `/api/v1/insights/`

### Alerts

- Webhook (JSON with a Slack-compatible `text` field) and/or email when a validation fails, a score drop is detected, or a reconciliation finds critical divergences
- Sent after the database commit by the background worker; delivery failures are logged and never break the action that caused them

### Search, Filters, Export & Bulk Import

- Search and filters on every list page (bookmarkable URLs) and `?search=` / `?ordering=` / field filters on every API endpoint
- Download trust scores, validations, metrics, mappings and reconciliation findings as **CSV, Excel, or Parquet** (`/export/<dataset>.<format>`)
- Bulk-import semantic mappings from CSV; the columns match the export, so you can export, edit in a spreadsheet, and upload back

### Monitoring

- `/healthz` (database + broker) for load balancers and uptime checks
- `/metrics` in Prometheus format: request rate, latency, DB queries, plus trust, quality, consistency, and open divergences. Requires a bearer token
- Optional Prometheus + Grafana stack with a provisioned dashboard (see [Docker](#docker))

### REST API

- Full CRUD API for all entities via Django REST Framework; Swagger UI at `/api/docs/`
- Token auth, role-based write permissions, per-client rate limits (120/min anonymous, 600/min logged in)
- Browsable API at `/api/v1/`; OSI export/import via API

---

## Pages

| Page | URL | Description |
| ---- | --- | ----------- |
| Dashboard | `/` | Trust and quality scores, anomalies, 7-day outlook, 30-day health trend, reconciliation status |
| Data Sources | `/sources/` | All monitored systems with trust scores and validation history |
| Governance | `/governance/` | Define canonical metrics (the single source of truth) |
| Semantic Mappings | `/semantic/` | Map how metrics are implemented per source system |
| Reconciliation | `/reconciliation/` | Run cross-source comparison, view divergences |
| Exports | `/export/<dataset>.<csv\|xlsx\|parquet>` | trust-scores, validations, governance-metrics, semantic-definitions, reconciliation |
| Data Lineage | `/lineage/` | Track data flows between systems |
| OSI Export | `/osi/` | Export/import semantic model as vendor-neutral JSON |
| API Browser | `/api/v1/` | Interactive REST API explorer |
| API Docs | `/api/docs/` | Swagger UI generated from the OpenAPI schema (`/api/schema/`) |
| Admin Panel | `/admin/` | Django admin for direct data management |

---

## Quick Start

```bash
# Clone and setup
git clone https://github.com/somesh-ghaturle/1-Trillion-AI-Problem.git
cd 1-Trillion-AI-Problem
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Initialize database
python manage.py migrate

# Load sample data (8 sources, 8 metrics, 23 semantic definitions, reconciliation runs)
python manage.py seed_data

# Create a login (needed to create, upload, or run anything)
python manage.py createsuperuser

# Start the server
python manage.py runserver
```

### Access Model

Every page and `GET` API endpoint is public and read-only. Writing (creating metrics, uploading CSVs, running reconciliation, importing OSI specs, API writes) depends on role:

| Role | Who | Can write? |
| ---- | --- | ---------- |
| **Admin** | Superusers | Everything, plus the admin panel |
| **Editor** | Users in the `Editor` group (created automatically on `migrate`) | All app data |
| **Viewer** | Any other logged-in user, or anonymous | No — read-only (403 on writes) |

Make someone an editor in **Admin → Users → Groups**, or:

```bash
python manage.py shell -c "from django.contrib.auth.models import User, Group; User.objects.get(username='alice').groups.add(Group.objects.get(name='Editor'))"
```

Log in via **Log in** in the sidebar (or `/api/auth/login/`). For scripts, get an API token (rate-limited to 10/min):

```bash
curl -X POST localhost:8000/api/auth/token/ -d username=alice -d password=...
# {"token": "9944b0..."}
curl -H "Authorization: Token 9944b0..." localhost:8000/api/v1/sources/ -d name=Redshift -d source_type=database
```

Session auth (the browsable API) also works. HTTP Basic auth is not accepted. Tokens can be viewed and revoked in **Admin → Auth Token → Tokens**.

**Login lockout** ([django-axes](https://github.com/jazzband/django-axes)): 5 failed logins for the same username from the same IP lock that pair out for 15 minutes. This covers the login page, the admin and the token endpoint, and a successful login resets the count. Locking by username + IP means nobody can lock a user out from everywhere. Unlock early with **Admin → Axes → Access attempts** or `python manage.py axes_reset`.

Rate limits and lockouts key on the client IP. Behind one TLS proxy (Render, Heroku, Fly) the default is right; set `DJANGO_NUM_PROXIES` if you have a different number of proxies (docker-compose uses `0`).

Open <http://localhost:8000/> to see the dashboard populated with realistic enterprise data demonstrating cross-source inconsistencies.

### Sample Data

The `seed_data` command creates a realistic enterprise scenario:

- **8 data sources**: Snowflake DWH, Tableau Cloud, PostgreSQL Production, Salesforce CRM, Stripe Payments, HubSpot Marketing, Google BigQuery, CSV Uploads
- **8 governance metrics**: Total Revenue, MRR, Active Customer Count, Churn Rate, CAC, NPS, Average Deal Size, Pipeline Uptime
- **23 semantic definitions**: Showing how each metric is calculated differently in each system — with intentional inconsistencies that mirror real-world enterprise problems
- **9 data lineage flows**: ETL pipelines, streaming, API syncs, and manual uploads between systems
- **40 validation results**: Historical quality checks across all sources
- **24 trust scores**: 6-dimension trust analysis for all sources
- **8 reconciliation runs**: Automated cross-source comparison results

To reset and re-seed:

```bash
python manage.py seed_data --flush
```

---

## Deploy a live demo

A demo is already running at <https://trust-control-center.onrender.com>. To deploy your own copy:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/somesh-ghaturle/1-Trillion-AI-Problem)

One click creates a free Render web service from [`render.yaml`](render.yaml): Docker build, sample data, `/healthz` health check, generated secret key and admin password (shown under the service's **Environment** tab). The free plan sleeps after 15 minutes idle, so the first visit after a quiet spell takes about a minute to wake.

## Docker

```bash
# App + PostgreSQL + Redis + Celery worker
DJANGO_SUPERUSER_USERNAME=admin DJANGO_SUPERUSER_PASSWORD=change-me docker compose up --build

# Optional: add Prometheus (localhost:9090) and Grafana (localhost:3000, admin / $GRAFANA_PASSWORD)
METRICS_TOKEN=$(openssl rand -hex 24) GRAFANA_PASSWORD=change-me \
  docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up --build
```

`docker compose` runs **PostgreSQL 17**, **Redis**, the web app (gunicorn) and a **Celery worker**. Without Docker, local `runserver` uses SQLite and runs background tasks inline, so nothing else needs to be installed. Sample data is seeded only when the database is empty.

| Variable | Purpose |
| -------- | ------- |
| `DATABASE_URL` | `postgres://user:pass@host:5432/dbname` (add `?sslmode=require` for managed Postgres). Unset = SQLite |
| `REDIS_URL` | Celery broker and shared cache. Unset = tasks run inline, per-process cache |
| `DJANGO_SECRET_KEY` | Required for any real deployment |
| `DJANGO_SUPERUSER_USERNAME` / `DJANGO_SUPERUSER_PASSWORD` | Create an admin login on startup |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_NUM_PROXIES` | Host names; number of reverse proxies in front (for client IPs in rate limits and lockouts) |
| `ALERT_WEBHOOK_URL`, `ALERT_EMAILS` | Alert destinations (Slack-compatible webhook; comma-separated emails) |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | SMTP for email alerts. Unset = printed to the console |
| `API_RATE_ANON`, `API_RATE_USER` | API rate limits (default `120/min`, `600/min`) |
| `METRICS_TOKEN` | Bearer token for `/metrics`. Unset = endpoint disabled |
| `POSTGRES_PASSWORD`, `GRAFANA_PASSWORD` | Compose `db` password (default `trust`); Grafana admin password (required for monitoring) |

---

## API Endpoints

| Endpoint | Methods | Description |
| -------- | ------- | ----------- |
| `/healthz` | GET | Database + broker health (200 / 503) |
| `/metrics` | GET | Prometheus metrics (`Authorization: Bearer $METRICS_TOKEN`) |
| `/api/` | GET | API health check |
| `/api/auth/token/` | POST | Exchange username/password for an API token |
| `/api/schema/` | GET | OpenAPI 3 schema (YAML) |
| `/api/docs/` | GET | Swagger UI |
| `/api/v1/sources/` | GET, POST, PUT, DELETE | Data source CRUD |
| `/api/v1/governance-metrics/` | GET, POST, PUT, DELETE | Governance metric CRUD |
| `/api/v1/semantic-definitions/` | GET, POST, PUT, DELETE | Semantic definition CRUD |
| `/api/v1/reconciliations/` | GET | Reconciliation run history |
| `/api/v1/reconciliations/run/` | POST | Trigger reconciliation (202 + task id when a worker is configured) |
| `/api/v1/insights/` | GET | Anomalies and 7-day outlook |
| `/api/v1/lineage/` | GET, POST, PUT, DELETE | Data lineage CRUD |
| `/api/v1/trust-scores/` | GET | Trust score history |
| `/api/v1/validations/` | GET | Validation result history |
| `/api/v1/governance-metrics/osi-export/` | GET | OSI spec export |
| `/api/v1/governance-metrics/osi-import/` | POST | OSI spec import |

Every list endpoint accepts `?search=`, `?ordering=` and field filters (for example `/api/v1/trust-scores/?trust_level=low&ordering=-overall_score`).

---

## Management Commands

```bash
# Populate realistic sample data
python manage.py seed_data

# Reset and re-populate
python manage.py seed_data --flush

# Calculate trust scores for all sources
python manage.py calc_trust

# Run data validation
python manage.py validate_data --file path/to/data.csv --source "my-source"

# Export governance metrics
python manage.py export_governance

# Import metric definitions from a dbt project's semantic layer
python manage.py import_dbt path/to/dbt_project [--source NAME] [--dry-run]
```

---

## Tests

```bash
# Run all tests
python manage.py test core -v 2

# Run specific test modules
python manage.py test core.tests.test_reconciliation -v 2
python manage.py test core.tests.test_api -v 2
python manage.py test core.tests.test_models -v 2
python manage.py test core.tests.test_views -v 2
```

### End-to-end (Docker)

`scripts/e2e.py` exercises the running docker-compose stack over HTTP: every page, CSV export, static files, anonymous-write blocking, login (including behind an HTTPS proxy), login lockout, UI writes, reconciliation runs, and API token auth. CI runs it on every push and PR, then checks that a restart and a full `down`/`up` keep the data without re-seeding.

```bash
DJANGO_SUPERUSER_USERNAME=admin DJANGO_SUPERUSER_PASSWORD=secret docker compose up --build -d
E2E_PASSWORD=secret python3 scripts/e2e.py
```

Unit test coverage includes:

- Model creation and constraints (unique_together, validators)
- All 14 view functions (GET and POST)
- All REST API endpoints (CRUD operations)
- Reconciliation engine (consistent, divergent, naming, formula detection, structural SQL diff)
- OSI export/import round-trip
- Trust score calculation
- Auth: anonymous reads allowed, anonymous and viewer writes blocked, editor and superuser writes allowed, API tokens, token endpoint throttling, spoofed X-Forwarded-For, login lockout
- Seed command is idempotent

---

## Project Structure

```text
./
├── trustsite/                  # Django project: settings, URLs, Celery app
├── core/                       # Main application
│   ├── models.py               # DataSource, GovernanceMetric, SemanticDefinition, ReconciliationRun, ...
│   ├── views.py / api_views.py # Pages and DRF API
│   ├── tasks.py                # Celery tasks (reconciliation, alert delivery)
│   ├── alerts.py               # Webhook / email alerts from model signals
│   ├── exports.py              # CSV / Excel / Parquet downloads
│   ├── monitoring.py           # /healthz and /metrics
│   ├── utils/
│   │   ├── reconciliation.py   # SQL-aware cross-source comparison
│   │   ├── insights.py         # Anomaly detection and outlook
│   │   ├── dbt_import.py       # dbt Semantic Layer YAML -> mappings
│   │   ├── bulk_import.py      # CSV -> mappings
│   │   ├── osi_export.py       # OSI JSON export/import
│   │   └── trust_scoring.py, data_quality_validator.py
│   ├── management/commands/    # seed_data, import_dbt, calc_trust, validate_data, export_governance
│   └── tests/                  # Unit and integration tests
├── templates/, static/         # Dark/light UI
├── monitoring/                 # Prometheus config, Grafana datasource + dashboard
├── examples/dbt_project/       # Sample dbt semantic layer
├── scripts/e2e.py              # End-to-end checks against the running Docker stack
├── docker-compose.yml          # Postgres, Redis, web, worker
├── docker-compose.monitoring.yml  # Optional Prometheus + Grafana
└── .github/workflows/ci.yml    # Tests on Postgres + SQLite (Python 3.11/3.12), Docker e2e
```

---

## Tech Stack

- **Backend**: Django, Django REST Framework, drf-spectacular, django-filter, sqlglot (formula parsing), pandas
- **Async**: Celery + Redis
- **Frontend**: Django Templates, Chart.js, CSS variables (dark/light)
- **Database**: PostgreSQL (psycopg 3) or SQLite
- **Security**: role-based permissions, token auth, rate limiting, django-axes login lockout
- **Observability**: django-prometheus, Prometheus, Grafana
- **Delivery**: Docker, gunicorn, WhiteNoise, GitHub Actions (unit tests on Postgres + SQLite, docker-compose end-to-end)

---

## Background: The OSI Initiative

The **Open Semantic Interchange (OSI)** is a vendor-neutral specification created by Snowflake, Salesforce, dbt Labs, BlackRock, and 15+ other companies. It standardizes how semantic metadata (metrics, dimensions, relationships) is defined and shared across tools — a "Rosetta Stone" for business data.

This project implements the core principles of OSI:

1. **Canonical metric definitions** — One authoritative formula per business metric
2. **Semantic mappings** — How each source system implements each metric
3. **Cross-source reconciliation** — Automated detection of where definitions diverge
4. **Vendor-neutral interchange** — Export/import semantic models as JSON

Learn more: [VentureBeat — The $1 Trillion AI Problem](https://venturebeat.com/ai/the-usd1-trillion-ai-problem-why-snowflake-tableau-and-blackrock-are-giving)

---

## Roadmap

### Phase 1 — Security & API Polish ✅
- [x] **Authentication** — Login required for all writes; anonymous users get read-only access
- [x] **Role-Based Access Control** — Admin / Editor / Viewer via Django groups and model permissions, API tokens
- [x] **Swagger/OpenAPI Documentation** — `/api/docs/`, generated with drf-spectacular
- [x] **API Rate Limiting** — Per-client limits for anonymous and logged-in users, plus login lockout (django-axes)

### Phase 2 — Production Infrastructure ✅
- [x] **PostgreSQL Support** — `DATABASE_URL`; CI tests on Postgres and SQLite
- [x] **Celery + Redis** — Reconciliation runs and alert delivery in a background worker
- [x] **Alerts & Notifications** — Webhook (Slack-compatible) and email on failed validations, score drops, critical divergences

### Phase 3 — Analytics & Export ✅
- [x] **Historical Trend Analytics** — 30-day "Health Over Time" chart with table view
- [x] **Anomaly Detection & Forecasting** — Per-source score-drop detection and a 7-day outlook
- [x] **Export Formats** — CSV, Excel and Parquet for trust scores, validations, metrics, mappings, and findings
- [x] **Bulk Import** — CSV import of semantic mappings (round-trips with the export); reconcile all metrics in one run

### Phase 4 — UX & Integrations ✅
- [x] **Search & Filtering** — On every list page and API endpoint
- [x] **dbt Connector** — Import metric definitions from dbt Semantic Layer YAML
- [x] **Monitoring & Observability** — `/healthz`, Prometheus `/metrics`, provisioned Grafana dashboard

### Future
- [ ] **Live warehouse & BI connectors** — Sync definitions directly from Snowflake, BigQuery, Tableau, and Salesforce. Not built yet, because each needs a real account to test against; dbt YAML import covers the most common source of metric definitions today.

---

## Contributing

PRs welcome. For changes to scoring logic, reconciliation rules, or governance features, include unit tests in `core/tests/`.

```bash
# Run tests before submitting
python manage.py test core -v 2
```

---

## License

[MIT](LICENSE) © 2025-2026 Somesh Ghaturle
