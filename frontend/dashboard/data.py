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


VALIDATION_RULE_LABELS = (
    ("required", "Missing Fields"),
    ("numeric", "Numeric Errors"),
    ("range", "Range Errors"),
    ("invalid_marker", "ERROR_TIMEOUT Occurrences"),
)
FORWARD_DRIVING_METRIC_GROUPS = (
    {
        "title": "Driving Stability",
        "caption_key": "speedSteeringCorrelationCaption",
        "metrics": (
            ("Steering Variability", "steeringVariability", "float", "Measures how stable forward steering behavior was. Higher values indicate more corrections."),
            ("Speed Variability", "speedVariability", "float", "Measures how consistent forward vehicle speed was. Higher values indicate larger fluctuations."),
            ("Steering-Speed Correlation", "speedSteeringCorrelation", "float2", "Shows whether steering intensity is associated with speed changes during forward driving."),
        ),
    },
    {
        "title": "Turning Behavior",
        "metrics": (
            ("Turning Measurements", "totalTurns", "count", "Number of forward measurements where steering angle exceeded the turning threshold."),
            ("Sharp Turn Measurements", "sharpTurns", "count", "Number of forward measurements where steering angle exceeded the sharp-turn threshold."),
            ("Avg Speed During Turns", "averageSpeedDuringTurns", "float", "Average forward speed across measurements classified as turning."),
            ("Avg Speed Straight", "averageSpeedDuringStraightDriving", "float", "Average forward speed across measurements classified as straight driving."),
        ),
    },
)
REVERSE_DRIVING_METRIC_GROUPS = (
    {
        "title": "Reverse Context",
        "metrics": (
            ("Reverse Measurements", "measurementCount", "count", "Number of analyzed measurements recorded while reversing."),
            ("Reverse Percentage", "percentage", "percent", "Share of usable measurements recorded while reversing."),
            ("Avg Reverse Speed", "averageSpeed", "float", "Average speed during valid, non-outlier reverse driving."),
            ("Steering Variability", "steeringVariability", "float", "Measures how much steering angle varied during reverse driving."),
        ),
    },
)


def create_data_quality_rows(quality_report: JsonObject) -> list[dict[str, str]]:
    total_row_count = cast(int, quality_report["totalRows"])
    valid_row_count = cast(int, quality_report["validRows"])
    invalid_row_count = cast(int, quality_report["invalidRows"])
    outlier_row_count = cast(int, quality_report["outlierRows"])

    return [
        {
            "label": "Total Rows",
            "value": format_count(total_row_count),
            "detail": "All rows imported from the measurement CSV.",
        },
        {
            "label": "Valid Rows",
            "value": format_count(valid_row_count),
            "detail": "Rows that passed validation and can be considered for analysis.",
        },
        {
            "label": "Invalid Rows",
            "value": format_count(invalid_row_count),
            "detail": "Rows with missing, non-numeric, out-of-range, or sensor-error values.",
        },
        {
            "label": "Outlier Rows",
            "value": format_count(outlier_row_count),
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
    missing_field_table_rows = [
        {"Field": field_name.replace("_", " ").title(), "Count": count}
        for field_name, count in missing_by_field.items()
    ]

    return pd.DataFrame(missing_field_table_rows)


def create_session_information_rows(session: JsonObject) -> list[dict[str, object]]:
    metadata = cast(JsonObject, session["metadata"])
    sensors_active = metadata.get("sensors_active", [])
    sensors_active_text = (
        ", ".join(str(sensor_name) for sensor_name in sensors_active)
        if isinstance(sensors_active, list)
        else ""
    )

    return [
        {"Field": "Session ID", "Value": metadata.get("session_id", "")},
        {"Field": "Vehicle ID", "Value": metadata.get("vehicle_id", "")},
        {"Field": "Driver ID", "Value": metadata.get("driver_id", "")},
        {"Field": "Recording Date", "Value": metadata.get("recording_date", "")},
        {"Field": "Test Location", "Value": metadata.get("test_location", "")},
        {"Field": "Start Time UTC", "Value": metadata.get("start_time_utc", "")},
        {"Field": "End Time UTC", "Value": metadata.get("end_time_utc", "")},
        {"Field": "Sample Rate Hz", "Value": metadata.get("sample_rate_hz", "")},
        {"Field": "Hardware Version", "Value": metadata.get("hardware_version", "")},
        {"Field": "Firmware Version", "Value": metadata.get("firmware_version", "")},
        {"Field": "Sensors Active", "Value": sensors_active_text},
        {"Field": "Notes", "Value": metadata.get("notes", "")},
    ]


def _format_driving_metric(value: object, value_type: str) -> str:
    if value_type == "count":
        return format_count(cast(int, value or 0))
    if value_type == "percent":
        return format_percentage(cast(float, value or 0))
    if value_type == "float2":
        return format_float_metric(cast(float | None, value), decimals=2)

    return format_float_metric(cast(float | None, value))


def _build_metric_groups(
    driving_data: JsonObject,
    metric_group_configs: tuple[dict[str, object], ...],
) -> list[dict[str, object]]:
    metric_groups: list[dict[str, object]] = []

    for metric_group_config in metric_group_configs:
        metric_group: dict[str, object] = {
            "title": metric_group_config["title"],
            "metrics": [
                {
                    "label": label,
                    "value": _format_driving_metric(driving_data.get(key), value_type),
                    "help": help_text,
                }
                for label, key, value_type, help_text in metric_group_config["metrics"]
            ],
        }
        caption_key = metric_group_config.get("caption_key")
        if caption_key:
            metric_group["caption"] = driving_data[caption_key]

        metric_groups.append(metric_group)

    return metric_groups


def create_forward_driving_metric_groups(analytics: JsonObject) -> list[dict[str, object]]:
    return _build_metric_groups(
        cast(JsonObject, analytics["forwardDriving"]),
        FORWARD_DRIVING_METRIC_GROUPS,
    )


def create_reverse_driving_metric_groups(analytics: JsonObject) -> list[dict[str, object]]:
    return _build_metric_groups(
        cast(JsonObject, analytics["reverseDriving"]),
        REVERSE_DRIVING_METRIC_GROUPS,
    )


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
    problem_measurements = [
        measurement
        for measurement in measurements
        if measurement.get("isValid") is False or measurement.get("isOutlier") is True
    ]
    if not problem_measurements:
        return pd.DataFrame()

    problem_row_display_records = [
        {
            "Row Index": measurement["rowIndex"],
            "Validation Errors": format_validation_error_messages(
                measurement.get("validationErrors")
            ),
            "Timestamp": format_display_value(measurement.get("timestamp")),
            "Speed": format_display_value(measurement.get("speed")),
            "Wheel Angle": format_display_value(measurement.get("wheelAngle")),
            "Reverse State": format_display_value(measurement.get("reverseState")),
            "Is Outlier": format_display_value(measurement.get("isOutlier")),
        }
        for measurement in problem_measurements
    ]

    return pd.DataFrame(problem_row_display_records)
