import uuid
from datetime import date

import pytest

from import_flow import DuplicateSessionError, import_session
from db.models import MeasurementModel, SessionModel


class FakeSessionQuery:
    def __init__(self, imported_sessions: list[SessionModel]) -> None:
        self.imported_sessions = imported_sessions
        self.session_id: str | None = None

    def filter_by(self, session_id: str) -> "FakeSessionQuery":
        self.session_id = session_id
        return self

    def first(self) -> SessionModel | None:
        for imported_session in self.imported_sessions:
            if imported_session.session_id == self.session_id:
                return imported_session

        return None


class FakeDatabaseSession:
    def __init__(self) -> None:
        self.imported_sessions: list[SessionModel] = []
        self.imported_measurements: list[MeasurementModel] = []
        self.was_committed = False
        self.was_rolled_back = False

    def query(self, model: type[SessionModel]) -> FakeSessionQuery:
        return FakeSessionQuery(self.imported_sessions)

    def add(self, database_model: object) -> None:
        if isinstance(database_model, SessionModel):
            self.imported_sessions.append(database_model)

    def add_all(self, database_models: list[MeasurementModel]) -> None:
        self.imported_measurements.extend(database_models)

    def flush(self) -> None:
        for imported_session in self.imported_sessions:
            if imported_session.id is None:
                imported_session.id = uuid.uuid4()

    def commit(self) -> None:
        self.was_committed = True

    def rollback(self) -> None:
        self.was_rolled_back = True

    def refresh(self, database_model: object) -> None:
        return None


def create_metadata_content(session_id: str = "session-001") -> str:
    return (
        "{"
        f'"session_id": "{session_id}", '
        '"vehicle_id": "vehicle-001", '
        '"driver_id": "driver-001", '
        '"recording_date": "2025-01-01", '
        '"test_location": "Handling Track A", '
        '"start_time_utc": "2025-01-01T12:00:00Z", '
        '"end_time_utc": "2025-01-01T12:01:00Z", '
        '"sample_rate_hz": 1, '
        '"hardware_version": "v2.1.4", '
        '"firmware_version": "fw_beta_0.9", '
        '"sensors_active": ["steering_angle_sensor", "obd2_speed", "reverse_state"], '
        '"notes": "Sample notes"'
        "}"
    )


def create_csv_content() -> str:
    return (
        "timestamp,speed,wheel_angle,reverse_state\n"
        "2025-01-01T12:00:00Z,10,0,false\n"
        "2025-01-01T12:01:00Z,20,5,true\n"
    )


def test_import_session_creates_one_session_and_measurements() -> None:
    fake_database_session = FakeDatabaseSession()

    imported_session = import_session(
        metadata_content=create_metadata_content(),
        csv_content=create_csv_content(),
        database_session=fake_database_session,
    )

    assert imported_session.session_id == "session-001"
    assert imported_session.vehicle_id == "vehicle-001"
    assert imported_session.recording_date == date(2025, 1, 1)
    assert imported_session.session_metadata["test_location"] == "Handling Track A"
    assert imported_session.session_metadata["sample_rate_hz"] == 1
    assert imported_session.session_metadata["sensors_active"] == [
        "steering_angle_sensor",
        "obd2_speed",
        "reverse_state",
    ]
    assert len(fake_database_session.imported_sessions) == 1
    assert len(fake_database_session.imported_measurements) == 2
    assert fake_database_session.was_committed is True
    assert fake_database_session.was_rolled_back is False


def test_import_session_stores_measurement_quality_results() -> None:
    fake_database_session = FakeDatabaseSession()

    imported_session = import_session(
        metadata_content=create_metadata_content(),
        csv_content=create_csv_content(),
        database_session=fake_database_session,
    )

    assert not hasattr(imported_session, "quality_report")
    assert not hasattr(imported_session, "analytics_report")
    assert [measurement.is_valid for measurement in fake_database_session.imported_measurements] == [
        True,
        True,
    ]
    assert [measurement.is_outlier for measurement in fake_database_session.imported_measurements] == [
        False,
        False,
    ]


def test_import_session_rejects_duplicate_session() -> None:
    fake_database_session = FakeDatabaseSession()
    fake_database_session.imported_sessions.append(
        SessionModel(
            session_id="session-001",
            vehicle_id="vehicle-001",
            driver_id="driver-001",
            recording_date=date(2025, 1, 1),
            session_metadata={},
        )
    )

    with pytest.raises(DuplicateSessionError):
        import_session(
            metadata_content=create_metadata_content(),
            csv_content=create_csv_content(),
            database_session=fake_database_session,
        )
