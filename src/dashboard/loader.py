"""Application loader — cached startup pipeline from raw files through analytics bundle."""

import streamlit as st

from analytics import build_analytics_bundle
from dashboard.config import (
    CSV_PATH,
    DB_PATH,
    METADATA_FILE_NAME,
    METADATA_PATH,
    SOURCE_FILE_NAME,
)
from database import initialize_database, save_session_with_measurements
from ingestion import (
    clean_measurement_data,
    load_dataset,
    load_session_metadata,
    normalize_types,
    validate_metadata_file,
    validate_required_columns,
)
from quality import (
    build_analytics_dataframe,
    build_cleaning_summary_dataframe,
    build_quality_dataframe,
    generate_quality_report,
)


@st.cache_data
def load_application_data():
    raw_dataframe = load_dataset(CSV_PATH)
    metadata = load_session_metadata(METADATA_PATH)

    validate_required_columns(raw_dataframe)
    validate_metadata_file(metadata)

    normalized_dataframe = normalize_types(raw_dataframe)
    cleaned_dataframe = clean_measurement_data(normalized_dataframe)

    initialize_database(DB_PATH)
    save_session_with_measurements(
        DB_PATH,
        metadata,
        cleaned_dataframe,
        SOURCE_FILE_NAME,
        METADATA_FILE_NAME,
    )

    quality_dataframe = build_quality_dataframe(cleaned_dataframe)
    analytics_dataframe = build_analytics_dataframe(
        cleaned_dataframe,
        quality_dataframe,
    )
    quality_report = generate_quality_report(
        raw_dataframe,
        normalized_dataframe,
        cleaned_dataframe,
        quality_dataframe,
    )

    return {
        "metadata": metadata,
        "cleaned_dataframe": cleaned_dataframe,
        "analytics_dataframe": analytics_dataframe,
        "quality_dataframe": quality_dataframe,
        "quality_report": quality_report,
        "cleaning_summary": build_cleaning_summary_dataframe(quality_report),
        "analytics": build_analytics_bundle(analytics_dataframe),
    }
