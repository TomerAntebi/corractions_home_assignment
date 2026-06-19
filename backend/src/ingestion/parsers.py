import json
from io import BytesIO, StringIO

import pandas as pd


REQUIRED_METADATA_FIELDS = ("session_id", "vehicle_id", "driver_id", "recording_date")
REQUIRED_MEASUREMENT_FIELDS = ("timestamp", "speed", "wheel_angle", "reverse_state")


def parse_metadata(metadata_content: str | bytes) -> dict[str, object]:
    try:
        parsed_metadata: object = json.loads(metadata_content)
    except json.JSONDecodeError as parse_error:
        raise ValueError("Metadata content must be valid JSON.") from parse_error

    if not isinstance(parsed_metadata, dict):
        raise ValueError("Metadata content must be a JSON object.")

    missing_metadata_fields = [
        metadata_field
        for metadata_field in REQUIRED_METADATA_FIELDS
        if metadata_field not in parsed_metadata
    ]
    if missing_metadata_fields:
        raise ValueError(f"Missing metadata fields: {', '.join(missing_metadata_fields)}.")

    return dict(parsed_metadata)


def parse_csv(csv_content: str | bytes) -> pd.DataFrame:
    csv_buffer = BytesIO(csv_content) if isinstance(csv_content, bytes) else StringIO(csv_content)
    measurements_dataframe = pd.read_csv(csv_buffer, keep_default_na=False)

    missing_measurement_fields = [
        measurement_field
        for measurement_field in REQUIRED_MEASUREMENT_FIELDS
        if measurement_field not in measurements_dataframe.columns
    ]
    if missing_measurement_fields:
        raise ValueError(f"Missing CSV fields: {', '.join(missing_measurement_fields)}.")

    return measurements_dataframe[list(REQUIRED_MEASUREMENT_FIELDS)]
