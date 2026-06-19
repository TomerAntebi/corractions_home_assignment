"""Quality report generation from persisted measurements."""

from db.models import MeasurementModel
from quality.models import DataQualityReport


class DataQualityReporter:
    def generate_quality_report_from_measurements(
        self,
        measurements: list[MeasurementModel],
    ) -> DataQualityReport:
        total_rows = len(measurements)
        valid_rows = sum(1 for measurement in measurements if measurement.is_valid)
        outlier_rows = sum(1 for measurement in measurements if measurement.is_outlier)

        return DataQualityReport(
            total_rows=total_rows,
            valid_rows=valid_rows,
            invalid_rows=total_rows - valid_rows,
            outlier_rows=outlier_rows,
            missing_by_field=self._count_missing_fields_from_measurements(measurements),
            invalid_by_rule=self._count_invalid_rules_from_measurements(measurements),
            sensor_errors=self._collect_sensor_errors_from_measurements(measurements),
        )

    def _count_missing_fields_from_measurements(
        self,
        measurements: list[MeasurementModel],
    ) -> dict[str, int]:
        missing_by_field: dict[str, int] = {}

        for measurement in measurements:
            for validation_error in measurement.validation_errors:
                if validation_error.get("rule") == "required":
                    field = str(validation_error["field"])
                    missing_by_field[field] = missing_by_field.get(field, 0) + 1

        return missing_by_field

    def _count_invalid_rules_from_measurements(
        self,
        measurements: list[MeasurementModel],
    ) -> dict[str, int]:
        invalid_by_rule: dict[str, int] = {}

        for measurement in measurements:
            for validation_error in measurement.validation_errors:
                rule = str(validation_error["rule"])
                invalid_by_rule[rule] = invalid_by_rule.get(rule, 0) + 1

        return invalid_by_rule

    def _collect_sensor_errors_from_measurements(
        self,
        measurements: list[MeasurementModel],
    ) -> list[str]:
        sensor_errors: list[str] = []

        for measurement in measurements:
            for validation_error in measurement.validation_errors:
                raw_value = validation_error.get("raw_value")
                if (
                    validation_error.get("rule") == "invalid_marker"
                    and raw_value is not None
                    and str(raw_value) not in sensor_errors
                ):
                    sensor_errors.append(str(raw_value))

        return sensor_errors
