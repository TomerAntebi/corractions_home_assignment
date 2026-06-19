import os
from pathlib import Path

from db.database import DatabaseSession, initialize_database
from db.models import SessionModel
from import_flow import import_session


SAMPLE_DATA_DIR = Path(os.getenv("SAMPLE_DATA_DIR", "/sample-data"))
SAMPLE_METADATA_PATH = SAMPLE_DATA_DIR / "metadata_session_042.json"
SAMPLE_CSV_PATH = SAMPLE_DATA_DIR / "field_session_042.csv"
SAMPLE_SESSION_ID = "field_session_042"


def seed_sample_data() -> None:
    database_session = DatabaseSession()

    try:
        existing_session = (
            database_session.query(SessionModel)
            .filter_by(session_id=SAMPLE_SESSION_ID)
            .first()
        )
        if existing_session is not None:
            print(f"Sample session {SAMPLE_SESSION_ID} already exists.")
            return

        import_session(
            metadata_content=SAMPLE_METADATA_PATH.read_bytes(),
            csv_content=SAMPLE_CSV_PATH.read_bytes(),
            database_session=database_session,
        )
        print(f"Imported sample session {SAMPLE_SESSION_ID}.")
    finally:
        database_session.close()


if __name__ == "__main__":
    initialize_database()
    seed_sample_data()
