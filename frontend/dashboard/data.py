import pandas as pd

from dashboard.helpers import (
    JsonObject,
    describe_quality_score,
    format_count,
    format_percentage,
    get_analyzed_measurement_count,
    get_json_object,
    get_number,
)


STATISTIC_NAMES = ["min", "max", "mean", "median", "stdDev", "p5", "p95"]
STATISTIC_DESCRIPTIONS = {
    "min": "Lowest value found in valid non-outlier measurements.",
    "max": "Highest value found in valid non-outlier measurements.",
    "mean": "Average value across valid non-outlier measurements.",
    "median": "Middle value, useful when the data contains extreme values.",
    "stdDev": "How much values usually vary from the average.",
    "p5": "5th percentile. 5% of values are below this number.",
    "p95": "95th percentile. 95% of values are below this number.",
}


def create_statistics_rows(statistics: JsonObject) -> list[JsonObject]:
    return [
        {
            "metric": statistic_name,
            "value": statistics.get(statistic_name),
            "meaning": STATISTIC_DESCRIPTIONS[statistic_name],
        }
        for statistic_name in STATISTIC_NAMES
    ]


def create_executive_summary_rows(
    quality_report: JsonObject,
    analytics: JsonObject,
) -> list[dict[str, str]]:
    speed_statistics = get_json_object(analytics, "speed")
    wheel_angle_statistics = get_json_object(analytics, "wheelAngle")
    reverse_state_summary = get_json_object(analytics, "reverseStateSummary")

    quality_score = get_number(quality_report, "qualityScore")
    total_rows = get_number(quality_report, "totalRows")
    invalid_rows = get_number(quality_report, "invalidRows")
    outlier_rows = get_number(quality_report, "outlierRows")
    forward_count = get_number(reverse_state_summary, "forwardCount")
    reverse_count = get_number(reverse_state_summary, "reverseCount")
    analyzed_measurement_count = get_analyzed_measurement_count(analytics)
    reverse_percentage = (
        reverse_count / analyzed_measurement_count
        if analyzed_measurement_count > 0
        else 0
    )
    max_speed = get_number(speed_statistics, "max")
    min_wheel_angle = get_number(wheel_angle_statistics, "min")
    max_wheel_angle = get_number(wheel_angle_statistics, "max")

    return [
        {
            "label": "Quality Score",
            "value": format_percentage(quality_score),
            "detail": describe_quality_score(quality_score),
        },
        {
            "label": "Validation Issues",
            "value": format_count(invalid_rows),
            "detail": (
                "Rows that failed required, numeric, range, or sensor-marker checks "
                f"out of {format_count(total_rows)} imported rows."
            ),
        },
        {
            "label": "Outliers Excluded",
            "value": format_count(outlier_rows),
            "detail": "Valid rows with unusual sensor values. These are excluded from trend charts.",
        },
        {
            "label": "Peak Speed",
            "value": f"{max_speed:.1f}",
            "detail": "Highest non-outlier speed used in the analytics calculations.",
        },
        {
            "label": "Reverse Driving",
            "value": format_percentage(reverse_percentage),
            "detail": (
                f"{format_count(reverse_count)} reverse measurements and "
                f"{format_count(forward_count)} forward measurements were analyzed."
            ),
        },
        {
            "label": "Steering Range",
            "value": f"{min_wheel_angle:.1f} to {max_wheel_angle:.1f}",
            "detail": "Observed wheel-angle range after invalid rows and outliers were removed.",
        },
    ]


def create_quality_breakdown_dataframe(quality_report: JsonObject) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Status": "Valid Rows", "Count": get_number(quality_report, "validRows")},
            {"Status": "Invalid Rows", "Count": get_number(quality_report, "invalidRows")},
            {"Status": "Outlier Rows", "Count": get_number(quality_report, "outlierRows")},
        ]
    )


def create_validation_error_dataframe(quality_report: JsonObject) -> pd.DataFrame:
    invalid_by_rule = get_json_object(quality_report, "invalidByRule")
    validation_error_rows = [
        {"Rule": rule_name, "Count": count}
        for rule_name, count in invalid_by_rule.items()
    ]

    return pd.DataFrame(validation_error_rows)


def create_reverse_state_dataframe(analytics: JsonObject) -> pd.DataFrame:
    reverse_state_summary = get_json_object(analytics, "reverseStateSummary")

    return pd.DataFrame(
        [
            {"State": "Forward", "Count": get_number(reverse_state_summary, "forwardCount")},
            {"State": "Reverse", "Count": get_number(reverse_state_summary, "reverseCount")},
        ]
    )


def create_missing_fields_dataframe(quality_report: JsonObject) -> pd.DataFrame:
    missing_by_field = get_json_object(quality_report, "missingByField")
    missing_field_rows = [
        {"Field": field_name.replace("_", " ").title(), "Count": count}
        for field_name, count in missing_by_field.items()
    ]

    return pd.DataFrame(missing_field_rows)


def create_chart_dataframe(
    measurements: list[JsonObject],
    measurement_field: str,
) -> pd.DataFrame:
    measurements_dataframe = pd.DataFrame(measurements)
    if measurements_dataframe.empty:
        return pd.DataFrame()

    required_chart_fields = {"rowIndex", measurement_field, "isValid", "isOutlier"}
    if not required_chart_fields.issubset(measurements_dataframe.columns):
        return pd.DataFrame()

    chart_dataframe = measurements_dataframe[
        measurements_dataframe["isValid"].eq(True)
        & measurements_dataframe["isOutlier"].eq(False)
    ][["rowIndex", measurement_field]].dropna()
    if chart_dataframe.empty:
        return pd.DataFrame()

    chart_dataframe["rowIndex"] = pd.to_numeric(
        chart_dataframe["rowIndex"],
        errors="coerce",
    )
    chart_dataframe[measurement_field] = pd.to_numeric(
        chart_dataframe[measurement_field],
        errors="coerce",
    )
    chart_dataframe = chart_dataframe.dropna().sort_values("rowIndex")

    return chart_dataframe


def create_problem_rows_dataframe(measurements: list[JsonObject]) -> pd.DataFrame:
    measurements_dataframe = pd.DataFrame(measurements)
    if measurements_dataframe.empty:
        return pd.DataFrame()

    required_problem_fields = {"isValid", "isOutlier"}
    if not required_problem_fields.issubset(measurements_dataframe.columns):
        return pd.DataFrame()

    return measurements_dataframe[
        measurements_dataframe["isValid"].eq(False)
        | measurements_dataframe["isOutlier"].eq(True)
    ]
