"""Application loader — cached startup pipeline from raw files through analytics bundle."""

import streamlit as st

import ingestion
import quality
from analytics import build_analytics_bundle
from dashboard.config import CSV_PATH, DB_PATH, METADATA_FILE_NAME, METADATA_PATH, SOURCE_FILE_NAME
from database import initialize_database, save_session_with_measurements


@st.cache_data
def load_application_data():
    raw_dataframe = ingestion.load_dataset(CSV_PATH)
    metadata = ingestion.load_session_metadata(METADATA_PATH)

    ingestion.validate_required_columns(raw_dataframe)
    ingestion.validate_metadata_file(metadata)

    normalized_dataframe = ingestion.normalize_types(raw_dataframe)
    measurement_dataframe = ingestion.prepare_measurement_data(normalized_dataframe)
    measurement_dataframe = ingestion.add_session_timeline(measurement_dataframe, metadata)

    initialize_database(DB_PATH)
    save_session_with_measurements(
        DB_PATH, metadata, measurement_dataframe, SOURCE_FILE_NAME, METADATA_FILE_NAME,
    )

    quality_dataframe = quality.build_quality_dataframe(measurement_dataframe)
    analytics_dataframe = quality.build_analytics_dataframe(measurement_dataframe, quality_dataframe)
    quality_report = quality.generate_quality_report(raw_dataframe, measurement_dataframe, quality_dataframe)

    return {
        "metadata": metadata,
        "measurement_dataframe": measurement_dataframe,
        "analytics_dataframe": analytics_dataframe,
        "quality_dataframe": quality_dataframe,
        "quality_report": quality_report,
        "cleaning_summary": quality.build_cleaning_summary_dataframe(quality_report),
        "analytics": build_analytics_bundle(
            analytics_dataframe, sample_rate_hz=metadata["sample_rate_hz"],
        ),
    }
