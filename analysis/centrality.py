"""
Citation network centrality analysis using networkx.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

import networkx as nx
import psycopg2


def get_conn():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "research_pulse"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", "postgres"),
    )


def build_graph(conn) -> nx.DiGraph:
    G = nx.DiGraph()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT paper_id, arxiv_id, title FROM raw_papers WHERE s2_id IS NOT NULL"
        )
        for row in cur.fetchall():
            G.add_node(row[0], arxiv_id=row[1], title=row[2])

        cur.execute("SELECT citing_paper_id, cited_paper_id FROM paper_citations")
        for row in cur.fetchall():
            G.add_edge(row[0], row[1])
    return G


def compute_centrality(G: nx.DiGraph) -> list[dict]:
    if len(G.nodes) == 0:
        return []

    pagerank = nx.pagerank(G)
    betweenness = nx.betweenness_centrality(G)
    in_degree = dict(G.in_degree())
    out_degree = dict(G.out_degree())

    results = []
    for node in G.nodes():
        results.append(
            {
                "paper_id": node,
                "arxiv_id": G.nodes[node].get("arxiv_id", ""),
                "title": G.nodes[node].get("title", ""),
                "pagerank": round(pagerank.get(node, 0), 6),
                "betweenness": round(betweenness.get(node, 0), 6),
                "in_degree": in_degree.get(node, 0),
                "out_degree": out_degree.get(node, 0),
            }
        )
    return results


def save_results(results: list[dict], conn) -> None:
    with conn.cursor() as cur:
        for r in results:
            cur.execute(
                """
                INSERT INTO paper_centrality 
                (paper_id, arxiv_id, title, pagerank, betweenness, in_degree, out_degree)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (paper_id) DO UPDATE SET
                    arxiv_id = EXCLUDED.arxiv_id,
                    title = EXCLUDED.title,
                    pagerank = EXCLUDED.pagerank,
                    betweenness = EXCLUDED.betweenness,
                    in_degree = EXCLUDED.in_degree,
                    out_degree = EXCLUDED.out_degree,
                    computed_at = now()
                """,
                (
                    r["paper_id"],
                    r["arxiv_id"],
                    r["title"],
                    r["pagerank"],
                    r["betweenness"],
                    r["in_degree"],
                    r["out_degree"],
                ),
            )
        conn.commit()


def export_csv(results: list[dict], path: str = "analysis/centrality.csv") -> None:
    if not results:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)


def run_centrality(export: bool = False) -> None:
    conn = get_conn()
    try:
        print("Building citation graph...")
        G = build_graph(conn)
        print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

        if G.number_of_nodes() == 0:
            print("No citation data available. Run enrichment with --fetch-edges first.")
            return

        print("Computing centrality metrics...")
        results = compute_centrality(G)

        print("Saving to database...")
        save_results(results, conn)

        if export:
            export_csv(results)
            print("Exported to analysis/centrality.csv")

        print(f"Done. Processed {len(results)} papers.")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", action="store_true", help="Also export to CSV")
    args = parser.parse_args()

    try:
        run_centrality(export=args.export)
    except Exception as e:
        print(f"Centrality analysis failed: {e}", file=sys.stderr)
        sys.exit(1)