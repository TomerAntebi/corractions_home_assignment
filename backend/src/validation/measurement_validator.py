"""
Validation logic for normalized measurement rows.

Validation reports malformed or suspicious inputs without mutating the normalized
measurement. Downstream quality analysis and analytics decide how to use the
validated rows.
"""

from validation.models import (
    ABSENT_VALUE_MARKERS,
    FIELDS_CHECKED_FOR_SENSOR_ERROR,
    MeasurementRow,
    NUMERIC_RANGE_RULES,
    PARSED_NUMERIC_FIELDS,
    REQUIRED_ANALYTICS_FIELDS,
    RULE_INVALID_MARKER,
    RULE_NUMERIC,
    RULE_RANGE,
    RULE_REQUIRED,
    SENSOR_ERROR_MARKER,
    MeasurementValidationError,
)


def validate_measurement(measurement: MeasurementRow) -> MeasurementRow:
    validation_errors: list[MeasurementValidationError] = []
    flagged_fields: set[str] = set()

    collect_sensor_error_issues(measurement, validation_errors, flagged_fields)
    collect_non_numeric_issues(measurement, validation_errors, flagged_fields)
    collect_missing_required_issues(measurement, validation_errors, flagged_fields)
    collect_out_of_range_issues(measurement, validation_errors, flagged_fields)

    is_valid = len(validation_errors) == 0

    return measurement.model_copy(
        update={
            "validation_errors": validation_errors,
            "is_valid": is_valid,
        }
    )


def collect_sensor_error_issues(
    measurement: MeasurementRow,
    validation_errors: list[MeasurementValidationError],
    flagged_fields: set[str],
) -> None:
    # ERROR_TIMEOUT is the most specific signal, so it wins over generic checks.
    for field_name in FIELDS_CHECKED_FOR_SENSOR_ERROR:
        raw_field_value = getattr(measurement, f"raw_{field_name}")
        if str(raw_field_value).strip() != SENSOR_ERROR_MARKER:
            continue

        validation_error = create_validation_error(
            field_name=field_name,
            rule=RULE_INVALID_MARKER,
            message=f"{field_name} contains ERROR_TIMEOUT",
            raw_value=SENSOR_ERROR_MARKER,
        )
        record_validation_error(validation_errors, flagged_fields, validation_error)


def collect_non_numeric_issues(
    measurement: MeasurementRow,
    validation_errors: list[MeasurementValidationError],
    flagged_fields: set[str],
) -> None:
    for field_name in PARSED_NUMERIC_FIELDS:
        if field_name in flagged_fields:
            continue

        numeric_value = getattr(measurement, field_name)
        raw_field_value = getattr(measurement, f"raw_{field_name}")
        if numeric_value is None and not raw_value_is_absent(raw_field_value):
            validation_error = create_validation_error(
                field_name=field_name,
                rule=RULE_NUMERIC,
                message=f"{field_name} must be numeric",
                raw_value=raw_field_value,
            )
            record_validation_error(validation_errors, flagged_fields, validation_error)


def collect_missing_required_issues(
    measurement: MeasurementRow,
    validation_errors: list[MeasurementValidationError],
    flagged_fields: set[str],
) -> None:
    # Required fields are the minimum data needed for session analytics.
    for field_name in REQUIRED_ANALYTICS_FIELDS:
        if field_name in flagged_fields:
            continue

        field_value = getattr(measurement, field_name)
        if field_value is not None:
            continue

        raw_field_value = getattr(measurement, f"raw_{field_name}")
        validation_error = create_validation_error(
            field_name=field_name,
            rule=RULE_REQUIRED,
            message=f"{field_name} is required",
            raw_value=raw_field_value,
        )
        record_validation_error(validation_errors, flagged_fields, validation_error)


def collect_out_of_range_issues(
    measurement: MeasurementRow,
    validation_errors: list[MeasurementValidationError],
    flagged_fields: set[str],
) -> None:
    for numeric_range_rule in NUMERIC_RANGE_RULES:
        field_name = numeric_range_rule.field_name
        if field_name in flagged_fields:
            continue

        numeric_value = getattr(measurement, field_name)
        if numeric_value is None:
            continue

        if numeric_range_rule.minimum <= numeric_value <= numeric_range_rule.maximum:
            continue

        raw_field_value = getattr(measurement, f"raw_{field_name}")
        validation_error = create_validation_error(
            field_name=field_name,
            rule=RULE_RANGE,
            message=(
                f"{field_name} must be between "
                f"{numeric_range_rule.minimum} and {numeric_range_rule.maximum}"
            ),
            raw_value=raw_field_value,
        )
        record_validation_error(validation_errors, flagged_fields, validation_error)


def create_validation_error(
    *,
    field_name: str,
    rule: str,
    message: str,
    raw_value: object | None = None,
) -> MeasurementValidationError:
    return MeasurementValidationError(
        field=field_name,
        rule=rule,
        message=message,
        raw_value=None if raw_value is None else str(raw_value),
    )


def record_validation_error(
    validation_errors: list[MeasurementValidationError],
    flagged_fields: set[str],
    validation_error: MeasurementValidationError,
) -> None:
    validation_errors.append(validation_error)
    flagged_fields.add(validation_error.field)


def raw_value_is_absent(raw_value: object | None) -> bool:
    if raw_value is None:
        return True

    return str(raw_value).strip() in ABSENT_VALUE_MARKERS
