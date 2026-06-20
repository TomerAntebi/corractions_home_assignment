"""
Validation logic for normalized measurement rows.

Validation reports malformed or suspicious inputs without mutating the normalized
measurement. Downstream quality analysis and analytics decide how to use the
validated rows.
"""

from validation.models import (
    ABSENT_VALUE_MARKERS,
    FIELDS_CHECKED_FOR_SENSOR_ERROR,
    NormalizedMeasurement,
    NUMERIC_RANGE_RULES,
    PARSED_NUMERIC_FIELDS,
    REQUIRED_ANALYTICS_FIELDS,
    RULE_INVALID_MARKER,
    RULE_NUMERIC,
    RULE_RANGE,
    RULE_REQUIRED,
    SENSOR_ERROR_MARKER,
    ValidationIssue,
    ValidationResult,
)


class MeasurementValidator:
    def validate_measurement(
        self,
        measurement: NormalizedMeasurement,
    ) -> ValidationResult:
        validation_issues: list[ValidationIssue] = []
        flagged_fields: set[str] = set()

        self._collect_sensor_error_issues(measurement, validation_issues, flagged_fields)
        self._collect_non_numeric_issues(measurement, validation_issues, flagged_fields)
        self._collect_missing_required_issues(measurement, validation_issues, flagged_fields)
        self._collect_out_of_range_issues(measurement, validation_issues, flagged_fields)

        return ValidationResult(
            measurement=measurement,
            issues=validation_issues,
            is_valid=len(validation_issues) == 0,
        )

    def _collect_sensor_error_issues(
        self,
        measurement: NormalizedMeasurement,
        validation_issues: list[ValidationIssue],
        flagged_fields: set[str],
    ) -> None:
        # ERROR_TIMEOUT is the most specific signal, so it wins over generic checks.
        for field_name in FIELDS_CHECKED_FOR_SENSOR_ERROR:
            raw_field_value = getattr(measurement, f"raw_{field_name}")
            if str(raw_field_value).strip() != SENSOR_ERROR_MARKER:
                continue

            self._record_issue(
                validation_issues,
                flagged_fields,
                field_name=field_name,
                rule=RULE_INVALID_MARKER,
                message=f"{field_name} contains ERROR_TIMEOUT",
                raw_value=SENSOR_ERROR_MARKER,
            )

    def _collect_non_numeric_issues(
        self,
        measurement: NormalizedMeasurement,
        validation_issues: list[ValidationIssue],
        flagged_fields: set[str],
    ) -> None:
        for field_name in PARSED_NUMERIC_FIELDS:
            if field_name in flagged_fields:
                continue

            numeric_value = getattr(measurement, field_name)
            raw_field_value = getattr(measurement, f"raw_{field_name}")
            if numeric_value is None and not self._raw_value_is_absent(raw_field_value):
                self._record_issue(
                    validation_issues,
                    flagged_fields,
                    field_name=field_name,
                    rule=RULE_NUMERIC,
                    message=f"{field_name} must be numeric",
                    raw_value=None if raw_field_value is None else str(raw_field_value),
                )

    def _collect_missing_required_issues(
        self,
        measurement: NormalizedMeasurement,
        validation_issues: list[ValidationIssue],
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
            self._record_issue(
                validation_issues,
                flagged_fields,
                field_name=field_name,
                rule=RULE_REQUIRED,
                message=f"{field_name} is required",
                raw_value=None if raw_field_value is None else str(raw_field_value),
            )

    def _collect_out_of_range_issues(
        self,
        measurement: NormalizedMeasurement,
        validation_issues: list[ValidationIssue],
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
            self._record_issue(
                validation_issues,
                flagged_fields,
                field_name=field_name,
                rule=RULE_RANGE,
                message=(
                    f"{field_name} must be between "
                    f"{numeric_range_rule.minimum} and {numeric_range_rule.maximum}"
                ),
                raw_value=None if raw_field_value is None else str(raw_field_value),
            )

    def _record_issue(
        self,
        validation_issues: list[ValidationIssue],
        flagged_fields: set[str],
        *,
        field_name: str,
        rule: str,
        message: str,
        raw_value: str | None = None,
    ) -> None:
        validation_issues.append(
            ValidationIssue(
                field=field_name,
                rule=rule,
                message=message,
                raw_value=raw_value,
            )
        )
        flagged_fields.add(field_name)

    def _raw_value_is_absent(self, raw_value: object | None) -> bool:
        if raw_value is None:
            return True

        return str(raw_value).strip() in ABSENT_VALUE_MARKERS
