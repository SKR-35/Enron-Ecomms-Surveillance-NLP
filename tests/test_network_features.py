"""
test_network_features.py

Purpose:
    Smoke-test Enron communication network outputs.

What this tests:
    - Network edge and node metric parquet files exist.
    - Directed email edge table contains required source/target fields.
    - Network metrics contain expected centrality and activity columns.
    - Graph size is large enough to represent a real communication network.

Why it matters:
    Network analytics are central to this project. If this layer breaks,
    investigation views and graph-based risk scoring become unreliable.
"""

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.utils.logger import get_logger  # noqa: E402


logger = get_logger(
    script_name="test_network_features",
    project_root=PROJECT_ROOT,
)

EDGES_FILE = PROJECT_ROOT / "data" / "processed" / "email_network_edges.parquet"
NODES_FILE = PROJECT_ROOT / "data" / "processed" / "email_network_metrics.parquet"


def test_network_files_exist():
    logger.info("Checking edge file exists: %s", EDGES_FILE)
    logger.info("Checking node file exists: %s", NODES_FILE)

    assert EDGES_FILE.exists()
    assert NODES_FILE.exists()


def test_network_edges_are_valid():
    edges = pd.read_parquet(EDGES_FILE)

    logger.info("Network edges shape: %s", edges.shape)

    required_cols = [
        "source",
        "target",
        "email_count",
        "risky_email_count",
        "risky_email_pct",
    ]

    missing_cols = [col for col in required_cols if col not in edges.columns]

    logger.info("Missing edge columns: %s", missing_cols)

    assert not missing_cols
    assert len(edges) > 100_000
    assert edges["source"].notna().all()
    assert edges["target"].notna().all()
    assert (edges["email_count"] > 0).all()


def test_network_metrics_are_valid():
    nodes = pd.read_parquet(NODES_FILE)

    logger.info("Network metrics shape: %s", nodes.shape)

    required_cols = [
        "node",
        "weighted_total_email_count",
        "total_connection_count",
        "degree_centrality",
        "betweenness_centrality",
        "risky_email_total",
    ]

    missing_cols = [col for col in required_cols if col not in nodes.columns]

    logger.info("Missing node columns: %s", missing_cols)

    assert not missing_cols
    assert len(nodes) > 20_000
    assert nodes["node"].notna().all()
    assert (nodes["weighted_total_email_count"] >= 0).all()
    assert (nodes["betweenness_centrality"] >= 0).all()