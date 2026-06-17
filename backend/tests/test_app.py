import uuid
from datetime import UTC, date, datetime

from api.controllers import session_controller
from api.routes.health_routes import get_health
from db.models import MeasurementModel, SessionModel


class FakeSessionQuery:
    def __init__(self, sessions: list[SessionModel]) -> None:
        self.sessions = sessions

    def all(self) -> list[SessionModel]:
        return self.sessions


class FakeDatabaseSession:
    def __init__(self, sessions: list[SessionModel]) -> None:
        self.sessions = sessions

    def query(self, model: type[SessionModel]) -> FakeSessionQuery:
        return FakeSessionQuery(self.sessions)

    def get(self, model: type[SessionModel], session_id: uuid.UUID) -> SessionModel | None:
        for session_model in self.sessions:
            if session_model.id == session_id:
                return session_model

        return None


def create_session_model() -> SessionModel:
    session_id = uuid.uuid4()
    session_model = SessionModel(
        id=session_id,
        session_id="session-001",
        vehicle_id="vehicle-001",
        driver_id="driver-001",
        recording_date=date(2025, 1, 1),
        session_metadata={
            "session_id": "session-001",
            "vehicle_id": "vehicle-001",
            "driver_id": "driver-001",
            "recording_date": "2025-01-01",
            "test_location": "Handling Track A",
        },
    )
    session_model.measurements = [
        MeasurementModel(
            id=uuid.uuid4(),
            session_id=session_id,
            row_index=0,
            timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
            speed=40.5,
            wheel_angle=2.5,
            reverse_state=False,
            raw_timestamp="2025-01-01T12:00:00Z",
            raw_speed="40.5",
            raw_wheel_angle="2.5",
            raw_reverse_state="false",
            is_valid=True,
            validation_errors=[],
            is_outlier=False,
        )
    ]

    return session_model


def test_health_response_shape() -> None:
    response = get_health()

    assert response.status == "ok"
    assert response.timestamp


def test_sessions_list_response_shape() -> None:
    session_model = create_session_model()

    response = session_controller.get_sessions(
        database_session=FakeDatabaseSession([session_model]),
    )

    assert [session.model_dump(by_alias=True) for session in response] == [
        {
            "id": str(session_model.id),
            "sessionId": "session-001",
            "vehicleId": "vehicle-001",
            "driverId": "driver-001",
            "recordingDate": "2025-01-01",
            "metadata": {
                "session_id": "session-001",
                "vehicle_id": "vehicle-001",
                "driver_id": "driver-001",
                "recording_date": "2025-01-01",
                "test_location": "Handling Track A",
            },
            "qualityScore": 1.0,
        }
    ]


def test_session_detail_analytics_and_dashboard_response_shapes() -> None:
    session_model = create_session_model()
    fake_database_session = FakeDatabaseSession([session_model])

    dashboard_response = session_controller.get_dashboard(
        id=session_model.id,
        database_session=fake_database_session,
    )

    dashboard_response_body = dashboard_response.model_dump(by_alias=True)
    assert set(dashboard_response_body) == {
        "session",
        "analytics",
        "qualityReport",
        "measurements",
    }
    assert dashboard_response_body["qualityReport"] == {
        "totalRows": 1,
        "validRows": 1,
        "invalidRows": 0,
        "outlierRows": 0,
        "qualityScore": 1.0,
        "missingByField": {},
        "invalidByRule": {},
        "sensorErrors": [],
    }
    assert dashboard_response_body["analytics"]["analyzedMeasurementCount"] == 1
    assert dashboard_response_body["analytics"]["speed"]["mean"] == 40.5
    assert dashboard_response_body["measurements"][0] == {
        "rowIndex": 0,
        "timestamp": "2025-01-01T12:00:00Z",
        "speed": 40.5,
        "wheelAngle": 2.5,
        "reverseState": False,
        "isValid": True,
        "isOutlier": False,
    }
