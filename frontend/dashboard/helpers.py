from collections.abc import Mapping
from typing import cast


JsonObject = dict[str, object]


def get_number(source: JsonObject, key: str) -> float:
    value = source.get(key)
    if isinstance(value, bool):
        return 0
    if isinstance(value, int | float):
        return float(value)

    return 0


def get_json_object(source: JsonObject, key: str) -> JsonObject:
    value = source.get(key)
    if isinstance(value, Mapping):
        return cast(JsonObject, dict(value))

    return {}


def get_json_objects(source: JsonObject, key: str) -> list[JsonObject]:
    value = source.get(key)
    if not isinstance(value, list):
        return []

    return [
        cast(JsonObject, measurement)
        for measurement in value
        if isinstance(measurement, Mapping)
    ]


def format_percentage(value: float) -> str:
    return f"{value * 100:.0f}%"


def format_count(value: float) -> str:
    return f"{int(value):,}"


def get_analyzed_measurement_count(analytics: JsonObject) -> float:
    analyzed_measurement_count = get_number(analytics, "analyzedMeasurementCount")
    if analyzed_measurement_count > 0:
        return analyzed_measurement_count

    reverse_state_summary = get_json_object(analytics, "reverseStateSummary")
    return (
        get_number(reverse_state_summary, "forwardCount")
        + get_number(reverse_state_summary, "reverseCount")
    )


def describe_quality_score(quality_score: float) -> str:
    if quality_score >= 0.9:
        return "Excellent data quality. Almost all rows are usable for analysis."
    if quality_score >= 0.75:
        return "Good data quality. Most rows are usable, with some issues to review."
    if quality_score >= 0.5:
        return "Moderate data quality. Review validation failures and outliers before relying on trends."

    return "Low data quality. The session needs investigation before using it for decisions."
