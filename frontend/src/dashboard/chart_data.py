"""Map API analytics responses to chart and summary table dataframes."""

from typing import cast

import pandas as pd

from dashboard.helpers import JsonObject


FORWARD_REVERSE_COMPARISON_METRICS = (
    ("speedMean", "averageSpeed", "Average Speed"),
    ("steeringVariability", "steeringVariability", "Steering Variability"),
)


def mean_from_timeline(forward_driving: JsonObject, field: str) -> float | None:
    timeline = cast(list[JsonObject], forward_driving.get("timeline", []))
    if not timeline:
        return None

    values = [cast(float, timeline_point[field]) for timeline_point in timeline]
    return sum(values) / len(values)


def create_timeline_chart_dataframe(
    forward_driving: JsonObject,
    measurement_field: str,
) -> pd.DataFrame:
    timeline = cast(list[JsonObject], forward_driving.get("timeline", []))
    if not timeline:
        return pd.DataFrame()

    return pd.DataFrame(
        [
            {
                "rowIndex": timeline_point["rowIndex"],
                measurement_field: timeline_point[measurement_field],
            }
            for timeline_point in timeline
        ]
    )


def create_steering_bucket_chart_dataframe(forward_driving: JsonObject) -> pd.DataFrame:
    steering_bucket_analysis = cast(
        JsonObject,
        forward_driving.get("steeringBucketAnalysis", {}),
    )
    buckets = cast(list[JsonObject], steering_bucket_analysis.get("buckets", []))
    if not buckets:
        return pd.DataFrame()

    return pd.DataFrame(
        [
            {
                "Steering Intensity Bucket": bucket["label"],
                "Average Speed": bucket["averageSpeed"],
            }
            for bucket in buckets
            if bucket.get("averageSpeed") is not None
        ]
    )


def create_forward_reverse_comparison_dataframe(analytics: JsonObject) -> pd.DataFrame:
    forward_driving = cast(JsonObject, analytics["forwardDriving"])
    reverse_driving = cast(JsonObject, analytics["reverseDriving"])
    comparison_rows: list[dict[str, object]] = []

    for forward_metric_key, reverse_metric_key, metric_label in FORWARD_REVERSE_COMPARISON_METRICS:
        forward_value = forward_driving.get(forward_metric_key)
        if forward_value is not None:
            comparison_rows.append(
                {
                    "Metric": metric_label,
                    "Direction": "Forward",
                    "Value": forward_value,
                }
            )

        reverse_value = reverse_driving.get(reverse_metric_key)
        if reverse_value is not None:
            comparison_rows.append(
                {
                    "Metric": metric_label,
                    "Direction": "Reverse",
                    "Value": reverse_value,
                }
            )

    if not comparison_rows:
        return pd.DataFrame()

    return pd.DataFrame(comparison_rows)
