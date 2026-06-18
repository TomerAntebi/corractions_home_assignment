# Field Test Ingestion & Analytics

Local prototype for the Corractions home challenge: ingest the provided field-test session, handle real-world data quality issues, store the data in PostgreSQL, and review session insights in a Streamlit dashboard.

## Assignment Scope

The challenge provides one sample session in `sample-data/`:

- `field_session_042.csv` — raw measurement batch
- `metadata_session_042.json` — session metadata

The prototype is intentionally scoped to this sample data. It is not a generic ingestion platform or production system.

## What This Project Does

The application satisfies the two core requirements from the challenge:

### 1. Ingest and process the data

1. Read session metadata from JSON and measurements from CSV.
2. Normalize raw values while preserving the original inputs.
3. Validate required fields, numeric values, ranges, and invalid sensor markers.
4. Detect statistical outliers on valid rows using IQR.
5. Store the session and measurements in PostgreSQL.

### 2. Visualize and analyze the session

1. Expose processed session data through a small FastAPI API.
2. Display session metadata, data quality, driving behavior KPIs, generated insights, charts, and raw/problem rows in Streamlit.

## Running Locally

Start the full stack:

```bash
docker compose up --build
```

Services:

- Backend API: `http://localhost:8000`
- Streamlit dashboard: `http://localhost:8501`
- PostgreSQL: `localhost:5432`

On startup, the backend runs Alembic migrations and imports the bundled sample session if it is not already in the database.

## Architecture

```text
sample-data/
  -> seed_sample_data.py
  -> import_flow.py
      parse metadata + csv
      normalize
      validate
      detect outliers (IQR)
      persist to PostgreSQL
  -> FastAPI dashboard API
  -> Streamlit dashboard
```

Project layout:

- `backend/` — FastAPI API, ingestion, validation, quality analysis, analytics, persistence, migrations
- `frontend/` — Streamlit dashboard and API client
- `sample-data/` — provided challenge files
- `docker-compose.yml` — PostgreSQL, backend, and frontend

### Why this stack

- **PostgreSQL** — sessions and measurements are relational data; easy to query for dashboard responses and to explain in an interview.
- **FastAPI** — small typed REST API between storage and the dashboard.
- **Streamlit** — fastest way to build a reviewer-facing dashboard for one sample session.
- **Docker Compose** — one command to spin up the full review environment.

### Backend modules

- `ingestion.py` — metadata parsing, CSV parsing, normalization
- `validation/` — validation models and measurement validation rules
- `quality.py` — IQR outlier detection at import time and quality report generation for the API
- `analytics.py` — driving behavior metrics and plain-language insights
- `import_flow.py` — end-to-end import and persistence
- `seed_sample_data.py` — imports the provided sample session on startup
- `db/` — SQLAlchemy models, database session setup, Alembic migrations
- `api/` — FastAPI routes

## Data Quality

The sample CSV contains the kind of real-world issues the challenge expects:

- Missing required fields: `timestamp`, `speed`, `wheel_angle`
- Non-numeric sensor values
- Out-of-range values:
  - speed must be between `0` and `200`
  - wheel angle must be between `-45` and `45`
- Invalid sensor markers such as `ERROR_TIMEOUT`
- Statistical outliers detected with IQR on valid speed and wheel-angle values

Invalid rows and outliers are preserved for review. Analytics use valid, non-outlier measurements by default.

Outlier detection runs separately for forward-driving and reverse-driving measurements so reverse sessions are not misclassified as anomalies.

The quality report exposed by the API includes:

- total rows
- valid rows
- invalid rows
- outlier rows
- missing fields by field name
- invalid rows by validation rule
- sensor error markers

## Analytics

The backend computes session analytics from stored measurements:

- chart reference means for speed and wheel angle
- driving behavior metrics:
  - steering and speed variability
  - turning and sharp-turn measurement counts and average speeds during turn vs straight measurements
  - speed–steering correlation
  - reverse-driving percentage and average reverse speed
- plain-language driving insights generated from those metrics

The dashboard renders API values and builds charts from the measurement time series.

## Dashboard

The Streamlit dashboard is organized for a quick reviewer scan:

1. **Session Information** — metadata and recording context
2. **Driver Behavior** — grouped KPI cards for stability, turning, reverse driving, and key observations
3. **Data Quality** — row counts and detected sensor error markers when present
4. **Validation Breakdown** — missing fields, validation rules, and sensor errors
5. **Driving Visualization** — speed across session, wheel angle across session, speed vs steering scatter, turn vs straight speed comparison
6. **Problem Rows** — invalid and outlier rows with validation messages, raw values, and normalized values
7. **Raw Measurements** — valid, non-outlier measurement table

Charts use Matplotlib and render through Streamlit.

## API Overview

Primary endpoints:

- `GET /api/v1/health`
- `GET /api/v1/sessions`
- `GET /api/v1/sessions/{id}/dashboard`

There is no HTTP file-upload import endpoint. The provided sample session is imported automatically during backend startup from `sample-data/`.

## How I Would Scale This

If this moved from one sample file to thousands of longer files:

- Move import work to background jobs instead of running it during app startup
- Stream CSV parsing in chunks for large files
- Add pagination and filtering to session list APIs
- Downsample dashboard charts while keeping raw measurements queryable separately
- Persist validation summaries and index common filter fields
- Add authentication, structured logging, observability, and retryable import jobs

## Next Steps

If this were extended beyond the timeboxed prototype, the next priorities would be:

- Add `POST /api/v1/sessions/import` for manual file uploads
- Add session pagination and filtering for large session lists
- Downsample long time-series charts while keeping raw measurements queryable
- Add authentication and production observability

## Notes

This is a timeboxed assignment prototype built for the provided sample session. The implementation favors readable, deterministic data handling and a straightforward reviewer experience over enterprise architecture.

Questions about the challenge can be sent to yuval@corractions.com.
