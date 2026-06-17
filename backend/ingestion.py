import json
from io import BytesIO, StringIO

import pandas as pd


REQUIRED_METADATA_FIELDS = ("session_id", "vehicle_id", "driver_id", "recording_date")
REQUIRED_MEASUREMENT_FIELDS = ("timestamp", "speed", "wheel_angle", "reverse_state")
INVALID_VALUE_MARKERS = {"", "null", "NaN", "ERROR_TIMEOUT"}
TRUE_REVERSE_STATE_VALUES = {"1", "true", "True"}
FALSE_REVERSE_STATE_VALUES = {"0", "false", "False"}


class MetadataParser:
    def parse_metadata(self, metadata_content: str | bytes) -> dict[str, object]:
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


class CsvParser:
    def parse_csv(self, csv_content: str | bytes) -> list[dict[str, object | None]]:
        csv_buffer = BytesIO(csv_content) if isinstance(csv_content, bytes) else StringIO(csv_content)
        measurements_dataframe = pd.read_csv(csv_buffer, keep_default_na=False)

        missing_measurement_fields = [
            measurement_field
            for measurement_field in REQUIRED_MEASUREMENT_FIELDS
            if measurement_field not in measurements_dataframe.columns
        ]
        if missing_measurement_fields:
            raise ValueError(f"Missing CSV fields: {', '.join(missing_measurement_fields)}.")

        raw_measurement_rows: list[dict[str, object | None]] = []
        for measurement_row in measurements_dataframe[list(REQUIRED_MEASUREMENT_FIELDS)].to_dict(
            orient="records"
        ):
            raw_measurement_rows.append(dict(measurement_row))

        return raw_measurement_rows


class Normalizer:
    def normalize_measurements(
        self,
        raw_measurement_rows: list[dict[str, object | None]],
    ) -> list[dict[str, object | None]]:
        normalized_measurements: list[dict[str, object | None]] = []

        for row_index, raw_measurement_row in enumerate(raw_measurement_rows):
            raw_timestamp = raw_measurement_row.get("timestamp")
            raw_speed = raw_measurement_row.get("speed")
            raw_wheel_angle = raw_measurement_row.get("wheel_angle")
            raw_reverse_state = raw_measurement_row.get("reverse_state")

            normalized_measurements.append(
                {
                    "row_index": row_index,
                    "timestamp": self._normalize_timestamp(raw_timestamp),
                    "speed": self._normalize_number(raw_speed),
                    "wheel_angle": self._normalize_number(raw_wheel_angle),
                    "reverse_state": self._normalize_reverse_state(raw_reverse_state),
                    "raw_timestamp": self._preserve_raw_value(raw_timestamp),
                    "raw_speed": self._preserve_raw_value(raw_speed),
                    "raw_wheel_angle": self._preserve_raw_value(raw_wheel_angle),
                    "raw_reverse_state": self._preserve_raw_value(raw_reverse_state),
                }
            )

        return normalized_measurements

    def _normalize_timestamp(self, raw_timestamp: object | None) -> str | None:
        if self._is_invalid_value(raw_timestamp):
            return None

        timestamp_value = pd.to_datetime(raw_timestamp, errors="coerce")
        if pd.isna(timestamp_value):
            return None

        return timestamp_value.isoformat()

    def _normalize_number(self, raw_number: object | None) -> float | None:
        if self._is_invalid_value(raw_number):
            return None

        numeric_value = pd.to_numeric(raw_number, errors="coerce")
        if pd.isna(numeric_value):
            return None

        return float(numeric_value)

    def _normalize_reverse_state(self, raw_reverse_state: object | None) -> bool | None:
        if self._is_invalid_value(raw_reverse_state):
            return None

        reverse_state_text = str(raw_reverse_state)
        if reverse_state_text in TRUE_REVERSE_STATE_VALUES:
            return True
        if reverse_state_text in FALSE_REVERSE_STATE_VALUES:
            return False

        return None

    def _preserve_raw_value(self, raw_value: object | None) -> object | None:
        if pd.isna(raw_value):
            return None

        return raw_value

    def _is_invalid_value(self, raw_value: object | None) -> bool:
        if raw_value is None or pd.isna(raw_value):
            return True

        return str(raw_value).strip() in INVALID_VALUE_MARKERS
