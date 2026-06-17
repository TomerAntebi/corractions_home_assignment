# Field Test Ingestion & Analytics

Local prototype for ingesting raw field-test CSV data, validating data quality, storing the normalized session, and presenting operational analytics in a Streamlit dashboard.

## What This Project Does

The application moves a field-test session from raw files into a reviewable analytics workflow:

1. Reads session metadata from JSON.
2. Reads measurement data from CSV.
3. Normalizes raw values while preserving original inputs.
4. Validates required fields, numeric values, ranges, and invalid sensor markers.
5. Detects statistical outliers using IQR.
6. Stores the session and measurements in PostgreSQL.
7. Derives quality reports and analytics from stored measurements for API responses.
8. Exposes REST APIs with FastAPI.
9. Displays the session, quality metrics, analytics, charts, and measurement table in Streamlit.

## Running Locally

Start the full stack:

```bash
docker compose up --build
```

Services:

- Backend API: `http://localhost:8000`
- Streamlit dashboard: `http://localhost:8501`
- PostgreSQL: `localhost:5432`

On startup, the backend runs migrations and imports the sample session from `sample-data/` if it has not already been imported.

## Architecture

The project is intentionally small and local-first:

- `backend/` contains the FastAPI API, ingestion flow, validation, data quality logic, analytics, persistence, and migrations.
- `frontend/` contains the Streamlit dashboard and API client.
- `sample-data/` contains the provided metadata and CSV files.
- `docker-compose.yml` runs PostgreSQL, backend, and frontend together.

Backend flow:

```text
metadata + csv
  -> parse
  -> normalize
  -> validate
  -> analyze quality
  -> persist session + measurements
  -> derive quality report + analytics
  -> expose via API
```

Key backend modules:

- `ingestion.py`: metadata parsing, CSV parsing, and normalization.
- `validation/`: validation configuration, models, and measurement validation logic.
- `quality.py`: IQR outlier detection and quality report generation.
- `analytics.py`: statistics for speed, wheel angle, and reverse-state summary.
- `import_flow.py`: end-to-end import and persistence flow.
- `db/`: SQLAlchemy models, database session setup, and Alembic migrations.
- `api/`: FastAPI routes and session API handlers.

## Data Quality

The system handles common raw field-data issues:

- Missing required fields: `timestamp`, `speed`, `wheel_angle`.
- Non-numeric sensor values for numeric fields.
- Out-of-range values:
  - speed must be between `0` and `200`.
  - wheel angle must be between `-45` and `45`.
- Invalid sensor marker values such as `ERROR_TIMEOUT`.
- Outliers detected with the IQR method on valid numeric speed and wheel-angle values.

The quality report includes:

- total rows
- valid rows
- invalid rows
- outlier rows
- quality score
- missing fields by field name
- invalid rows by validation rule
- sensor error markers

Invalid rows and outliers are preserved for review, but analytics use valid non-outlier measurements by default.

## Outlier Detection

Outliers are detected using the IQR method.

To avoid classifying legitimate reverse-driving measurements as anomalies, IQR calculations are performed separately for:

- Forward driving measurements
- Reverse driving measurements

This preserves the simplicity of the IQR approach while producing more meaningful anomaly detection results for mixed driving sessions.

## Analytics

For speed and wheel angle, the backend calculates:

- minimum
- maximum
- mean
- median
- standard deviation
- p5
- p95

The backend also calculates a reverse-state summary:

- forward measurement count
- reverse measurement count

## Dashboard

The Streamlit dashboard provides a quick review surface for the imported session:

- session information
- executive summary
- quality metrics
- data quality and validation breakdowns
- speed and wheel-angle statistics
- speed-over-time and wheel-angle-over-time charts
- reverse-state summary
- distribution charts
- problem-row preview
- full measurements table

Dashboard visualizations use Matplotlib and render through Streamlit.

## API Overview

Primary endpoints:

- `GET /api/v1/health`
- `GET /api/v1/sessions`
- `GET /api/v1/sessions/{id}/dashboard`

The bundled sample session is imported automatically during backend startup from `sample-data/`.

## Scaling Discussion

This prototype is designed for local review, but the flow can scale with clear next steps:

- For many files, move import work to a background job queue instead of processing uploads synchronously.
- For larger CSVs, stream parsing in chunks instead of loading the full file at once.
- For thousands of sessions, add pagination and filtering to session list APIs.
- For long measurement series, downsample dashboard charts and keep raw measurements queryable separately.
- For data quality at scale, persist validation issue summaries and index common filter fields.
- For operational use, add authentication, structured logging, observability, and retryable import jobs.

## Notes

This is a timeboxed assignment prototype, not a production platform. The implementation favors readable, deterministic data handling and a straightforward reviewer experience over enterprise architecture.
