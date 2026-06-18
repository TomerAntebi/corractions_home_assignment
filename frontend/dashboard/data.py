from typing import cast

import pandas as pd

from dashboard.helpers import (
    JsonObject,
    format_count,
    format_display_value,
    format_float_metric,
    format_percentage,
    format_validation_error_messages,
)


MEASUREMENT_COLUMNS = ["rowIndex", "speed", "wheelAngle"]
STEERING_BUCKET_BINS = [0, 5, 10, 15, 20, 25, float("inf")]
STEERING_BUCKET_LABELS = ["0-5°", "5-10°", "10-15°", "15-20°", "20-25°", "25°+"]
LOW_STEERING_BUCKETS = ("0-5°", "5-10°")
HIGH_STEERING_BUCKETS = ("20-25°", "25°+")
STEERING_SPEED_CHANGE_THRESHOLD = 0.05
VALIDATION_RULE_LABELS = (
    ("required", "Missing Fields"),
    ("numeric", "Numeric Errors"),
    ("range", "Range Errors"),
    ("invalid_marker", "ERROR_TIMEOUT Occurrences"),
)
TURN_SPEED_MODES = (
    ("averageSpeedDuringTurns", "Turning"),
    ("averageSpeedDuringStraightDriving", "Straight Driving"),
)


def create_data_quality_rows(quality_report: JsonObject) -> list[dict[str, str]]:
    total_rows = cast(int, quality_report["totalRows"])
    valid_rows = cast(int, quality_report["validRows"])
    invalid_rows = cast(int, quality_report["invalidRows"])
    outlier_rows = cast(int, quality_report["outlierRows"])

    return [
        {
            "label": "Total Rows",
            "value": format_count(total_rows),
            "detail": "All rows imported from the measurement CSV.",
        },
        {
            "label": "Valid Rows",
            "value": format_count(valid_rows),
            "detail": "Rows that passed validation and can be considered for analysis.",
        },
        {
            "label": "Invalid Rows",
            "value": format_count(invalid_rows),
            "detail": "Rows with missing, non-numeric, out-of-range, or sensor-error values.",
        },
        {
            "label": "Outlier Rows",
            "value": format_count(outlier_rows),
            "detail": "Valid rows marked as statistically unusual by the quality analysis.",
        },
    ]


def create_validation_error_dataframe(quality_report: JsonObject) -> pd.DataFrame:
    invalid_by_rule = cast(dict[str, int], quality_report["invalidByRule"])
    return pd.DataFrame(
        [
            {"Issue Type": label, "Count": invalid_by_rule.get(rule_key, 0)}
            for rule_key, label in VALIDATION_RULE_LABELS
        ]
    )


def create_missing_fields_dataframe(quality_report: JsonObject) -> pd.DataFrame:
    missing_by_field = cast(dict[str, int], quality_report["missingByField"])
    missing_field_rows = [
        {"Field": field_name.replace("_", " ").title(), "Count": count}
        for field_name, count in missing_by_field.items()
    ]

    return pd.DataFrame(missing_field_rows)


def create_session_information_rows(session: JsonObject) -> list[dict[str, object]]:
    metadata = cast(JsonObject, session["metadata"])
    sensors_active = metadata.get("sensors_active", [])
    sensors_active_text = (
        ", ".join(str(sensor_name) for sensor_name in sensors_active)
        if isinstance(sensors_active, list)
        else ""
    )

    return [
        {"Field": "Session ID", "Value": session["sessionId"]},
        {"Field": "Vehicle ID", "Value": session["vehicleId"]},
        {"Field": "Driver ID", "Value": session["driverId"]},
        {"Field": "Recording Date", "Value": session["recordingDate"]},
        {"Field": "Test Location", "Value": metadata.get("test_location", "")},
        {"Field": "Start Time UTC", "Value": metadata.get("start_time_utc", "")},
        {"Field": "End Time UTC", "Value": metadata.get("end_time_utc", "")},
        {"Field": "Sample Rate Hz", "Value": metadata.get("sample_rate_hz", "")},
        {"Field": "Hardware Version", "Value": metadata.get("hardware_version", "")},
        {"Field": "Firmware Version", "Value": metadata.get("firmware_version", "")},
        {"Field": "Sensors Active", "Value": sensors_active_text},
        {"Field": "Notes", "Value": metadata.get("notes", "")},
    ]


def _create_filtered_measurements_dataframe(
    measurements: list[JsonObject],
    *,
    reverse_state: bool | None = None,
) -> pd.DataFrame:
    measurements_dataframe = pd.DataFrame(measurements)
    if measurements_dataframe.empty:
        return pd.DataFrame()

    measurement_mask = (
        measurements_dataframe["isValid"].eq(True)
        & measurements_dataframe["isOutlier"].eq(False)
    )
    if reverse_state is not None:
        measurement_mask &= measurements_dataframe["reverseState"].eq(reverse_state)

    filtered_dataframe = measurements_dataframe.loc[
        measurement_mask,
        MEASUREMENT_COLUMNS,
    ].dropna().copy()
    if filtered_dataframe.empty:
        return pd.DataFrame()

    for column_name in MEASUREMENT_COLUMNS:
        filtered_dataframe[column_name] = pd.to_numeric(
            filtered_dataframe[column_name],
            errors="coerce",
        )

    return filtered_dataframe.dropna().sort_values("rowIndex")


