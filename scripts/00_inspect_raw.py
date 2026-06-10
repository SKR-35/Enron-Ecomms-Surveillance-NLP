"""
00_inspect_raw.py

Inspect the raw Enron emails.csv file safely.

Outputs:
    logs/00_inspect_raw_<timestamp>.log

Run:
    python scripts/00_inspect_raw.py
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
# Paths and config
# ---------------------------------------------------------------------

RAW_FILE = PROJECT_ROOT / "data" / "raw" / "emails.csv"

SAMPLE_ROWS = 5
CHUNK_SIZE = 100_000

logger = get_logger(
    script_name="00_inspect_raw",
    project_root=PROJECT_ROOT,
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def log_section(title: str) -> None:
    logger.info("")
    logger.info("=" * 80)
    logger.info(title)
    logger.info("=" * 80)


def inspect_file() -> None:
    log_section("1. File Check")

    if not RAW_FILE.exists():
        raise FileNotFoundError(f"Raw file not found: {RAW_FILE}")

    size_mb = RAW_FILE.stat().st_size / (1024 ** 2)
    size_gb = RAW_FILE.stat().st_size / (1024 ** 3)

    logger.info("File path : %s", RAW_FILE)
    logger.info("File size : %.2f MB / %.2f GB", size_mb, size_gb)


def inspect_sample() -> pd.DataFrame:
    log_section("2. Sample Read")

    df = pd.read_csv(RAW_FILE, nrows=SAMPLE_ROWS)

    logger.info("Sample shape : %s", df.shape)
    logger.info("Columns      : %s", df.columns.tolist())

    logger.info("Dtypes:")
    logger.info("\n%s", df.dtypes.to_string())

    logger.info("Sample rows:")
    logger.info("\n%s", df.head(SAMPLE_ROWS).to_string())

    return df


def estimate_rows() -> int:
    log_section("3. Row Count")

    total_rows = 0

    for chunk in pd.read_csv(RAW_FILE, chunksize=CHUNK_SIZE):
        total_rows += len(chunk)

    logger.info("Total rows : %s", f"{total_rows:,}")

    return total_rows


def inspect_nulls() -> None:
    log_section("4. Null Count")

    null_counts = None
    total_rows = 0

    for chunk in pd.read_csv(RAW_FILE, chunksize=CHUNK_SIZE):
        total_rows += len(chunk)

        chunk_nulls = chunk.isna().sum()

        if null_counts is None:
            null_counts = chunk_nulls
        else:
            null_counts = null_counts.add(chunk_nulls, fill_value=0)

    null_summary = pd.DataFrame(
        {
            "null_count": null_counts.astype(int),
            "null_pct": (null_counts / total_rows * 100).round(2),
        }
    ).sort_values("null_pct", ascending=False)

    logger.info("Null summary:")
    logger.info("\n%s", null_summary.to_string())


def inspect_message_structure(df: pd.DataFrame) -> None:
    log_section("5. Raw Message Structure")

    if "message" not in df.columns:
        logger.warning("'message' column not found")
        logger.warning("Available columns: %s", df.columns.tolist())
        return

    first_message = str(df["message"].iloc[0])

    logger.info("First message preview, first 2,000 characters:")
    logger.info("\n%s", first_message[:2_000])

    logger.info("First 30 lines:")

    for i, line in enumerate(first_message.splitlines()[:30], start=1):
        logger.info("%02d | %s", i, line)


def main() -> None:
    log_section("RAW DATA INSPECTION STARTED")

    inspect_file()
    sample_df = inspect_sample()
    estimate_rows()
    inspect_nulls()
    inspect_message_structure(sample_df)

    log_section("RAW DATA INSPECTION COMPLETED")


if __name__ == "__main__":
    main()