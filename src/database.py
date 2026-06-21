"""SQLite persistence — stores session metadata and cleaned measurement rows."""

import json
import sqlite3
from datetime import datetime, timezone

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


def save_session_with_measurements(
    db_path,
    metadata,
    cleaned_dataframe,
    source_file,
    metadata_file,
):
    session_id = metadata["session_id"]
    imported_at = datetime.now(timezone.utc).isoformat()
    metadata_json = json.dumps(metadata)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "DELETE FROM measurements WHERE session_id = ?",
            (session_id,),
        )
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
            (
                session_id,
                metadata_json,
                source_file,
                metadata_file,
                imported_at,
            ),
        )

        measurement_rows = [
            (
                session_id,
                row[MeasurementColumn.TIMESTAMP].isoformat(),
                float(row[MeasurementColumn.WHEEL_ANGLE]),
                float(row[MeasurementColumn.SPEED]),
                int(row[MeasurementColumn.REVERSE_STATE]),
            )
            for _, row in cleaned_dataframe.iterrows()
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
