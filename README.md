# Field Test Ingestion & Analytics

A local prototype built for the Corractions home assignment.

The system ingests a field-test driving session, handles real-world data quality issues, stores the processed data in PostgreSQL, and presents driving behavior insights through a Streamlit dashboard.

---

# Assignment Scope

The challenge provides a single sample session:

```text
sample-data/
├── field_session_042.csv
└── metadata_session_042.json
```

This project is intentionally scoped to the provided dataset.

It is **not** a production platform, generic ingestion engine, or large-scale analytics system.

The focus is to demonstrate:

* Data ingestion
* Data normalization
* Data validation
* Data quality analysis
* Analytics generation
* Data visualization

---

# Features

## Data Ingestion

* Read metadata from JSON
* Read measurements from CSV
* Validate required fields
* Normalize timestamps, numbers, and boolean values
* Capture offending CSV values in validation errors at import time

## Data Quality

* Missing field detection
* Invalid numeric value detection
* Range validation
* Sensor error marker detection (`ERROR_TIMEOUT`)
* Statistical outlier detection using IQR

## Data Persistence

* Store session metadata
* Store all measurements
* Store validation results
* Store outlier flags

## Analytics

* Driving behavior metrics
* Steering variability
* Speed variability
* Turning behavior analysis
* Reverse-driving analysis
* Speed-steering correlation
* Generated reviewer insights

## Dashboard

* Session information
* Driver behavior insights
* Data quality summary
* Validation breakdown
* Driving visualizations
* Problem row inspection
* Raw measurement review

---

# Running Locally

Start the complete stack:

```bash
docker compose up --build
```

Services:

| Service             | URL                   |
| ------------------- | --------------------- |
| Backend API         | http://localhost:8000 |
| Streamlit Dashboard | http://localhost:8501 |
| PostgreSQL          | localhost:5432        |

---

# Automatic Data Import

When the backend starts:

1. Database tables are created and the sample session is seeded during FastAPI startup.
2. Duplicate imports are skipped.

No manual import step is required.

---

# System Pipeline

The application follows a simple and explicit processing pipeline:

```text
Metadata JSON
+
CSV Measurements
        │
        ▼
   Parse Files
        │
        ▼
 Normalize Data
        │
        ▼
 Validate Measurements
        │
        ▼
 Detect Outliers (IQR)
        │
        ▼
 Store in PostgreSQL
        │
        ▼
 Generate Analytics
        │
        ▼
 Build Dashboard Response
        │
        ▼
 Streamlit Dashboard
```

---

# Architecture

```mermaid
flowchart TB

    Metadata["metadata_session_042.json"]
    Csv["field_session_042.csv"]

    Metadata --> Parser
    Csv --> Parser

    Parser["Parse"]

    Parser --> Normalize["Normalize"]

    Normalize --> Validate["Validate"]

    Validate --> Quality["Quality Analysis<br/>IQR Outlier Detection"]

    Quality --> Database["PostgreSQL"]

    Database --> Analytics["Analytics Engine"]

    Database --> Api["FastAPI API"]

    Analytics --> Api

    Api --> Dashboard["Streamlit Dashboard"]
```

---

# Project Structure

```text
backend/
├── src/
│   ├── main.py              FastAPI application entry point
│   ├── api/                 FastAPI routes
│   ├── db/                  SQLAlchemy models and database setup
│   ├── validation/          Validation rules and models
│   ├── analytics/           Driving behavior analytics (orchestration, metrics, insights)
│   ├── quality/             Outlier detection and quality reporting
│   ├── ingestion/           Metadata parsing, CSV parsing, normalization
│   ├── schemas/             Pydantic response models
│   ├── import_flow.py       End-to-end ingestion workflow
│   └── seed_sample_data.py  Sample data importer
├── requirements.txt
└── Dockerfile

frontend/
├── dashboard.py         Streamlit application entry point
├── api_client.py        Backend API communication
├── dashboard/
│   ├── sections.py      Dashboard layout and rendering
│   ├── data.py          Table and display formatting
│   ├── chart_data.py    API-to-chart DataFrame mapping
│   ├── charts.py        Chart creation helpers
│   └── helpers.py       Formatting and utility helpers

sample-data/
├── field_session_042.csv
└── metadata_session_042.json

docker-compose.yml
README.md
```

---

# Why This Technology Stack

## PostgreSQL

Sessions and measurements are naturally relational data.

PostgreSQL provides:

* Simple persistence
* Easy querying
* Strong typing
* Clear interview discussion

---

## FastAPI

FastAPI provides:

* Typed API contracts
* Simple route definitions
* Easy integration with Pydantic models
* Lightweight backend architecture

---

## Streamlit

Streamlit allows rapid creation of reviewer-facing dashboards without building a separate frontend application.

This makes it ideal for a time-boxed prototype.

---

## Docker Compose

Docker Compose allows the entire system to run using a single command.

This makes review and evaluation straightforward.

---

# Backend

The backend is responsible for ingestion, validation, persistence, analytics, and API responses.

## ingestion/

Responsible for:

* Metadata parsing (`parse_metadata`)
* CSV parsing (`parse_csv`)
* Data normalization (`normalize_measurements`)

---

## validation/

Responsible for:

