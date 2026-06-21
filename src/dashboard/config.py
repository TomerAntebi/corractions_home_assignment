"""Dashboard configuration — file paths, database location, and shared UI constants."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH = PROJECT_ROOT / "sample-data" / "field_session_042.csv"
METADATA_PATH = PROJECT_ROOT / "sample-data" / "metadata_session_042.json"
DB_PATH = PROJECT_ROOT / "driving_analysis.db"
SOURCE_FILE_NAME = "field_session_042.csv"
METADATA_FILE_NAME = "metadata_session_042.json"
ANALYTICS_NOTE = (
    "Metrics and charts use cleaned data with outlier rows excluded. "
    "Outliers are reported in the Data Quality tab and are not stored in the database."
)
