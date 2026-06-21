# Field Test Analytics

A simple analytics prototype built for the Corractions home assignment.

The application loads a field-test driving session, cleans the measurement data, stores it in SQLite, and presents driving behavior insights through a Streamlit dashboard.

---

## Assignment Scope

The challenge provides a single sample session:

```text
sample-data/
├── field_session_042.csv
└── metadata_session_042.json
```

This project is scoped to that dataset — a prototype, not a production platform.

It demonstrates ingestion, data quality analysis, behavioral analytics, and visualization.

---

## Running Locally

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start the dashboard:

```bash
streamlit run src/app.py
```

On startup, the application:

1. Loads the CSV and JSON metadata from `sample-data/`
2. Validates and cleans the measurement data
3. Stores the session metadata and cleaned measurements in `driving_analysis.db`
4. Computes quality metrics and driving analytics dynamically with pandas

Analytics are **not** stored in the database. They are recalculated each time the app runs.

---

## Project Structure

```text
src/
├── app.py               Streamlit entry point
├── dashboard/           config, loader, UI helpers, tabs
├── ingestion.py         MeasurementColumn enum, load, validate, normalize, clean
├── database.py          SQLite persistence for sessions and measurements
├── quality.py           Missing value and outlier analysis
├── analytics.py         build_analytics_bundle() — all driving metrics
└── visualizations/      theme, chart helpers, driving and behavior charts
requirements.txt         Python dependencies
sample-data/             Assignment CSV and metadata JSON
driving_analysis.db      SQLite database (created on first run)
```

---

## Architecture

```text
Assignment Files
      ↓
  src/ingestion.py
      ↓
  src/database.py        ← store imported metadata + cleaned measurements
      ↓
  src/quality.py         ← compute quality insights at runtime
  src/analytics.py       ← build_analytics_bundle() at runtime
      ↓
  src/visualizations/
  src/dashboard/
  src/app.py
```

**Database responsibility:** store imported data.

**Analytics responsibility:** calculate insights.

**Visualization responsibility:** display insights.

---

## Dashboard Tabs

| Tab | Metrics | Charts / Tables |
| --- | ------- | --------------- |
| Session Data | — | Session metadata table, measurements table |
| Forward Driving | Measurement count, average speed, speed variability, steering variability, total turns, sharp turns | Speed profile, steering timeline, speed/steering distributions, steering bucket chart |
| Reverse Driving | Same metrics as Forward | Same charts as Forward (orange styling) |
| Driver Behavior | Steering jerkiness, speed instability, forward/reverse sudden corrections | Forward and reverse correction timelines, forward vs reverse summary table |
| Data Quality | Cleaning summary pipeline | Invalid values table, outlier summary table |

---

## Technology Choices

**Pandas** — primary data structure for measurements and analytics.

**Streamlit** — simple reviewer-facing dashboard without a separate frontend.

**SQLite** — lightweight local persistence for imported session data.

**Matplotlib / Seaborn** — behavioral charts for the dashboard.

---

## Data Storage

### Sessions

Session metadata is stored exactly as received from the JSON file:

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    metadata_json TEXT NOT NULL,
    source_file TEXT NOT NULL,
    metadata_file TEXT NOT NULL,
    imported_at TEXT NOT NULL
);
```

### Measurements

Only cleaned measurement rows are stored:

```sql
CREATE TABLE measurements (
    measurement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    timestamp TEXT,
    wheel_angle REAL,
    speed REAL,
    reverse_state INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
```

No analytics results, outlier flags, or dashboard metrics are persisted.