* Required field validation
* Numeric validation
* Range validation
* Sensor error marker validation

---

## quality/

Responsible for:

* Statistical outlier detection
* Data quality reporting

Outliers are detected using the Interquartile Range (IQR) method.

Forward-driving and reverse-driving measurements are analyzed separately to avoid false outlier classifications.

---

## analytics/

Responsible for generating driving behavior analytics such as:

* Steering variability
* Speed variability
* Turning behavior
* Reverse-driving behavior
* Speed-steering correlation
* Reviewer insights

Modules:

* `calculator.py` — orchestration only
* `statistics.py` — basic statistics and forward timeline series
* `driving_behavior.py` — driver behavior metrics and speed-steering correlation
* `insights.py` — text interpretation

---

## import_flow.py

Coordinates the complete import workflow:

```text
Parse
→ Normalize
→ Validate
→ Detect Outliers
→ Persist
```

---

## db/

Contains:

* SQLAlchemy models
* Database session setup
* `initialize_database()` — creates tables via `Base.metadata.create_all()`

---

## api/

Provides dashboard-facing API endpoints.

---

# Frontend

The frontend is implemented using Streamlit.

Its responsibility is presentation only.

All ingestion, validation, quality analysis, and analytics calculations happen in the backend.

The frontend consumes the dashboard API response and renders the results for review.

---

## Session Information

Displays session metadata and recording context.

Examples:

* Session ID
* Vehicle ID
* Recording date
* Test location
* Hardware version
* Active sensors

---

## Driver Behavior Insights

Metrics and observations are split by drive direction:

**Forward Driving** (primary control analysis):

* Steering variability
* Speed variability
* Turning measurements
* Sharp turn measurements
* Speed-steering correlation

**Reverse Driving** (context):

* Reverse measurement count and percentage
* Average reverse speed
* Reverse steering variability

Key observations are generated automatically from these metrics.

---

## Data Quality

Displays:

* Total rows
* Valid rows
* Invalid rows
* Outlier rows
* Sensor error markers

---

## Validation Breakdown

Explains why measurements failed validation.

Examples:

* Missing values
* Invalid numeric values
* Range violations
* Sensor errors

---

## Driving Visualization

Forward-driving charts use the pre-computed backend timeline (`forwardDriving.timeline`):

* Speed Across Session (forward only)
* Wheel Angle Across Session (forward only)
* Speed vs Steering scatter (forward only; derived from timeline on the dashboard)

**Forward vs Reverse:**

* Forward vs Reverse comparison — grouped bars for average speed and steering variability (Forward vs Reverse)

The frontend maps API series to charts without recomputing analytics.

---

## Problem Rows

Displays:

* Invalid measurements
* Outlier measurements
* Validation messages (including raw offending values where relevant)
* Normalized values

This allows reviewers to quickly understand data quality issues.

---

## Raw Measurements

Displays the normalized measurements used by the dashboard (not original CSV strings).

---

# Data Quality Handling

The sample data intentionally includes real-world quality issues.

The system detects:

## Missing Required Fields

Examples:

```text
timestamp
speed
wheel_angle
```

---

## Invalid Numeric Values

Examples:

```text
abc
xyz
```

where numeric values are expected.

---

## Range Violations

### Speed

```text
0 <= speed <= 200
```

### Wheel Angle

```text
-45 <= wheel_angle <= 45
```

---

## Sensor Error Markers

Examples:

```text
ERROR_TIMEOUT
```

These are reported explicitly rather than treated as generic validation failures.

---

## Statistical Outliers

Outliers are detected using IQR.

Only valid measurements participate in outlier analysis.

Outliers remain visible for reviewer inspection.

---

# Analytics

The backend generates analytics from valid, non-outlier measurements.

## Driving Stability

* Steering variability
* Speed variability

## Turning Behavior

* Turning measurements
* Sharp turn measurements
* Average speed while turning
* Average speed while driving straight

## Reverse Driving

* Reverse percentage
* Reverse measurement count
* Average reverse speed

## Driving Relationships

* Speed-steering correlation

## Reviewer Insights

Short observations generated from calculated metrics.

Examples:

```text
No sharp turn measurements were detected.

Reverse driving accounted for 16% of analyzed measurements.

No strong relationship was observed between steering intensity and speed.
```

---

# API Overview

Primary endpoints:

```http
GET /api/v1/health

GET /api/v1/sessions

GET /api/v1/sessions/{id}/dashboard

GET /api/v1/sessions/{id}/measurements
```

The dashboard endpoint provides:

* Session metadata
* Quality report
* Analytics: `forwardDriving`, `reverseDriving`, `drivingInsights`

The measurements endpoint provides the full measurement list for tables.

---

# Scaling Considerations

If this prototype were expanded beyond the assignment:

* Background import jobs
* Chunked CSV processing
* Session pagination
* Dashboard chart downsampling
* Authentication
* Structured logging
* Monitoring and observability
* Retryable import workflows

These improvements were intentionally left out to keep the assignment focused and easy to review.

---

# Future Improvements

Possible next steps:

* Manual file upload endpoint
* Session filtering and pagination
* Larger dataset support
* Authentication and authorization
* Operational monitoring
* Advanced analytics

---
