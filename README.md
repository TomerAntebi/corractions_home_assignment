# Field Test Analytics

A simple analytics prototype built for the Corractions home assignment.

The application loads a field-test driving session, normalizes measurement data, stores it in SQLite, and presents driving behavior insights through a Streamlit dashboard.

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
2. Normalizes types and builds a session timeline from metadata
3. Stores all measurement rows in `driving_analysis.db` (missing values kept as NULL)
4. Computes quality flags and driving analytics dynamically with pandas

Analytics are **not** stored in the database. They are recalculated each time the app runs.

---

## Project Structure

```text
src/
├── app.py               Streamlit entry point
├── dashboard/           config, loader, UI helpers, tabs
├── ingestion.py         load, validate, normalize, timeline creation
├── database.py          SQLite persistence for sessions and measurements
├── quality.py           Missing value and outlier flagging
├── analytics.py         build_analytics_bundle() — all driving metrics
└── visualizations/      theme, chart helpers, driving and behavior charts
requirements.txt         Python dependencies
sample-data/             Assignment CSV and metadata JSON
driving_analysis.db      SQLite database (created on first run)
```

---

## Architecture

```text
CSV + Metadata
      ↓
Timeline Creation (elapsed_seconds, display_time)
      ↓
Quality Analysis (flags only — no row removal)
      ↓
Analytics Bundle (build_analytics_bundle)
      ↓
Visualizations
      ↓
Streamlit Dashboard
```

**Database responsibility:** store imported data.

**Analytics responsibility:** calculate insights.

**Visualization responsibility:** display insights.

---

## Dashboard Tabs

| Tab | Metrics | Charts / Tables |
| --- | ------- | --------------- |
| Session Data | — | Session metadata table, measurements table |
| Forward Driving | Measurements, average speed, speed/steering variability | Speed timeline, steering timeline, distributions, steering bucket chart |
| Reverse Driving | Same as Forward | Same charts as Forward (orange styling) |
| Driver Behavior | Control profile, sudden steering events | Control profile, attention mapping timeline, forward vs reverse summary table |
| Data Quality | Missing values, outlier flags | Quality summary, missing values table, outlier summary |

---

## Timeline

Session time is derived from metadata — not from CSV timestamps or row index:

- `elapsed_seconds` — 0, 1, 2, … based on `sample_rate_hz`
- `display_time` — `start_time_utc` + elapsed seconds

Reverse segments are detected dynamically from `reverse_state` and expressed in elapsed seconds.

---

## Technology Choices

**Pandas** — primary data structure for measurements and analytics.

**Streamlit** — simple reviewer-facing dashboard without a separate frontend.

**SQLite** — lightweight local persistence for imported session data.

**Matplotlib / Seaborn** — behavioral charts for the dashboard.

---

## Data Storage

### Sessions

Session metadata is stored exactly as received from the JSON file.

### Measurements

All measurement rows are stored. Missing sensor values are stored as NULL.

No analytics results, outlier flags, or dashboard metrics are persisted.
