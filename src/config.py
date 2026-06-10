"""
config.py

Project-wide configuration.
"""

from pathlib import Path

# ---------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"

RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
DASHBOARD_DIR = DATA_DIR / "dashboard"

LOG_DIR = PROJECT_ROOT / "logs"

REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

# ---------------------------------------------------------------------
# NLP
# ---------------------------------------------------------------------

MIN_EMAIL_LENGTH = 20

# ---------------------------------------------------------------------
# Risk scoring
# ---------------------------------------------------------------------

HIGH_RISK_THRESHOLD = 70
MEDIUM_RISK_THRESHOLD = 40

# ---------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------

TOP_NETWORK_NODES = 50