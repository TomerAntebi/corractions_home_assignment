import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    vehicle_id: Mapped[str] = mapped_column(String(255), nullable=False)
    driver_id: Mapped[str] = mapped_column(String(255), nullable=False)
    recording_date: Mapped[date] = mapped_column(Date, nullable=False)
    session_metadata: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )

    measurements: Mapped[list["MeasurementModel"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )


class MeasurementModel(Base):
    __tablename__ = "measurements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id"),
        nullable=False,
        index=True,
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    wheel_angle: Mapped[float | None] = mapped_column(Float, nullable=True)
    reverse_state: Mapped[bool | None] = mapped_column(nullable=True)
    is_valid: Mapped[bool] = mapped_column(nullable=False)
    validation_errors: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False, default=list)
    is_outlier: Mapped[bool] = mapped_column(nullable=False)

    session: Mapped[SessionModel] = relationship(back_populates="measurements")
