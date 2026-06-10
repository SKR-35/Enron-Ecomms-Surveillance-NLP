"""
02_profile_parsed_emails.py

Profile parsed Enron emails.

Input:
    data/interim/parsed_emails.parquet

Outputs:
    logs/02_profile_parsed_emails_<timestamp>.log
    data/outputs/top_senders.csv
    data/outputs/top_recipients.csv

Run:
    python scripts/02_profile_parsed_emails.py
"""

from pathlib import Path
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

PARSED_FILE = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "parsed_emails.parquet"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "outputs"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

logger = get_logger(
    script_name="02_profile_parsed_emails",
    project_root=PROJECT_ROOT
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def log_section(title: str) -> None:
    logger.info("")
    logger.info("=" * 80)
    logger.info(title)
    logger.info("=" * 80)


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():

    log_section("LOAD DATA")

    df = pd.read_parquet(PARSED_FILE)

    logger.info(
        "Shape : %s",
        df.shape
    )

    logger.info(
        "Columns : %s",
        df.columns.tolist()
    )

    # --------------------------------------------------------------
    # Coverage
    # --------------------------------------------------------------

    log_section("FIELD COVERAGE")

    for col in [
        "message_id",
        "date",
        "from_email",
        "to_email",
        "subject",
        "body",
        "cc_email",
        "bcc_email",
    ]:

        if col not in df.columns:
            continue

        populated = df[col].notna().sum()

        pct = round(
            populated / len(df) * 100,
            2
        )

        logger.info(
            "%-15s : %10s (%6.2f%%)",
            col,
            f"{populated:,}",
            pct
        )

    # --------------------------------------------------------------
    # Parse errors
    # --------------------------------------------------------------

    log_section("PARSE ERRORS")

    parse_errors = df[
        df["parse_error"].notna()
    ]

    logger.info(
        "Parse error count : %s",
        f"{len(parse_errors):,}"
    )

    if len(parse_errors) > 0:

        logger.info(
            "Sample parse errors:"
        )

        logger.info(
            "\n%s",
            parse_errors[
                [
                    "file",
                    "parse_error"
                ]
            ]
            .head(10)
            .to_string()
        )

    # --------------------------------------------------------------
    # Body statistics
    # --------------------------------------------------------------

    log_section("BODY STATISTICS")

    df["body_length"] = (
        df["body"]
        .fillna("")
        .astype(str)
        .str.len()
    )

    logger.info(
        "Average body length : %.2f",
        df["body_length"].mean()
    )

    logger.info(
        "Median body length : %.2f",
        df["body_length"].median()
    )

    logger.info(
        "Max body length : %s",
        f"{int(df['body_length'].max()):,}"
    )

    # --------------------------------------------------------------
    # Date range
    # --------------------------------------------------------------

    log_section("DATE RANGE")

    try:

        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce"
        )

        logger.info(
            "Min date : %s",
            df["date"].min()
        )

        logger.info(
            "Max date : %s",
            df["date"].max()
        )

    except Exception as exc:

        logger.warning(
            "Date conversion failed: %s",
            exc
        )

    # --------------------------------------------------------------
    # Top senders
    # --------------------------------------------------------------

    log_section("TOP SENDERS")

    top_senders = (
        df["from_email"]
        .value_counts()
        .head(25)
        .reset_index()
    )

    top_senders.columns = [
        "sender",
        "email_count"
    ]

    logger.info(
        "\n%s",
        top_senders.head(10).to_string()
    )

    top_senders.to_csv(
        OUTPUT_DIR / "top_senders.csv",
        index=False
    )

    # --------------------------------------------------------------
    # Top recipients
    # --------------------------------------------------------------

    log_section("TOP RECIPIENTS")

    top_recipients = (
        df["to_email"]
        .value_counts()
        .head(25)
        .reset_index()
    )

    top_recipients.columns = [
        "recipient",
        "email_count"
    ]

    logger.info(
        "\n%s",
        top_recipients.head(10).to_string()
    )

    top_recipients.to_csv(
        OUTPUT_DIR / "top_recipients.csv",
        index=False
    )

    # --------------------------------------------------------------
    # Folder analysis
    # --------------------------------------------------------------

    log_section("TOP FOLDERS")

    if "x_folder" in df.columns:

        folders = (
            df["x_folder"]
            .value_counts()
            .head(20)
        )

        logger.info(
            "\n%s",
            folders.to_string()
        )

    # --------------------------------------------------------------
    # Subject analysis
    # --------------------------------------------------------------

    log_section("SUBJECT ANALYSIS")

    empty_subjects = (
        df["subject"]
        .fillna("")
        .str.strip()
        .eq("")
        .sum()
    )

    logger.info(
        "Empty subjects : %s",
        f"{empty_subjects:,}"
    )

    logger.info(
        "Non-empty subjects : %s",
        f"{len(df)-empty_subjects:,}"
    )

    log_section(
        "PROFILE COMPLETED"
    )


if __name__ == "__main__":
    main()