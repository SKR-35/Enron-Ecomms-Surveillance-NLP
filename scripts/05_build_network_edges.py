"""
05_build_network_edges.py

Build sender-recipient email network edges from Enron parsed/risk dataset.

Input:
    data/processed/email_risk_phrases.parquet

Outputs:
    data/processed/email_network_edges.parquet
    data/outputs/top_email_edges.csv

Run:
    python scripts/05_build_network_edges.py
"""

from pathlib import Path
import re
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.utils.logger import get_logger  # noqa: E402


INPUT_FILE = PROJECT_ROOT / "data" / "processed" / "email_risk_phrases.parquet"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "email_network_edges.parquet"
OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logger = get_logger(
    script_name="05_build_network_edges",
    project_root=PROJECT_ROOT,
)


EMAIL_PATTERN = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")


def log_section(title: str) -> None:
    logger.info("")
    logger.info("=" * 80)
    logger.info(title)
    logger.info("=" * 80)


def normalize_email(value: object) -> str:
    if pd.isna(value):
        return ""

    text = str(value).lower().strip()
    match = EMAIL_PATTERN.search(text)

    if match:
        return match.group(0)

    return text


def extract_recipients(value: object) -> list[str]:
    if pd.isna(value):
        return []

    text = str(value).lower()

    emails = EMAIL_PATTERN.findall(text)

    if emails:
        return sorted(set(emails))

    # fallback for names without email addresses
    parts = re.split(r"[;,]", text)
    parts = [p.strip() for p in parts if p.strip()]

    return sorted(set(parts))


def main() -> None:
    log_section("BUILD NETWORK EDGES STARTED")

    logger.info("Input file  : %s", INPUT_FILE)
    logger.info("Output file : %s", OUTPUT_FILE)

    df = pd.read_parquet(INPUT_FILE)

    logger.info("Loaded shape: %s", df.shape)

    log_section("NORMALIZE SENDERS AND RECIPIENTS")

    df["sender_norm"] = df["from_email"].apply(normalize_email)
    df["recipient_list"] = df["to_email"].apply(extract_recipients)

    valid = df[
        df["sender_norm"].ne("")
        & df["recipient_list"].map(len).gt(0)
    ].copy()

    logger.info("Valid emails for edges: %s", f"{len(valid):,}")

    log_section("EXPLODE RECIPIENTS")

    edges = valid[
        [
            "message_id",
            "date",
            "sender_norm",
            "recipient_list",
            "risk_phrase_score",
            "has_any_risk_phrase",
            "risk_phrase_category_count",
            "body_length",
            "word_count",
        ]
    ].explode("recipient_list")

    edges = edges.rename(
        columns={
            "sender_norm": "source",
            "recipient_list": "target",
        }
    )

    edges = edges[
        edges["source"].ne("")
        & edges["target"].ne("")
        & edges["source"].ne(edges["target"])
    ].copy()

    logger.info("Raw edge rows after explode: %s", f"{len(edges):,}")

    log_section("AGGREGATE EDGES")

    edge_summary = (
        edges
        .groupby(["source", "target"], as_index=False)
        .agg(
            email_count=("message_id", "count"),
            avg_risk_phrase_score=("risk_phrase_score", "mean"),
            max_risk_phrase_score=("risk_phrase_score", "max"),
            risky_email_count=("has_any_risk_phrase", "sum"),
            avg_body_length=("body_length", "mean"),
            avg_word_count=("word_count", "mean"),
        )
    )

    edge_summary["risky_email_pct"] = (
        edge_summary["risky_email_count"]
        / edge_summary["email_count"]
        * 100
    ).round(2)

    edge_summary = edge_summary.sort_values(
        ["email_count", "risky_email_count"],
        ascending=False
    )

    logger.info("Unique directed edges: %s", f"{len(edge_summary):,}")

    logger.info(
        "Unique sources: %s",
        f"{edge_summary['source'].nunique():,}"
    )

    logger.info(
        "Unique targets: %s",
        f"{edge_summary['target'].nunique():,}"
    )

    log_section("TOP EDGES")

    logger.info(
        "\n%s",
        edge_summary.head(20).to_string(index=False)
    )

    top_edges_file = OUTPUT_DIR / "top_email_edges.csv"
    edge_summary.head(100).to_csv(top_edges_file, index=False)

    logger.info("Saved top edges: %s", top_edges_file)

    log_section("WRITE OUTPUT")

    edge_summary.to_parquet(OUTPUT_FILE, index=False)

    logger.info("Saved output: %s", OUTPUT_FILE)
    logger.info("Output shape: %s", edge_summary.shape)

    log_section("BUILD NETWORK EDGES COMPLETED")


if __name__ == "__main__":
    main()