def create_average_speed_by_steering_bucket_dataframe(
    measurements: list[JsonObject],
) -> pd.DataFrame:
    forward_dataframe = _create_filtered_measurements_dataframe(
        measurements,
        reverse_state=False,
    )
    if forward_dataframe.empty:
        return pd.DataFrame()

    bucket_dataframe = forward_dataframe[["speed", "wheelAngle"]].copy()
    bucket_dataframe["absoluteWheelAngle"] = bucket_dataframe["wheelAngle"].abs()
    bucket_dataframe["Steering Bucket"] = pd.cut(
        bucket_dataframe["absoluteWheelAngle"],
        bins=STEERING_BUCKET_BINS,
        labels=STEERING_BUCKET_LABELS,
        right=False,
    )

    grouped_buckets = bucket_dataframe.groupby("Steering Bucket", observed=False).agg(
        avg_speed=("speed", "mean"),
        measurement_count=("speed", "count"),
    )

    return pd.DataFrame(
        {
            "Steering Bucket": STEERING_BUCKET_LABELS,
            "Avg Speed": [
                grouped_buckets.loc[bucket_label, "avg_speed"]
                if bucket_label in grouped_buckets.index
                else None
                for bucket_label in STEERING_BUCKET_LABELS
            ],
            "Measurement Count": [
                int(grouped_buckets.loc[bucket_label, "measurement_count"])
                if bucket_label in grouped_buckets.index
                else 0
                for bucket_label in STEERING_BUCKET_LABELS
            ],
        }
    )


def create_steering_bucket_summary_table(bucket_dataframe: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Steering Bucket": bucket_dataframe["Steering Bucket"],
            "Avg Speed": [
                format_float_metric(cast(float | None, average_speed))
                if pd.notna(average_speed)
                else "N/A"
                for average_speed in bucket_dataframe["Avg Speed"]
            ],
            "Count": [
                format_count(measurement_count)
                for measurement_count in bucket_dataframe["Measurement Count"]
            ],
        }
    )


def _weighted_average_speed_for_buckets(
    bucket_dataframe: pd.DataFrame,
    bucket_labels: tuple[str, ...],
) -> float | None:
    populated_buckets = bucket_dataframe[
        bucket_dataframe["Steering Bucket"].isin(bucket_labels)
        & bucket_dataframe["Measurement Count"].gt(0)
    ]
    if populated_buckets.empty:
        return None

    total_measurement_count = int(populated_buckets["Measurement Count"].sum())
    if total_measurement_count == 0:
        return None

    weighted_speed_sum = (
        populated_buckets["Avg Speed"] * populated_buckets["Measurement Count"]
    ).sum()

    return float(weighted_speed_sum / total_measurement_count)


def describe_average_speed_by_steering_insight(bucket_dataframe: pd.DataFrame) -> str:
    populated_bucket_count = int(bucket_dataframe["Measurement Count"].gt(0).sum())
    if populated_bucket_count < 2:
        return "Not enough data across steering ranges to summarize speed behavior."

    low_average_speed = _weighted_average_speed_for_buckets(
        bucket_dataframe,
        LOW_STEERING_BUCKETS,
    )
    high_average_speed = _weighted_average_speed_for_buckets(
        bucket_dataframe,
        HIGH_STEERING_BUCKETS,
    )

    if low_average_speed is None or high_average_speed is None or low_average_speed == 0:
        return "Not enough data across steering ranges to summarize speed behavior."

    speed_difference_percentage = abs(high_average_speed - low_average_speed) / low_average_speed

    if speed_difference_percentage < STEERING_SPEED_CHANGE_THRESHOLD:
        return "Average speed remained relatively stable across steering ranges."

    if high_average_speed < low_average_speed:
        return (
            "Average speed decreased as steering intensity increased, suggesting the driver "
            "slowed down during stronger steering maneuvers."
        )

    return "Average speed increased as steering intensity increased."


