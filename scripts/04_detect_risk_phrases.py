"""
04_detect_risk_phrases.py

Detect FCC / compliance-style risk phrases in Enron email text.

Input:
    data/processed/email_text_features.parquet

Outputs:
    data/processed/email_risk_phrases.parquet
    data/outputs/risk_phrase_category_summary.csv
    data/outputs/top_risky_emails_sample.csv

Run:
    python scripts/04_detect_risk_phrases.py
"""

from pathlib import Path
import re
import sys

import pandas as pd


# ---------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.utils.logger import get_logger  # noqa: E402


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

INPUT_FILE = PROJECT_ROOT / "data" / "processed" / "email_text_features.parquet"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "email_risk_phrases.parquet"
OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logger = get_logger(
    script_name="04_detect_risk_phrases",
    project_root=PROJECT_ROOT,
)


# ---------------------------------------------------------------------
# Risk phrase dictionary
# ---------------------------------------------------------------------

RISK_PHRASES = {
    "confidentiality": [
        "confidential",
        "strictly confidential",
        "private",
        "privileged",
        "attorney client",
        "do not distribute",
        "do not forward",
        "internal use only",
        "sensitive",
    ],
    "concealment": [
        "off the record",
        "between us",
        "keep this between us",
        "do not tell",
        "don't tell",
        "not for distribution",
        "keep quiet",
        "cover up",
        "hide",
    ],
    "deletion": [
        "delete this",
        "delete after reading",
        "destroy",
        "shred",
        "remove this",
        "erase",
    ],
    "urgency_pressure": [
        "urgent",
        "asap",
        "immediately",
        "right away",
        "critical",
        "must do",
        "need this today",
        "deadline",
        "pressure",
    ],
    "legal_regulatory": [
        "legal",
        "lawyer",
        "attorney",
        "regulator",
        "sec",
        "federal",
        "investigation",
        "subpoena",
        "audit",
        "compliance",
    ],
    "financial_risk": [
        "loss",
        "losses",
        "write off",
        "write-off",
        "exposure",
        "liability",
        "default",
        "bankruptcy",
        "fraud",
        "manipulate",
        "misstate",
    ],
    "offline_meeting": [
        "call me",
        "let's talk",
        "lets talk",
        "discuss offline",
        "offline",
        "in person",
        "face to face",
        "not by email",
    ],
}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def log_section(title: str) -> None:
    logger.info("")
    logger.info("=" * 80)
    logger.info(title)
    logger.info("=" * 80)


def build_regex(phrases: list[str]) -> str:
    """
    Build safe regex pattern from phrase list.

    Uses word-ish boundaries where possible.
    """
    escaped = [re.escape(p.lower()) for p in phrases]
    return r"(" + "|".join(escaped) + r")"


def main() -> None:
    log_section("RISK PHRASE DETECTION STARTED")

    logger.info("Input file  : %s", INPUT_FILE)
    logger.info("Output file : %s", OUTPUT_FILE)

    df = pd.read_parquet(INPUT_FILE)

    logger.info("Loaded shape: %s", df.shape)

    # Combine subject and body for surveillance-style phrase detection
    log_section("PREPARE TEXT")

    df["surveillance_text"] = (
        df["subject_clean"].fillna("")
        + " "
        + df["body_clean"].fillna("")
    ).str.strip()

    logger.info("Prepared surveillance_text")

    # Detect risk categories
    log_section("DETECT CATEGORY FLAGS")

    category_cols = []

    for category, phrases in RISK_PHRASES.items():
        col = f"risk_{category}"
        pattern = build_regex(phrases)

        logger.info("Detecting category: %s", category)

        df[col] = (
            df["surveillance_text"]
            .str.contains(pattern, regex=True, na=False)
            .astype(int)
        )

        category_cols.append(col)

        logger.info(
            "%s hits: %s",
            col,
            f"{df[col].sum():,}"
        )

    # Aggregate risk phrase score
    log_section("CREATE RISK PHRASE SCORE")

    df["risk_phrase_category_count"] = df[category_cols].sum(axis=1)

    df["has_any_risk_phrase"] = (
        df["risk_phrase_category_count"].gt(0).astype(int)
    )

    # Simple weighted score for now.
    # We can tune this later with network metrics and investigation logic.
    weights = {
        "risk_confidentiality": 2,
        "risk_concealment": 4,
        "risk_deletion": 5,
        "risk_urgency_pressure": 2,
        "risk_legal_regulatory": 3,
        "risk_financial_risk": 3,
        "risk_offline_meeting": 2,
    }

    df["risk_phrase_score"] = 0

    for col, weight in weights.items():
        if col in df.columns:
            df["risk_phrase_score"] += df[col] * weight

    logger.info(
        "Emails with any risk phrase: %s",
        f"{df['has_any_risk_phrase'].sum():,}"
    )

    logger.info(
        "Average risk phrase score: %.4f",
        df["risk_phrase_score"].mean()
    )

    logger.info(
        "Max risk phrase score: %s",
        df["risk_phrase_score"].max()
    )

    # Category summary
    log_section("WRITE CATEGORY SUMMARY")

    summary_records = []

    for col in category_cols:
        count = int(df[col].sum())
        pct = round(count / len(df) * 100, 2)

        summary_records.append(
            {
                "risk_category": col.replace("risk_", ""),
                "email_count": count,
                "email_pct": pct,
            }
        )

    summary_df = (
        pd.DataFrame(summary_records)
        .sort_values("email_count", ascending=False)
    )

    summary_file = OUTPUT_DIR / "risk_phrase_category_summary.csv"
    summary_df.to_csv(summary_file, index=False)

    logger.info("\n%s", summary_df.to_string(index=False))
    logger.info("Saved summary: %s", summary_file)

    # Top risky sample for manual inspection
    log_section("WRITE TOP RISKY EMAIL SAMPLE")

    sample_cols = [
        "file",
        "date",
        "from_email",
        "to_email",
        "subject",
        "risk_phrase_score",
        "risk_phrase_category_count",
    ] + category_cols

    available_cols = [col for col in sample_cols if col in df.columns]

    top_risky = (
        df[df["risk_phrase_score"] > 0]
        .sort_values(
            ["risk_phrase_score", "risk_phrase_category_count"],
            ascending=False
        )
        [available_cols]
        .head(100)
    )

    sample_file = OUTPUT_DIR / "top_risky_emails_sample.csv"
    top_risky.to_csv(sample_file, index=False)

    logger.info("Top risky sample shape: %s", top_risky.shape)
    logger.info("Saved sample: %s", sample_file)

    # Write output parquet
    log_section("WRITE OUTPUT PARQUET")

    df.to_parquet(OUTPUT_FILE, index=False)

    logger.info("Saved output: %s", OUTPUT_FILE)
    logger.info("Output shape: %s", df.shape)

    log_section("RISK PHRASE DETECTION COMPLETED")


if __name__ == "__main__":
    main()