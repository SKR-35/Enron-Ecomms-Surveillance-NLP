"""
03_create_text_features.py

Create lightweight text features from parsed Enron emails.

Input:
    data/interim/parsed_emails.parquet

Output:
    data/processed/email_text_features.parquet

Run:
    python scripts/03_create_text_features.py
"""

from pathlib import Path
import re
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.utils.logger import get_logger  # noqa: E402


INPUT_FILE = PROJECT_ROOT / "data" / "interim" / "parsed_emails.parquet"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "email_text_features.parquet"

logger = get_logger(
    script_name="03_create_text_features",
    project_root=PROJECT_ROOT,
)


def log_section(title: str) -> None:
    logger.info("")
    logger.info("=" * 80)
    logger.info(title)
    logger.info("=" * 80)


def clean_text(text: object) -> str:
    if pd.isna(text):
        return ""

    text = str(text).lower()
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text


def uppercase_ratio(text: object) -> float:
    if pd.isna(text):
        return 0.0

    text = str(text)
    letters = [ch for ch in text if ch.isalpha()]

    if not letters:
        return 0.0

    uppercase_letters = [ch for ch in letters if ch.isupper()]

    return round(len(uppercase_letters) / len(letters), 4)


def main() -> None:
    log_section("CREATE TEXT FEATURES STARTED")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Input file  : %s", INPUT_FILE)
    logger.info("Output file : %s", OUTPUT_FILE)

    df = pd.read_parquet(INPUT_FILE)

    logger.info("Loaded shape: %s", df.shape)

    log_section("TEXT CLEANING")

    df["subject_clean"] = df["subject"].apply(clean_text)
    df["body_clean"] = df["body"].apply(clean_text)

    log_section("BASIC TEXT FEATURES")

    df["subject_length"] = df["subject_clean"].str.len()
    df["body_length"] = df["body_clean"].str.len()

    df["word_count"] = df["body_clean"].str.split().str.len()

    df["sentence_count"] = (
        df["body"]
        .fillna("")
        .astype(str)
        .str.count(r"[.!?]+")
    )

    df["has_subject"] = df["subject_clean"].str.len().gt(0).astype(int)

    df["is_reply"] = (
        df["subject_clean"]
        .str.startswith("re:")
        .astype(int)
    )

    df["is_forward"] = (
        df["subject_clean"]
        .str.startswith(("fw:", "fwd:"))
        .astype(int)
    )

    df["has_attachment_reference"] = (
        df["body_clean"]
        .str.contains(
            r"\b(attached|attachment|see attached|enclosed)\b",
            regex=True,
            na=False
        )
        .astype(int)
    )

    df["exclamation_count"] = (
        df["body"]
        .fillna("")
        .astype(str)
        .str.count("!")
    )

    df["question_count"] = (
        df["body"]
        .fillna("")
        .astype(str)
        .str.count(r"\?")
    )

    df["uppercase_ratio"] = df["body"].apply(uppercase_ratio)

    log_section("DATE NORMALIZATION")

    df["date_parsed"] = pd.to_datetime(
        df["date"],
        errors="coerce",
        utc=True
    )

    df["email_year"] = df["date_parsed"].dt.year
    df["email_month"] = df["date_parsed"].dt.month
    df["email_dayofweek"] = df["date_parsed"].dt.dayofweek
    df["email_hour"] = df["date_parsed"].dt.hour

    log_section("FEATURE SUMMARY")

    summary_cols = [
        "body_length",
        "word_count",
        "sentence_count",
        "exclamation_count",
        "question_count",
        "uppercase_ratio",
    ]

    logger.info("\n%s", df[summary_cols].describe().to_string())

    logger.info("Reply emails      : %s", f"{df['is_reply'].sum():,}")
    logger.info("Forward emails    : %s", f"{df['is_forward'].sum():,}")
    logger.info("Attachment refs   : %s", f"{df['has_attachment_reference'].sum():,}")
    logger.info("Parsed dates      : %s", f"{df['date_parsed'].notna().sum():,}")

    log_section("WRITE OUTPUT")

    df.to_parquet(OUTPUT_FILE, index=False)

    logger.info("Saved output: %s", OUTPUT_FILE)
    logger.info("Output shape: %s", df.shape)

    log_section("CREATE TEXT FEATURES COMPLETED")


if __name__ == "__main__":
    main()