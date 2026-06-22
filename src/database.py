"""SQLite persistence — stores session metadata and measurement rows."""

import json
import sqlite3
from datetime import datetime, timezone

import pandas as pd

from ingestion import MeasurementColumn

SESSIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    metadata_json TEXT NOT NULL,
    source_file TEXT NOT NULL,
    metadata_file TEXT NOT NULL,
    imported_at TEXT NOT NULL
);
"""

MEASUREMENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS measurements (
    measurement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    timestamp TEXT,
    wheel_angle REAL,
    speed REAL,
    reverse_state INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
"""


def initialize_database(db_path):
    with sqlite3.connect(db_path) as connection:
        connection.execute(SESSIONS_TABLE_SQL)
        connection.execute(MEASUREMENTS_TABLE_SQL)
        connection.commit()


def _optional_float(value):
    return None if pd.isna(value) else float(value)


def _optional_int(value):
    return None if pd.isna(value) else int(value)


def _timestamp_value(row):
    timestamp = row[MeasurementColumn.TIMESTAMP]
    if pd.notna(timestamp):
        return timestamp.isoformat()

    display_time = row.get(MeasurementColumn.DISPLAY_TIME)
    if pd.notna(display_time):
        return display_time.isoformat()

    return None


def save_session_with_measurements(db_path, metadata, measurement_dataframe, source_file, metadata_file):
    session_id = metadata["session_id"]
    imported_at = datetime.now(timezone.utc).isoformat()
    metadata_json = json.dumps(metadata)

    with sqlite3.connect(db_path) as connection:
        connection.execute("DELETE FROM measurements WHERE session_id = ?", (session_id,))
        connection.execute(
            """
            INSERT OR REPLACE INTO sessions (
                session_id,
                metadata_json,
                source_file,
                metadata_file,
                imported_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, metadata_json, source_file, metadata_file, imported_at),
        )

        measurement_rows = [
            (
                session_id, _timestamp_value(row),
                _optional_float(row[MeasurementColumn.WHEEL_ANGLE]),
                _optional_float(row[MeasurementColumn.SPEED]),
                _optional_int(row[MeasurementColumn.REVERSE_STATE]),
            )
            for _, row in measurement_dataframe.iterrows()
        ]

        connection.executemany(
            """
            INSERT INTO measurements (
                session_id,
                timestamp,
                wheel_angle,
                speed,
                reverse_state
            ) VALUES (?, ?, ?, ?, ?)
            """,
            measurement_rows,
        )
        connection.commit()
