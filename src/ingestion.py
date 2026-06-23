"""Data ingestion — loads CSV/JSON, validates columns, normalizes types, and builds session timeline."""

import json
import warnings
from enum import StrEnum

import pandas as pd


class MeasurementColumn(StrEnum):
    TIMESTAMP = "timestamp"
    WHEEL_ANGLE = "wheel_angle"
    SPEED = "speed"
    REVERSE_STATE = "reverse_state"
    ELAPSED_SECONDS = "elapsed_seconds"
    DISPLAY_TIME = "display_time"


REQUIRED_COLUMNS = [
    MeasurementColumn.TIMESTAMP, MeasurementColumn.WHEEL_ANGLE,
    MeasurementColumn.SPEED, MeasurementColumn.REVERSE_STATE,
]

TIMELINE_METADATA_FIELDS = ("start_time_utc", "end_time_utc", "sample_rate_hz")


def load_dataset(csv_path):
    return pd.read_csv(csv_path)


def load_session_metadata(json_path):
    with open(json_path, "r") as file:
        return json.load(file)


def validate_required_columns(dataframe):
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]

    if missing_columns:
        raise ValueError(f"Missing columns: {missing_columns}")


def validate_metadata_file(metadata):
    if not isinstance(metadata, dict):
        raise ValueError("Metadata must be a JSON object.")

    if "session_id" not in metadata:
        raise ValueError("Missing metadata field: session_id")

    if not metadata["session_id"]:
        raise ValueError("Metadata field session_id must not be empty.")

    for field_name in TIMELINE_METADATA_FIELDS:
        if field_name not in metadata:
            raise ValueError(f"Missing metadata field: {field_name}")

    if metadata["sample_rate_hz"] <= 0:
        raise ValueError("Metadata field sample_rate_hz must be greater than zero.")


def normalize_types(dataframe):
    """Convert raw CSV values to typed columns while preserving all rows."""
    normalized_dataframe = dataframe.copy()

    normalized_dataframe[MeasurementColumn.TIMESTAMP] = pd.to_datetime(
        normalized_dataframe[MeasurementColumn.TIMESTAMP]
    )
    for column in (
        MeasurementColumn.WHEEL_ANGLE,
        MeasurementColumn.SPEED,
        MeasurementColumn.REVERSE_STATE,
    ):
        normalized_dataframe[column] = pd.to_numeric(
            normalized_dataframe[column], errors="coerce"
        )

    return normalized_dataframe


def build_measurement_dataframe(raw_dataframe, metadata):
    """Return the final measurement dataframe used by storage and downstream analysis."""
    normalized_dataframe = normalize_types(raw_dataframe)
    return add_session_timeline(normalized_dataframe, metadata)


def add_session_timeline(dataframe, metadata):
    """Create session time from metadata instead of trusting row timestamps for elapsed time."""
    sample_rate_hz = metadata["sample_rate_hz"]
    start_time = pd.to_datetime(metadata["start_time_utc"])
    end_time = pd.to_datetime(metadata["end_time_utc"])

    timeline_dataframe = dataframe.reset_index(drop=True).copy()
    timeline_dataframe[MeasurementColumn.ELAPSED_SECONDS] = (
        pd.Series(range(len(timeline_dataframe))) / sample_rate_hz
    )
    timeline_dataframe[MeasurementColumn.DISPLAY_TIME] = (
        start_time
        + pd.to_timedelta(
            timeline_dataframe[MeasurementColumn.ELAPSED_SECONDS], unit="s",
        )
    )

    expected_duration_seconds = (end_time - start_time).total_seconds()
    expected_rows = int(expected_duration_seconds * sample_rate_hz) + 1
    if abs(len(timeline_dataframe) - expected_rows) > 1:
        warnings.warn(
            "Measurement row count does not align with metadata session duration.",
            stacklevel=2,
        )

    return timeline_dataframe
