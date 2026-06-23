"""Application data — cached startup pipeline from raw files through analytics bundle."""

import streamlit as st

import ingestion
import quality
from analytics.analytics import build_analytics_bundle
from analytics.features import build_analytics_dataframe
from dashboard.settings import CSV_PATH, DB_PATH, METADATA_FILE_NAME, METADATA_PATH, SOURCE_FILE_NAME
from database import initialize_database, save_session_with_measurements


@st.cache_data
def load_application_data():
    """Load once, then pass prepared dataframes/results to the dashboard tabs."""
    raw_dataframe = ingestion.load_dataset(CSV_PATH)
    metadata = ingestion.load_session_metadata(METADATA_PATH)

    ingestion.validate_required_columns(raw_dataframe)
    ingestion.validate_metadata_file(metadata)

    measurement_dataframe = ingestion.build_measurement_dataframe(raw_dataframe, metadata)

    # Persistence is intentionally limited to imported session data; analytics stay reproducible.
    initialize_database(DB_PATH)
    save_session_with_measurements(
        DB_PATH, metadata, measurement_dataframe, SOURCE_FILE_NAME, METADATA_FILE_NAME,
    )

    # Quality flags are kept separate from analytics features so the dashboard can explain both.
    quality_dataframe = quality.build_quality_dataframe(measurement_dataframe)
    clean_measurement_dataframe = quality.build_clean_measurement_dataframe(measurement_dataframe, quality_dataframe)
    analytics_dataframe = build_analytics_dataframe(clean_measurement_dataframe)
    quality_report = quality.generate_quality_report(raw_dataframe, measurement_dataframe, quality_dataframe)
    cleaning_summary = quality.build_cleaning_summary_dataframe(quality_report)
    analytics = build_analytics_bundle(analytics_dataframe, sample_rate_hz=metadata["sample_rate_hz"],)

    return {
        "metadata": metadata,
        "measurement_dataframe": measurement_dataframe,
        "analytics_dataframe": analytics_dataframe,
        "quality_dataframe": quality_dataframe,
        "quality_report": quality_report,
        "cleaning_summary": cleaning_summary,
        "analytics": analytics,
    }
