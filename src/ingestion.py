import json
from enum import StrEnum

import pandas as pd


class MeasurementColumn(StrEnum):
    TIMESTAMP = "timestamp"
    WHEEL_ANGLE = "wheel_angle"
    SPEED = "speed"
    REVERSE_STATE = "reverse_state"


REQUIRED_COLUMNS = list(MeasurementColumn)


def load_dataset(csv_path):
    return pd.read_csv(csv_path)


def load_session_metadata(json_path):
    with open(json_path, "r") as file:
        return json.load(file)


def validate_required_columns(dataframe):
    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing columns: {missing_columns}"
        )


def validate_metadata_file(metadata):
    if not isinstance(metadata, dict):
        raise ValueError("Metadata must be a JSON object.")

    if "session_id" not in metadata:
        raise ValueError("Missing metadata field: session_id")

    if not metadata["session_id"]:
        raise ValueError("Metadata field session_id must not be empty.")


def normalize_types(dataframe):
    normalized_dataframe = dataframe.copy()

    normalized_dataframe[MeasurementColumn.TIMESTAMP] = pd.to_datetime(
        normalized_dataframe[MeasurementColumn.TIMESTAMP]
    )

    normalized_dataframe[MeasurementColumn.WHEEL_ANGLE] = pd.to_numeric(
        normalized_dataframe[MeasurementColumn.WHEEL_ANGLE],
        errors="coerce",
    )

    normalized_dataframe[MeasurementColumn.SPEED] = pd.to_numeric(
        normalized_dataframe[MeasurementColumn.SPEED],
        errors="coerce",
    )

    normalized_dataframe[MeasurementColumn.REVERSE_STATE] = pd.to_numeric(
        normalized_dataframe[MeasurementColumn.REVERSE_STATE],
        errors="coerce",
    )

    return normalized_dataframe


def clean_measurement_data(dataframe):
    return dataframe.dropna(
        subset=REQUIRED_COLUMNS
    ).reset_index(drop=True)
