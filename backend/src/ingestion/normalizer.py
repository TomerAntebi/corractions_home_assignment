from datetime import datetime

import pandas as pd

from validation.models import NormalizedMeasurement


INVALID_VALUE_MARKERS = {"", "null", "NaN", "ERROR_TIMEOUT"}
TRUE_REVERSE_STATE_VALUES = {"1", "true", "True"}
FALSE_REVERSE_STATE_VALUES = {"0", "false", "False"}


def normalize_measurements(
    measurements_dataframe: pd.DataFrame,
) -> list[NormalizedMeasurement]:
    measurements_dataframe = measurements_dataframe.reset_index(drop=True)

    raw_timestamps = measurements_dataframe["timestamp"]
    raw_speeds = measurements_dataframe["speed"]
    raw_wheel_angles = measurements_dataframe["wheel_angle"]
    raw_reverse_states = measurements_dataframe["reverse_state"]

    timestamps = pd.to_datetime(
        raw_timestamps.mask(raw_timestamps.map(_is_invalid_value)),
        errors="coerce",
        dayfirst=True,
    )
    speeds = pd.to_numeric(
        raw_speeds.mask(raw_speeds.map(_is_invalid_value)),
        errors="coerce",
    )
    wheel_angles = pd.to_numeric(
        raw_wheel_angles.mask(raw_wheel_angles.map(_is_invalid_value)),
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
    reverse_states = reverse_states.mask(raw_reverse_states.map(_is_invalid_value))

    return [
        NormalizedMeasurement(
            row_index=row_index,
            timestamp=_to_datetime_or_none(timestamps.iloc[row_index]),
            speed=_to_float_or_none(speeds.iloc[row_index]),
            wheel_angle=_to_float_or_none(wheel_angles.iloc[row_index]),
            reverse_state=_to_bool_or_none(reverse_states.iloc[row_index]),
            raw_timestamp=raw_timestamps.iloc[row_index],
            raw_speed=raw_speeds.iloc[row_index],
            raw_wheel_angle=raw_wheel_angles.iloc[row_index],
            raw_reverse_state=raw_reverse_states.iloc[row_index],
        )
        for row_index in range(len(measurements_dataframe))
    ]


def _to_datetime_or_none(timestamp_value: object) -> datetime | None:
    if pd.isna(timestamp_value):
        return None

    if isinstance(timestamp_value, pd.Timestamp):
        return timestamp_value.to_pydatetime()

    if isinstance(timestamp_value, datetime):
        return timestamp_value

    return None


def _to_float_or_none(numeric_value: object) -> float | None:
    if pd.isna(numeric_value):
        return None

    return float(numeric_value)


def _to_bool_or_none(bool_value: object) -> bool | None:
    if pd.isna(bool_value):
        return None

    return bool(bool_value)


def _is_invalid_value(raw_value: object | None) -> bool:
    if raw_value is None or pd.isna(raw_value):
        return True

    return str(raw_value).strip() in INVALID_VALUE_MARKERS
