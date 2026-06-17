import os
from pathlib import Path

from db.database import DatabaseSession
from import_flow import DuplicateSessionError, import_session


SAMPLE_DATA_DIR = Path(os.getenv("SAMPLE_DATA_DIR", "/sample-data"))
SAMPLE_METADATA_PATH = SAMPLE_DATA_DIR / "metadata_session_042.json"
SAMPLE_CSV_PATH = SAMPLE_DATA_DIR / "field_session_042.csv"


def seed_sample_data() -> None:
    database_session = DatabaseSession()

    try:
        import_session(
            metadata_content=SAMPLE_METADATA_PATH.read_bytes(),
            csv_content=SAMPLE_CSV_PATH.read_bytes(),
            database_session=database_session,
        )
        print("Imported sample session field_session_042.")
    except DuplicateSessionError:
        print("Sample session field_session_042 already exists.")
    finally:
        database_session.close()


if __name__ == "__main__":
    seed_sample_data()
