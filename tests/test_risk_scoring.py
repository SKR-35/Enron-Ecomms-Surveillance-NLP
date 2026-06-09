"""
test_risk_scoring.py

Purpose:
    Smoke-test email-level risk scoring output.

What this tests:
    - Risk score parquet exists.
    - Required risk scoring fields exist.
    - Final risk scores are bounded between 0 and 100.
    - Risk bands contain expected categories.
    - At least some emails are flagged as Medium or High risk.

Why it matters:
    The dashboard and investigation workflow depend on stable, interpretable
    risk scores. This test catches broken scoring logic early.
"""

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.utils.logger import get_logger  # noqa: E402


logger = get_logger(
    script_name="test_risk_scoring",
    project_root=PROJECT_ROOT,
)

RISK_FILE = PROJECT_ROOT / "data" / "processed" / "email_risk_scores.parquet"


def test_risk_score_file_exists():
    logger.info("Checking risk score file exists: %s", RISK_FILE)
    assert RISK_FILE.exists()


def test_risk_score_columns_exist():
    df = pd.read_parquet(RISK_FILE)

    logger.info("Risk score shape: %s", df.shape)

    required_cols = [
        "final_risk_score",
        "risk_band",
        "risk_phrase_score",
        "risk_phrase_category_count",
        "sender_network_volume",
        "sender_connection_count",
        "sender_betweenness",
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]

    logger.info("Missing risk columns: %s", missing_cols)

    assert not missing_cols


def test_risk_scores_are_valid():
    df = pd.read_parquet(RISK_FILE)

    logger.info("Risk score summary:")
    logger.info("\n%s", df["final_risk_score"].describe().to_string())

    assert df["final_risk_score"].between(0, 100).all()

    valid_bands = {"Low", "Medium", "High"}
    observed_bands = set(df["risk_band"].dropna().unique())

    logger.info("Observed risk bands: %s", observed_bands)

    assert observed_bands.issubset(valid_bands)
    assert (df["risk_band"].isin(["Medium", "High"])).sum() > 0