"""
07_create_risk_scores.py

Create combined email-level surveillance risk scores.

Inputs:
    data/processed/email_risk_phrases.parquet
    data/processed/email_network_metrics.parquet

Output:
    data/processed/email_risk_scores.parquet
    data/outputs/top_risk_scored_emails.csv

Run:
    python scripts/07_create_risk_scores.py
"""

from pathlib import Path
import sys

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.utils.logger import get_logger  # noqa: E402


EMAIL_FILE = PROJECT_ROOT / "data" / "processed" / "email_risk_phrases.parquet"
NETWORK_FILE = PROJECT_ROOT / "data" / "processed" / "email_network_metrics.parquet"

OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "email_risk_scores.parquet"
OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logger = get_logger(
    script_name="07_create_risk_scores",
    project_root=PROJECT_ROOT,
)


def log_section(title: str) -> None:
    logger.info("")
    logger.info("=" * 80)
    logger.info(title)
    logger.info("=" * 80)


def minmax_score(series: pd.Series) -> pd.Series:
    series = series.fillna(0)

    min_val = series.min()
    max_val = series.max()

    if max_val == min_val:
        return pd.Series(0, index=series.index)

    return ((series - min_val) / (max_val - min_val) * 100).round(2)


def risk_band(score: float) -> str:
    if score >= 75:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def main() -> None:
    log_section("CREATE RISK SCORES STARTED")

    logger.info("Email file   : %s", EMAIL_FILE)
    logger.info("Network file : %s", NETWORK_FILE)
    logger.info("Output file  : %s", OUTPUT_FILE)

    emails = pd.read_parquet(EMAIL_FILE)
    network = pd.read_parquet(NETWORK_FILE)

    logger.info("Emails shape  : %s", emails.shape)
    logger.info("Network shape : %s", network.shape)

    log_section("PREPARE NETWORK FEATURES")

    network_features = network[
        [
            "node",
            "weighted_total_email_count",
            "total_connection_count",
            "betweenness_centrality",
            "risky_email_total",
        ]
    ].copy()

    network_features = network_features.rename(
        columns={
            "node": "from_email",
            "weighted_total_email_count": "sender_network_volume",
            "total_connection_count": "sender_connection_count",
            "betweenness_centrality": "sender_betweenness",
            "risky_email_total": "sender_network_risky_email_total",
        }
    )

    log_section("MERGE EMAIL + NETWORK FEATURES")

    df = emails.merge(
        network_features,
        on="from_email",
        how="left",
    )

    network_cols = [
        "sender_network_volume",
        "sender_connection_count",
        "sender_betweenness",
        "sender_network_risky_email_total",
    ]

    df[network_cols] = df[network_cols].fillna(0)

    logger.info("Merged shape: %s", df.shape)

    log_section("CREATE COMPONENT SCORES")

    df["phrase_component_score"] = minmax_score(df["risk_phrase_score"])

    df["network_volume_component_score"] = minmax_score(
        np.log1p(df["sender_network_volume"])
    )

    df["network_betweenness_component_score"] = minmax_score(
        df["sender_betweenness"]
    )

    df["sender_risk_component_score"] = minmax_score(
        np.log1p(df["sender_network_risky_email_total"])
    )

    df["text_intensity_component_score"] = minmax_score(
        np.log1p(df["body_length"].fillna(0))
        + df["exclamation_count"].fillna(0)
        + df["question_count"].fillna(0)
    )

    log_section("CREATE FINAL SCORE")

    df["final_risk_score"] = (
        0.40 * df["phrase_component_score"]
        + 0.20 * df["network_volume_component_score"]
        + 0.20 * df["network_betweenness_component_score"]
        + 0.10 * df["sender_risk_component_score"]
        + 0.10 * df["text_intensity_component_score"]
    ).round(2)

    df["risk_band"] = df["final_risk_score"].apply(risk_band)

    logger.info("Risk score summary:")
    logger.info("\n%s", df["final_risk_score"].describe().to_string())

    logger.info("Risk band counts:")
    logger.info("\n%s", df["risk_band"].value_counts().to_string())

    log_section("WRITE TOP RISK EMAIL SAMPLE")

    sample_cols = [
        "file",
        "date",
        "from_email",
        "to_email",
        "subject",
        "final_risk_score",
        "risk_band",
        "risk_phrase_score",
        "risk_phrase_category_count",
        "sender_network_volume",
        "sender_connection_count",
        "sender_betweenness",
        "body_length",
        "word_count",
    ]

    available_cols = [col for col in sample_cols if col in df.columns]

    top_risk = (
        df.sort_values("final_risk_score", ascending=False)
        [available_cols]
        .head(250)
    )

    top_file = OUTPUT_DIR / "top_risk_scored_emails.csv"
    top_risk.to_csv(top_file, index=False)

    logger.info("Saved top risk sample: %s", top_file)
    logger.info("Top risk sample shape: %s", top_risk.shape)

    log_section("WRITE OUTPUT")

    df.to_parquet(OUTPUT_FILE, index=False)

    logger.info("Saved output: %s", OUTPUT_FILE)
    logger.info("Output shape: %s", df.shape)

    log_section("CREATE RISK SCORES COMPLETED")


if __name__ == "__main__":
    main()