"""
Validation logic for normalized measurement rows.

Validation reports malformed or suspicious inputs without mutating the normalized
measurement. Downstream quality analysis and analytics decide how to use the
validated rows.
"""

from validation.config import (
    INVALID_MARKER,
    REQUIRED_FIELDS,
    SPEED_MAX,
    SPEED_MIN,
    WHEEL_ANGLE_MAX,
    WHEEL_ANGLE_MIN,
)
from validation.models import NormalizedMeasurement, ValidationIssue, ValidationResult


class MeasurementValidator:
    def validate_required_fields(self, measurement: NormalizedMeasurement) -> list[ValidationIssue]:
        validation_issues: list[ValidationIssue] = []

        # Required fields are the minimum data needed for session analytics.
        for field_name in REQUIRED_FIELDS:
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

        return validation_issues

    def validate_numeric_fields(self, measurement: NormalizedMeasurement) -> list[ValidationIssue]:
        validation_issues: list[ValidationIssue] = []

        numeric_fields = (
            ("speed", measurement.speed, measurement.raw_speed),
            ("wheel_angle", measurement.wheel_angle, measurement.raw_wheel_angle),
        )

        for field_name, numeric_value, raw_field_value in numeric_fields:
            if numeric_value is None and not self._is_missing_raw_value(raw_field_value):
                raw_value_text = str(raw_field_value).strip()
                # Sensor timeout markers are reported explicitly, not as generic numeric failures.
                if raw_value_text != INVALID_MARKER:
                    validation_issues.append(
                        ValidationIssue(
                            field=field_name,
                            rule="numeric",
                            message=f"{field_name} must be numeric",
                            raw_value=self._format_raw_value(raw_field_value),
                        )
                    )

        return validation_issues

    def validate_ranges(self, measurement: NormalizedMeasurement) -> list[ValidationIssue]:
        validation_issues: list[ValidationIssue] = []

        if measurement.speed is not None and not SPEED_MIN <= measurement.speed <= SPEED_MAX:
            validation_issues.append(
                ValidationIssue(
                    field="speed",
                    rule="range",
                    message="speed must be between 0 and 200",
                    raw_value=self._format_raw_value(measurement.raw_speed),
                )
            )

        if (
            measurement.wheel_angle is not None
            and not WHEEL_ANGLE_MIN <= measurement.wheel_angle <= WHEEL_ANGLE_MAX
        ):
            validation_issues.append(
                ValidationIssue(
                    field="wheel_angle",
                    rule="range",
                    message="wheel_angle must be between -45 and 45",
                    raw_value=self._format_raw_value(measurement.raw_wheel_angle),
                )
            )

        return validation_issues

    def validate_invalid_markers(self, measurement: NormalizedMeasurement) -> list[ValidationIssue]:
        validation_issues: list[ValidationIssue] = []

        # ERROR_TIMEOUT means the sensor failed to provide a trustworthy value.
        marker_fields = (
            ("timestamp", measurement.raw_timestamp),
            ("speed", measurement.raw_speed),
            ("wheel_angle", measurement.raw_wheel_angle),
            ("reverse_state", measurement.raw_reverse_state),
        )

        for field_name, raw_field_value in marker_fields:
            if str(raw_field_value).strip() == INVALID_MARKER:
                validation_issues.append(
                    ValidationIssue(
                        field=field_name,
                        rule="invalid_marker",
                        message=f"{field_name} contains ERROR_TIMEOUT",
                        raw_value=INVALID_MARKER,
                    )
                )

        return validation_issues

    def validate_measurement(
        self,
        normalized_measurement: dict[str, object | None] | NormalizedMeasurement,
    ) -> ValidationResult:
        measurement = self._create_normalized_measurement(normalized_measurement)
        validation_issues: list[ValidationIssue] = []

        validation_issues.extend(self.validate_required_fields(measurement))
        validation_issues.extend(self.validate_numeric_fields(measurement))
        validation_issues.extend(self.validate_ranges(measurement))
        validation_issues.extend(self.validate_invalid_markers(measurement))

        return ValidationResult(
            measurement=measurement,
            issues=validation_issues,
            is_valid=len(validation_issues) == 0,
        )

    def validate_all_measurements(
        self,
        normalized_measurements: list[dict[str, object | None] | NormalizedMeasurement],
    ) -> list[ValidationResult]:
        return [
            self.validate_measurement(normalized_measurement)
            for normalized_measurement in normalized_measurements
        ]

    def _create_normalized_measurement(
        self,
        normalized_measurement: dict[str, object | None] | NormalizedMeasurement,
    ) -> NormalizedMeasurement:
        if isinstance(normalized_measurement, NormalizedMeasurement):
            return normalized_measurement

        return NormalizedMeasurement.model_validate(normalized_measurement)

    def _format_raw_value(self, raw_value: object | None) -> str | None:
        if raw_value is None:
            return None

        return str(raw_value)

    def _is_missing_raw_value(self, raw_value: object | None) -> bool:
        if raw_value is None:
            return True

        return str(raw_value).strip() in {"", "null", "NaN"}