TURN_SPEED_MODES = (
    ("averageSpeedDuringTurns", "Turning"),
    ("averageSpeedDuringStraightDriving", "Straight Driving"),
)
DRIVING_METRIC_GROUPS = (
    {
        "title": "Driving Stability",
        "caption_key": "speedSteeringCorrelationCaption",
        "metrics": (
            ("Steering Variability", "steeringVariability", "float", "Measures how stable steering behavior was. Higher values indicate more corrections."),
            ("Speed Variability", "speedVariability", "float", "Measures how consistent vehicle speed was. Higher values indicate larger fluctuations."),
            ("Steering-Speed Correlation", "speedSteeringCorrelation", "float2", "Shows whether steering intensity is associated with speed changes."),
        ),
    },
    {
        "title": "Turning Behavior",
        "metrics": (
            ("Turning Measurements", "totalTurns", "count", "Number of analyzed measurements where steering angle exceeded the turning threshold."),
            ("Sharp Turn Measurements", "sharpTurns", "count", "Number of analyzed measurements where steering angle exceeded the sharp-turn threshold."),
            ("Avg Speed During Turns", "averageSpeedDuringTurns", "float", "Average speed across measurements classified as turning."),
            ("Avg Speed Straight", "averageSpeedDuringStraightDriving", "float", "Average speed across measurements classified as straight driving."),
        ),
    },
    {
        "title": "Reverse Driving",
        "metrics": (
            ("Reverse Percentage", "reversePercentage", "percent", "Share of usable measurements recorded while reversing."),
            ("Avg Reverse Speed", "averageReverseSpeed", "float", "Average speed during valid, non-outlier reverse driving."),
        ),
    },
)


def _format_driving_metric(value: object, value_type: str) -> str:
    if value_type == "count":
        return format_count(cast(int, value or 0))
    if value_type == "percent":
        return format_percentage(cast(float, value or 0))
    if value_type == "float2":
        return format_float_metric(cast(float | None, value), decimals=2)

    return format_float_metric(cast(float | None, value))


def create_driving_behavior_metric_groups(analytics: JsonObject) -> list[dict[str, object]]:
    driving_behavior = cast(JsonObject, analytics["drivingBehavior"])
    metric_groups: list[dict[str, object]] = []

    for metric_group_config in DRIVING_METRIC_GROUPS:
        metric_group: dict[str, object] = {
            "title": metric_group_config["title"],
            "metrics": [
                {
                    "label": label,
                    "value": _format_driving_metric(driving_behavior.get(key), value_type),
                    "help": help_text,
                }
                for label, key, value_type, help_text in metric_group_config["metrics"]
            ],
        }
        caption_key = metric_group_config.get("caption_key")
        if caption_key:
            metric_group["caption"] = driving_behavior[caption_key]

        metric_groups.append(metric_group)

    return metric_groups


def create_turn_speed_dataframe(analytics: JsonObject) -> pd.DataFrame:
    driving_behavior = cast(JsonObject, analytics["drivingBehavior"])
    speed_rows = [
        {
            "Driving Mode": driving_mode_label,
            "Average Speed": cast(float, driving_behavior[summary_key]),
        }
        for summary_key, driving_mode_label in TURN_SPEED_MODES
        if driving_behavior.get(summary_key) is not None
    ]

    return pd.DataFrame(speed_rows)


def create_chart_dataframe(
    measurements: list[JsonObject],
    measurement_field: str,
) -> pd.DataFrame:
    chart_dataframe = _create_filtered_measurements_dataframe(measurements)
    if chart_dataframe.empty:
        return pd.DataFrame()

    return chart_dataframe[["rowIndex", measurement_field]]


def create_valid_measurements_dataframe(measurements: list[JsonObject]) -> pd.DataFrame:
    measurements_dataframe = pd.DataFrame(measurements)
    if measurements_dataframe.empty:
        return pd.DataFrame()

    valid_measurements = measurements_dataframe[
        measurements_dataframe["isValid"].eq(True)
        & measurements_dataframe["isOutlier"].eq(False)
    ]
    if valid_measurements.empty:
        return pd.DataFrame()

    return valid_measurements[
        ["rowIndex", "timestamp", "speed", "wheelAngle", "reverseState"]
    ].rename(
        columns={
            "rowIndex": "Row Index",
            "timestamp": "Timestamp",
            "speed": "Speed",
            "wheelAngle": "Wheel Angle",
            "reverseState": "Reverse State",
        }
    )


def create_problem_rows_display_dataframe(measurements: list[JsonObject]) -> pd.DataFrame:
    problem_rows = [
        measurement
        for measurement in measurements
        if measurement.get("isValid") is False or measurement.get("isOutlier") is True
    ]
    if not problem_rows:
        return pd.DataFrame()

    display_rows = [
        {
            "Row Index": measurement["rowIndex"],
            "Validation Errors": format_validation_error_messages(
                measurement.get("validationErrors")
            ),
            "Raw Timestamp": format_display_value(measurement.get("rawTimestamp")),
            "Raw Speed": format_display_value(measurement.get("rawSpeed")),
            "Raw Wheel Angle": format_display_value(measurement.get("rawWheelAngle")),
            "Raw Reverse State": format_display_value(measurement.get("rawReverseState")),
            "Timestamp": format_display_value(measurement.get("timestamp")),
            "Speed": format_display_value(measurement.get("speed")),
            "Wheel Angle": format_display_value(measurement.get("wheelAngle")),
            "Reverse State": format_display_value(measurement.get("reverseState")),
            "Is Outlier": format_display_value(measurement.get("isOutlier")),
        }
        for measurement in problem_rows
    ]

    return pd.DataFrame(display_rows)
