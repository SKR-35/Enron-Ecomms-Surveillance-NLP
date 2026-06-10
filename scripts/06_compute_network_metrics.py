"""
06_compute_network_metrics.py

Compute node-level network metrics from Enron email edge table.

Input:
    data/processed/email_network_edges.parquet

Outputs:
    data/processed/email_network_metrics.parquet
    data/outputs/top_network_nodes.csv

Run:
    python scripts/06_compute_network_metrics.py
"""

from pathlib import Path
import sys

import networkx as nx
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.utils.logger import get_logger  # noqa: E402


INPUT_FILE = PROJECT_ROOT / "data" / "processed" / "email_network_edges.parquet"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "email_network_metrics.parquet"
OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logger = get_logger(
    script_name="06_compute_network_metrics",
    project_root=PROJECT_ROOT,
)


MIN_EMAIL_COUNT = 5


def log_section(title: str) -> None:
    logger.info("")
    logger.info("=" * 80)
    logger.info(title)
    logger.info("=" * 80)


def main() -> None:
    log_section("NETWORK METRICS STARTED")

    logger.info("Input file  : %s", INPUT_FILE)
    logger.info("Output file : %s", OUTPUT_FILE)
    logger.info("Min edge email count: %s", MIN_EMAIL_COUNT)

    edges = pd.read_parquet(INPUT_FILE)
    logger.info("Loaded edge shape: %s", edges.shape)

    log_section("FILTER EDGES")

    edges_filtered = edges[edges["email_count"] >= MIN_EMAIL_COUNT].copy()

    logger.info("Filtered edge shape: %s", edges_filtered.shape)
    logger.info("Unique sources: %s", f"{edges_filtered['source'].nunique():,}")
    logger.info("Unique targets: %s", f"{edges_filtered['target'].nunique():,}")

    log_section("BUILD DIRECTED GRAPH")

    graph = nx.DiGraph()

    for row in edges_filtered.itertuples(index=False):
        graph.add_edge(
            row.source,
            row.target,
            weight=row.email_count,
            risky_email_count=row.risky_email_count,
            avg_risk_phrase_score=row.avg_risk_phrase_score,
            risky_email_pct=row.risky_email_pct,
        )

    logger.info("Graph nodes: %s", f"{graph.number_of_nodes():,}")
    logger.info("Graph edges: %s", f"{graph.number_of_edges():,}")

    log_section("COMPUTE BASIC DEGREES")

    in_degree = dict(graph.in_degree(weight="weight"))
    out_degree = dict(graph.out_degree(weight="weight"))
    total_degree = {
        node: in_degree.get(node, 0) + out_degree.get(node, 0)
        for node in graph.nodes()
    }

    in_connections = dict(graph.in_degree())
    out_connections = dict(graph.out_degree())
    total_connections = {
        node: in_connections.get(node, 0) + out_connections.get(node, 0)
        for node in graph.nodes()
    }

    logger.info("Degree metrics computed")

    log_section("COMPUTE CENTRALITY METRICS")

    # These are unweighted and relatively safe on the filtered graph.
    degree_centrality = nx.degree_centrality(graph)
    in_degree_centrality = nx.in_degree_centrality(graph)
    out_degree_centrality = nx.out_degree_centrality(graph)

    logger.info("Degree centrality computed")

    # Betweenness can be expensive on large graphs.
    # We compute approximate betweenness for practical runtime.
    logger.info("Computing approximate betweenness centrality")

    betweenness_centrality = nx.betweenness_centrality(
        graph,
        k=min(1000, graph.number_of_nodes()),
        normalized=True,
        weight=None,
        seed=42,
    )

    logger.info("Approximate betweenness centrality computed")

    log_section("COMPUTE RISK FLOW METRICS")

    risk_out = {}
    risk_in = {}

    for source, target, data in graph.edges(data=True):
        risky_count = data.get("risky_email_count", 0)

        risk_out[source] = risk_out.get(source, 0) + risky_count
        risk_in[target] = risk_in.get(target, 0) + risky_count

    log_section("CREATE NODE METRICS TABLE")

    records = []

    for node in graph.nodes():
        records.append(
            {
                "node": node,
                "weighted_in_email_count": in_degree.get(node, 0),
                "weighted_out_email_count": out_degree.get(node, 0),
                "weighted_total_email_count": total_degree.get(node, 0),
                "in_connection_count": in_connections.get(node, 0),
                "out_connection_count": out_connections.get(node, 0),
                "total_connection_count": total_connections.get(node, 0),
                "degree_centrality": degree_centrality.get(node, 0),
                "in_degree_centrality": in_degree_centrality.get(node, 0),
                "out_degree_centrality": out_degree_centrality.get(node, 0),
                "betweenness_centrality": betweenness_centrality.get(node, 0),
                "risky_emails_sent": risk_out.get(node, 0),
                "risky_emails_received": risk_in.get(node, 0),
            }
        )

    metrics = pd.DataFrame(records)

    metrics["risky_email_total"] = (
        metrics["risky_emails_sent"]
        + metrics["risky_emails_received"]
    )

    metrics["network_activity_rank"] = (
        metrics["weighted_total_email_count"]
        .rank(method="dense", ascending=False)
        .astype(int)
    )

    metrics["betweenness_rank"] = (
        metrics["betweenness_centrality"]
        .rank(method="dense", ascending=False)
        .astype(int)
    )

    metrics = metrics.sort_values(
        [
            "weighted_total_email_count",
            "betweenness_centrality",
            "risky_email_total",
        ],
        ascending=False,
    )

    logger.info("Metrics shape: %s", metrics.shape)

    log_section("TOP NETWORK NODES")

    top_cols = [
        "node",
        "weighted_total_email_count",
        "weighted_in_email_count",
        "weighted_out_email_count",
        "total_connection_count",
        "betweenness_centrality",
        "risky_email_total",
    ]

    logger.info("\n%s", metrics[top_cols].head(25).to_string(index=False))

    top_file = OUTPUT_DIR / "top_network_nodes.csv"
    metrics[top_cols].head(100).to_csv(top_file, index=False)

    logger.info("Saved top nodes: %s", top_file)

    log_section("WRITE OUTPUT")

    metrics.to_parquet(OUTPUT_FILE, index=False)

    logger.info("Saved output: %s", OUTPUT_FILE)
    logger.info("Output shape: %s", metrics.shape)

    log_section("NETWORK METRICS COMPLETED")


if __name__ == "__main__":
    main()