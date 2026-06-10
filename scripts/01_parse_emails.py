"""
01_parse_emails.py

Parse raw Enron email messages into structured fields.

Input:
    data/raw/emails.csv

Output:
    data/interim/parsed_emails.parquet

Run:
    python scripts/01_parse_emails.py
"""

from pathlib import Path
import sys
from email import policy
from email.parser import Parser

import pandas as pd
from tqdm import tqdm


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
OUTPUT_FILE = PROJECT_ROOT / "data" / "interim" / "parsed_emails.parquet"

CHUNK_SIZE = 50_000

logger = get_logger(
    script_name="01_parse_emails",
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


def parse_message(raw_message: str) -> dict:
    """
    Parse one raw RFC-style email message.
    """

    try:
        msg = Parser(policy=policy.default).parsestr(raw_message)

        body = msg.get_body(preferencelist=("plain",))

        if body is not None:
            body_text = body.get_content()
        else:
            payload = msg.get_payload()
            body_text = payload if isinstance(payload, str) else ""

        return {
            "message_id": msg.get("Message-ID"),
            "date": msg.get("Date"),
            "from_email": msg.get("From"),
            "to_email": msg.get("To"),
            "cc_email": msg.get("Cc"),
            "bcc_email": msg.get("Bcc"),
            "subject": msg.get("Subject"),
            "mime_version": msg.get("Mime-Version"),
            "content_type": msg.get("Content-Type"),
            "x_from": msg.get("X-From"),
            "x_to": msg.get("X-To"),
            "x_cc": msg.get("X-cc"),
            "x_bcc": msg.get("X-bcc"),
            "x_folder": msg.get("X-Folder"),
            "x_origin": msg.get("X-Origin"),
            "x_filename": msg.get("X-FileName"),
            "body": body_text,
        }

    except Exception as exc:
        return {
            "message_id": None,
            "date": None,
            "from_email": None,
            "to_email": None,
            "cc_email": None,
            "bcc_email": None,
            "subject": None,
            "mime_version": None,
            "content_type": None,
            "x_from": None,
            "x_to": None,
            "x_cc": None,
            "x_bcc": None,
            "x_folder": None,
            "x_origin": None,
            "x_filename": None,
            "body": None,
            "parse_error": str(exc),
        }


def parse_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    parsed_records = []

    for _, row in chunk.iterrows():
        parsed = parse_message(str(row["message"]))
        parsed["file"] = row["file"]
        parsed_records.append(parsed)

    parsed_df = pd.DataFrame(parsed_records)

    if "parse_error" not in parsed_df.columns:
        parsed_df["parse_error"] = None

    return parsed_df


def main() -> None:
    log_section("EMAIL PARSING STARTED")

    if not RAW_FILE.exists():
        raise FileNotFoundError(f"Raw file not found: {RAW_FILE}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Input file  : %s", RAW_FILE)
    logger.info("Output file : %s", OUTPUT_FILE)
    logger.info("Chunk size  : %s", f"{CHUNK_SIZE:,}")

    parsed_chunks = []
    total_rows = 0

    reader = pd.read_csv(
        RAW_FILE,
        chunksize=CHUNK_SIZE,
    )

    for chunk_id, chunk in enumerate(tqdm(reader, desc="Parsing chunks"), start=1):
        logger.info("Parsing chunk %s with %s rows", chunk_id, f"{len(chunk):,}")

        parsed_chunk = parse_chunk(chunk)

        parsed_chunks.append(parsed_chunk)
        total_rows += len(parsed_chunk)

        logger.info("Parsed rows so far: %s", f"{total_rows:,}")

    logger.info("Combining parsed chunks")
    parsed_all = pd.concat(parsed_chunks, ignore_index=True)

    logger.info("Final shape: %s", parsed_all.shape)

    logger.info("Parse error count: %s", parsed_all["parse_error"].notna().sum())

    logger.info("Writing parquet file")
    parsed_all.to_parquet(OUTPUT_FILE, index=False)

    logger.info("Output saved: %s", OUTPUT_FILE)

    log_section("EMAIL PARSING COMPLETED")


if __name__ == "__main__":
    main()