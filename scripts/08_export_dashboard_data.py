"""
08_export_dashboard_data.py

Export lightweight dashboard-ready datasets.

Inputs:
    data/processed/email_risk_scores.parquet
    data/processed/email_network_edges.parquet
    data/processed/email_network_metrics.parquet

Outputs:
    data/dashboard/emails_dashboard.parquet
    data/dashboard/network_edges_dashboard.parquet
    data/dashboard/network_nodes_dashboard.parquet
    data/dashboard/kpi_summary.csv
    data/dashboard/risk_band_summary.csv
    data/dashboard/monthly_email_volume.csv

Run:
    python scripts/08_export_dashboard_data.py
"""

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.utils.logger import get_logger  # noqa: E402


EMAIL_SCORES_FILE = PROJECT_ROOT / "data" / "processed" / "email_risk_scores.parquet"
EDGES_FILE = PROJECT_ROOT / "data" / "processed" / "email_network_edges.parquet"
NODES_FILE = PROJECT_ROOT / "data" / "processed" / "email_network_metrics.parquet"

OUTPUT_DIR = PROJECT_ROOT / "data" / "dashboard"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logger = get_logger(
    script_name="08_export_dashboard_data",
    project_root=PROJECT_ROOT,
)


def log_section(title: str) -> None:
    logger.info("")
    logger.info("=" * 80)
    logger.info(title)
    logger.info("=" * 80)


