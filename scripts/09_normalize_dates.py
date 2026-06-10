"""
09_normalize_dates.py

Normalize Enron email date fields for reliable dashboard timelines.

Inputs:
    data/processed/email_risk_scores.parquet
    data/dashboard/emails_dashboard.parquet

Outputs:
    data/processed/email_risk_scores.parquet
    data/dashboard/emails_dashboard.parquet
    data/outputs/date_quality_summary.csv

Run:
    python scripts/09_normalize_dates.py
"""

from pathlib import Path
import re
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.utils.logger import get_logger  # noqa: E402


RISK_FILE = PROJECT_ROOT / "data" / "processed" / "email_risk_scores.parquet"
DASH_FILE = PROJECT_ROOT / "data" / "dashboard" / "emails_dashboard.parquet"
OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logger = get_logger(
    script_name="09_normalize_dates",
    project_root=PROJECT_ROOT,
)


def log_section(title: str) -> None:
    logger.info("")
    logger.info("=" * 80)
    logger.info(title)
    logger.info("=" * 80)


def clean_date_string(value: object) -> str:
    if pd.isna(value):
        return ""

    text = str(value).strip()

    # Remove timezone comments like "(PDT)", "(CST)", "(GMT Standard Time)"
    text = re.sub(r"\s*\([^)]*\)", "", text)

    # Remove duplicated whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def normalize_dates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["date_clean"] = df["date"].apply(clean_date_string)

    df["date_parsed"] = pd.to_datetime(
        df["date_clean"],
        errors="coerce",
        utc=True,
        format="mixed",
    )

    df["email_year"] = df["date_parsed"].dt.year
    df["email_month"] = df["date_parsed"].dt.month
    df["email_day"] = df["date_parsed"].dt.day
    df["email_dayofweek"] = df["date_parsed"].dt.dayofweek
    df["email_hour"] = df["date_parsed"].dt.hour
    df["email_month_period"] = df["date_parsed"].dt.to_period("M").astype(str)

    return df


def profile_dates(df: pd.DataFrame, label: str) -> dict:
    parsed_count = int(df["date_parsed"].notna().sum())
    total_count = len(df)

    return {
        "dataset": label,
        "total_rows": total_count,
        "parsed_dates": parsed_count,
        "parsed_pct": round(parsed_count / total_count * 100, 2),
        "min_date": df["date_parsed"].min(),
        "max_date": df["date_parsed"].max(),
    }


def main() -> None:
    log_section("NORMALIZE DATES STARTED")

    logger.info("Risk file      : %s", RISK_FILE)
    logger.info("Dashboard file : %s", DASH_FILE)

    risk_df = pd.read_parquet(RISK_FILE)
    dash_df = pd.read_parquet(DASH_FILE)

    logger.info("Risk shape before      : %s", risk_df.shape)
    logger.info("Dashboard shape before : %s", dash_df.shape)

    log_section("NORMALIZE RISK FILE DATES")
    risk_df = normalize_dates(risk_df)
    risk_profile = profile_dates(risk_df, "email_risk_scores")

    logger.info("Parsed dates : %s / %s (%s%%)",
                f"{risk_profile['parsed_dates']:,}",
                f"{risk_profile['total_rows']:,}",
                risk_profile["parsed_pct"])
    logger.info("Min date     : %s", risk_profile["min_date"])
    logger.info("Max date     : %s", risk_profile["max_date"])

    log_section("NORMALIZE DASHBOARD FILE DATES")
    dash_df = normalize_dates(dash_df)
    dash_profile = profile_dates(dash_df, "emails_dashboard")

    logger.info("Parsed dates : %s / %s (%s%%)",
                f"{dash_profile['parsed_dates']:,}",
                f"{dash_profile['total_rows']:,}",
                dash_profile["parsed_pct"])
    logger.info("Min date     : %s", dash_profile["min_date"])
    logger.info("Max date     : %s", dash_profile["max_date"])

    log_section("WRITE FILES")

    risk_df.to_parquet(RISK_FILE, index=False)
    dash_df.to_parquet(DASH_FILE, index=False)

    summary = pd.DataFrame([risk_profile, dash_profile])
    summary.to_csv(OUTPUT_DIR / "date_quality_summary.csv", index=False)

    logger.info("Overwritten risk file      : %s", RISK_FILE)
    logger.info("Overwritten dashboard file : %s", DASH_FILE)
    logger.info("Saved date summary         : %s", OUTPUT_DIR / "date_quality_summary.csv")

    log_section("NORMALIZE DATES COMPLETED")


if __name__ == "__main__":
    main()