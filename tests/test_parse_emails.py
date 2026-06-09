"""
test_parse_emails.py

Purpose:
    Smoke-test the parsed Enron email dataset.

What this tests:
    - Parsed parquet file exists.
    - Dataset has expected minimum row count.
    - Critical parsed email fields exist.
    - Parse error rate is acceptably low.

Why it matters:
    If this test fails, downstream NLP, risk scoring, and dashboard layers
    may be unreliable because the raw emails were not parsed correctly.
"""

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.utils.logger import get_logger  # noqa: E402


logger = get_logger(
    script_name="test_parse_emails",
    project_root=PROJECT_ROOT,
)

PARSED_FILE = PROJECT_ROOT / "data" / "interim" / "parsed_emails.parquet"


def test_parsed_emails_file_exists():
    logger.info("Checking parsed emails file exists: %s", PARSED_FILE)
    assert PARSED_FILE.exists()


def test_parsed_emails_shape_and_columns():
    logger.info("Reading parsed emails parquet")
    df = pd.read_parquet(PARSED_FILE)

    logger.info("Parsed emails shape: %s", df.shape)

    assert len(df) > 500_000

    required_cols = [
        "message_id",
        "date",
        "from_email",
        "to_email",
        "subject",
        "body",
        "parse_error",
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]

    logger.info("Missing columns: %s", missing_cols)

    assert not missing_cols


def test_parse_error_rate_is_low():
    df = pd.read_parquet(PARSED_FILE)

    parse_error_count = df["parse_error"].notna().sum()
    parse_error_rate = parse_error_count / len(df)

    logger.info("Parse error count: %s", parse_error_count)
    logger.info("Parse error rate: %.6f", parse_error_rate)

    assert parse_error_rate < 0.001