def main() -> None:
    log_section("EXPORT DASHBOARD DATA STARTED")

    logger.info("Email scores file : %s", EMAIL_SCORES_FILE)
    logger.info("Edges file        : %s", EDGES_FILE)
    logger.info("Nodes file        : %s", NODES_FILE)
    logger.info("Output dir        : %s", OUTPUT_DIR)

    emails = pd.read_parquet(EMAIL_SCORES_FILE)
    edges = pd.read_parquet(EDGES_FILE)
    nodes = pd.read_parquet(NODES_FILE)

    logger.info("Emails shape : %s", emails.shape)
    logger.info("Edges shape  : %s", edges.shape)
    logger.info("Nodes shape  : %s", nodes.shape)

    # ------------------------------------------------------------
    # Dashboard emails
    # ------------------------------------------------------------

    log_section("EXPORT EMAIL DASHBOARD TABLE")

    email_cols = [
        "file",
        "message_id",
        "date",
        "date_parsed",
        "from_email",
        "to_email",
        "subject",
        "body_length",
        "word_count",
        "is_reply",
        "is_forward",
        "has_attachment_reference",
        "risk_phrase_score",
        "risk_phrase_category_count",
        "has_any_risk_phrase",
        "final_risk_score",
        "risk_band",
        "sender_network_volume",
        "sender_connection_count",
        "sender_betweenness",
        "risk_confidentiality",
        "risk_concealment",
        "risk_deletion",
        "risk_urgency_pressure",
        "risk_legal_regulatory",
        "risk_financial_risk",
        "risk_offline_meeting",
    ]

    email_cols = [col for col in email_cols if col in emails.columns]

    emails_dash = emails[email_cols].copy()

    # Keep body out of dashboard export for performance.
    # Full text can be added later for an investigation detail page if needed.

    emails_dash.to_parquet(
        OUTPUT_DIR / "emails_dashboard.parquet",
        index=False,
    )

    logger.info("emails_dashboard shape: %s", emails_dash.shape)

    # ------------------------------------------------------------
    # Network edges
    # ------------------------------------------------------------

    log_section("EXPORT NETWORK EDGES DASHBOARD TABLE")

    edges_dash = (
        edges
        .sort_values(["email_count", "risky_email_count"], ascending=False)
        .head(50_000)
        .copy()
    )

    edges_dash.to_parquet(
        OUTPUT_DIR / "network_edges_dashboard.parquet",
        index=False,
    )

    logger.info("network_edges_dashboard shape: %s", edges_dash.shape)

    # ------------------------------------------------------------
    # Network nodes
    # ------------------------------------------------------------

    log_section("EXPORT NETWORK NODES DASHBOARD TABLE")

    nodes_dash = (
        nodes
        .sort_values(
            [
                "weighted_total_email_count",
                "betweenness_centrality",
                "risky_email_total",
            ],
            ascending=False,
        )
        .head(25_000)
        .copy()
    )

    nodes_dash.to_parquet(
        OUTPUT_DIR / "network_nodes_dashboard.parquet",
        index=False,
    )

    logger.info("network_nodes_dashboard shape: %s", nodes_dash.shape)

    # ------------------------------------------------------------
    # KPI summary
    # ------------------------------------------------------------

    log_section("EXPORT KPI SUMMARY")

    kpi_summary = pd.DataFrame(
        [
            {
                "metric": "total_emails",
                "value": len(emails),
            },
            {
                "metric": "emails_with_any_risk_phrase",
                "value": int(emails["has_any_risk_phrase"].sum()),
            },
            {
                "metric": "high_risk_emails",
                "value": int((emails["risk_band"] == "High").sum()),
            },
            {
                "metric": "medium_risk_emails",
                "value": int((emails["risk_band"] == "Medium").sum()),
            },
            {
                "metric": "unique_senders",
                "value": int(emails["from_email"].nunique()),
            },
            {
                "metric": "unique_network_nodes",
                "value": int(nodes["node"].nunique()),
            },
            {
                "metric": "unique_network_edges",
                "value": len(edges),
            },
            {
                "metric": "max_risk_score",
                "value": float(emails["final_risk_score"].max()),
            },
            {
                "metric": "avg_risk_score",
                "value": float(round(emails["final_risk_score"].mean(), 2)),
            },
        ]
    )

    kpi_summary.to_csv(
        OUTPUT_DIR / "kpi_summary.csv",
        index=False,
    )

    logger.info("\n%s", kpi_summary.to_string(index=False))

    # ------------------------------------------------------------
    # Risk band summary
    # ------------------------------------------------------------

    log_section("EXPORT RISK BAND SUMMARY")

    risk_band_summary = (
        emails["risk_band"]
        .value_counts()
        .rename_axis("risk_band")
        .reset_index(name="email_count")
    )

    risk_band_summary["email_pct"] = (
        risk_band_summary["email_count"] / len(emails) * 100
    ).round(2)

    risk_band_summary.to_csv(
        OUTPUT_DIR / "risk_band_summary.csv",
        index=False,
    )

    logger.info("\n%s", risk_band_summary.to_string(index=False))

    # ------------------------------------------------------------
    # Monthly volume
    # ------------------------------------------------------------

    log_section("EXPORT MONTHLY EMAIL VOLUME")

    if "date_parsed" in emails.columns:
        tmp = emails.copy()

        tmp["date_parsed"] = pd.to_datetime(
            tmp["date_parsed"],
            errors="coerce",
            utc=True,
        )

        tmp = tmp[tmp["date_parsed"].notna()].copy()
        tmp["month"] = tmp["date_parsed"].dt.to_period("M").astype(str)

        monthly = (
            tmp
            .groupby("month", as_index=False)
            .agg(
                email_count=("message_id", "count"),
                avg_risk_score=("final_risk_score", "mean"),
                high_risk_count=("risk_band", lambda x: (x == "High").sum()),
                medium_risk_count=("risk_band", lambda x: (x == "Medium").sum()),
            )
        )

        monthly["avg_risk_score"] = monthly["avg_risk_score"].round(2)

    else:
        monthly = pd.DataFrame(
            columns=[
                "month",
                "email_count",
                "avg_risk_score",
                "high_risk_count",
                "medium_risk_count",
            ]
        )

    monthly.to_csv(
        OUTPUT_DIR / "monthly_email_volume.csv",
        index=False,
    )

    logger.info("Monthly rows: %s", len(monthly))
    logger.info("\n%s", monthly.head(10).to_string(index=False))

    log_section("EXPORT DASHBOARD DATA COMPLETED")


if __name__ == "__main__":
    main()