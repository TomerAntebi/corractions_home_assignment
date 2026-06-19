"""
Validation logic for normalized measurement rows.

Validation reports malformed or suspicious inputs without mutating the normalized
measurement. Downstream quality analysis and analytics decide how to use the
validated rows.
"""

from validation.models import NormalizedMeasurement, ValidationIssue, ValidationResult


REQUIRED_FIELDS = ("timestamp", "speed", "wheel_angle")
MISSING_VALUE_MARKERS = {"", "null", "NaN"}
INVALID_MARKER = "ERROR_TIMEOUT"
SPEED_MIN = 0
SPEED_MAX = 200
WHEEL_ANGLE_MIN = -45
WHEEL_ANGLE_MAX = 45


class MeasurementValidator:
    def validate_measurement(
        self,
        measurement: NormalizedMeasurement,
    ) -> ValidationResult:
        validation_issues: list[ValidationIssue] = []
        fields_with_issues: set[str] = set()

        # ERROR_TIMEOUT is the most specific signal, so it wins over generic checks.
        for field_name, raw_field_value in (
            ("timestamp", measurement.raw_timestamp),
            ("speed", measurement.raw_speed),
            ("wheel_angle", measurement.raw_wheel_angle),
            ("reverse_state", measurement.raw_reverse_state),
        ):
            if str(raw_field_value).strip() == INVALID_MARKER:
                validation_issues.append(
                    ValidationIssue(
                        field=field_name,
                        rule="invalid_marker",
                        message=f"{field_name} contains ERROR_TIMEOUT",
                        raw_value=INVALID_MARKER,
                    )
                )
                fields_with_issues.add(field_name)

        for field_name, numeric_value, raw_field_value in (
            ("speed", measurement.speed, measurement.raw_speed),
            ("wheel_angle", measurement.wheel_angle, measurement.raw_wheel_angle),
        ):
            if field_name in fields_with_issues:
                continue
            if numeric_value is None and not self._is_missing_raw_value(raw_field_value):
                validation_issues.append(
                    ValidationIssue(
                        field=field_name,
                        rule="numeric",
                        message=f"{field_name} must be numeric",
                        raw_value=self._format_raw_value(raw_field_value),
                    )
                )
                fields_with_issues.add(field_name)

        # Required fields are the minimum data needed for session analytics.
        for field_name in REQUIRED_FIELDS:
            if field_name in fields_with_issues:
                continue
            field_value = getattr(measurement, field_name)
            if field_value is None:
                raw_field_value = getattr(measurement, f"raw_{field_name}")
                validation_issues.append(
                    ValidationIssue(
                        field=field_name,
                        rule="required",
                        message=f"{field_name} is required",
                        raw_value=self._format_raw_value(raw_field_value),
                    )
                )
                fields_with_issues.add(field_name)

        for field_name, numeric_value, raw_field_value, minimum_value, maximum_value in (
            ("speed", measurement.speed, measurement.raw_speed, SPEED_MIN, SPEED_MAX),
            (
                "wheel_angle",
                measurement.wheel_angle,
                measurement.raw_wheel_angle,
                WHEEL_ANGLE_MIN,
                WHEEL_ANGLE_MAX,
            ),
        ):
            if field_name in fields_with_issues or numeric_value is None:
                continue
            if not minimum_value <= numeric_value <= maximum_value:
                validation_issues.append(
                    ValidationIssue(
                        field=field_name,
                        rule="range",
                        message=f"{field_name} must be between {minimum_value} and {maximum_value}",
                        raw_value=self._format_raw_value(raw_field_value),
                    )
                )
                fields_with_issues.add(field_name)

        return ValidationResult(
            measurement=measurement,
            issues=validation_issues,
            is_valid=len(validation_issues) == 0,
        )

    def _format_raw_value(self, raw_value: object | None) -> str | None:
        if raw_value is None:
            return None

        return str(raw_value)

    def _is_missing_raw_value(self, raw_value: object | None) -> bool:
        if raw_value is None:
            return True

        return str(raw_value).strip() in MISSING_VALUE_MARKERS
