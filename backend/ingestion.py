import json
from datetime import datetime
from io import BytesIO, StringIO

import pandas as pd

from validation.models import NormalizedMeasurement


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
    def parse_csv(self, csv_content: str | bytes) -> pd.DataFrame:
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


class Normalizer:
    def normalize_measurements(
        self,
        measurements_dataframe: pd.DataFrame,
    ) -> list[NormalizedMeasurement]:
        measurements_dataframe = measurements_dataframe.reset_index(drop=True)

        raw_timestamps = measurements_dataframe["timestamp"]
        raw_speeds = measurements_dataframe["speed"]
        raw_wheel_angles = measurements_dataframe["wheel_angle"]
        raw_reverse_states = measurements_dataframe["reverse_state"]

        timestamps = pd.to_datetime(
            raw_timestamps.mask(raw_timestamps.map(self._is_invalid_value)),
            errors="coerce",
            dayfirst=True,
        )
        speeds = pd.to_numeric(
            raw_speeds.mask(raw_speeds.map(self._is_invalid_value)),
            errors="coerce",
        )
        wheel_angles = pd.to_numeric(
            raw_wheel_angles.mask(raw_wheel_angles.map(self._is_invalid_value)),
            errors="coerce",
        )
        reverse_states = (
            raw_reverse_states.astype(str)
            .str.strip()
            .map(
                {
                    **{value: True for value in TRUE_REVERSE_STATE_VALUES},
                    **{value: False for value in FALSE_REVERSE_STATE_VALUES},
                }
            )
        )
        reverse_states = reverse_states.mask(raw_reverse_states.map(self._is_invalid_value))

        return [
            NormalizedMeasurement(
                row_index=row_index,
                timestamp=self._to_datetime_or_none(timestamps.iloc[row_index]),
                speed=self._to_float_or_none(speeds.iloc[row_index]),
                wheel_angle=self._to_float_or_none(wheel_angles.iloc[row_index]),
                reverse_state=self._to_bool_or_none(reverse_states.iloc[row_index]),
                raw_timestamp=raw_timestamps.iloc[row_index],
                raw_speed=raw_speeds.iloc[row_index],
                raw_wheel_angle=raw_wheel_angles.iloc[row_index],
                raw_reverse_state=raw_reverse_states.iloc[row_index],
            )
            for row_index in range(len(measurements_dataframe))
        ]

    def _to_datetime_or_none(self, timestamp_value: object) -> datetime | None:
        if pd.isna(timestamp_value):
            return None

        if isinstance(timestamp_value, pd.Timestamp):
            return timestamp_value.to_pydatetime()

        if isinstance(timestamp_value, datetime):
            return timestamp_value

        return None

    def _to_float_or_none(self, numeric_value: object) -> float | None:
        if pd.isna(numeric_value):
            return None

        return float(numeric_value)

    def _to_bool_or_none(self, bool_value: object) -> bool | None:
        if pd.isna(bool_value):
            return None

        return bool(bool_value)

    def _is_invalid_value(self, raw_value: object | None) -> bool:
        if raw_value is None or pd.isna(raw_value):
            return True

        return str(raw_value).strip() in INVALID_VALUE_MARKERS
