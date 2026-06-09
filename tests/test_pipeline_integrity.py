"""
test_pipeline_integrity.py

Purpose:
    End-to-end file integrity test for the Enron surveillance pipeline.

What this tests:
    - Every major pipeline artifact exists.
    - Dashboard-ready files exist.
    - Dashboard email table has expected minimum size and required fields.

Why it matters:
    This acts as a lightweight quality gate before running the Streamlit app.
    It confirms the pipeline produced all files required by the dashboard.
"""

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.utils.logger import get_logger  # noqa: E402


logger = get_logger(
    script_name="test_pipeline_integrity",
    project_root=PROJECT_ROOT,
)


EXPECTED_FILES = [
    PROJECT_ROOT / "data" / "interim" / "parsed_emails.parquet",
    PROJECT_ROOT / "data" / "processed" / "email_text_features.parquet",
    PROJECT_ROOT / "data" / "processed" / "email_risk_phrases.parquet",
    PROJECT_ROOT / "data" / "processed" / "email_network_edges.parquet",
    PROJECT_ROOT / "data" / "processed" / "email_network_metrics.parquet",
    PROJECT_ROOT / "data" / "processed" / "email_risk_scores.parquet",
    PROJECT_ROOT / "data" / "dashboard" / "emails_dashboard.parquet",
    PROJECT_ROOT / "data" / "dashboard" / "network_edges_dashboard.parquet",
    PROJECT_ROOT / "data" / "dashboard" / "network_nodes_dashboard.parquet",
    PROJECT_ROOT / "data" / "dashboard" / "kpi_summary.csv",
    PROJECT_ROOT / "data" / "dashboard" / "risk_band_summary.csv",
    PROJECT_ROOT / "data" / "dashboard" / "monthly_email_volume.csv",
]


def test_pipeline_artifacts_exist():
    missing_files = []

    for file_path in EXPECTED_FILES:
        logger.info("Checking file: %s", file_path)

        if not file_path.exists():
            missing_files.append(str(file_path))

    logger.info("Missing files: %s", missing_files)

    assert not missing_files


def test_dashboard_email_table_is_valid():
    dashboard_file = PROJECT_ROOT / "data" / "dashboard" / "emails_dashboard.parquet"

    df = pd.read_parquet(dashboard_file)

    logger.info("Dashboard email table shape: %s", df.shape)

    required_cols = [
        "date",
        "date_parsed",
        "from_email",
        "to_email",
        "subject",
        "final_risk_score",
        "risk_band",
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]

    logger.info("Missing dashboard columns: %s", missing_cols)

    assert len(df) > 500_000
    assert not missing_cols
    assert df["final_risk_score"].between(0, 100).all()