"""
Unit tests for centrality analysis using mock citation graphs.
No database or network required.
"""
from __future__ import annotations

import unittest

import networkx as nx

from analysis.centrality import compute_centrality


class TestCentrality(unittest.TestCase):
    def test_empty_graph(self) -> None:
        G = nx.DiGraph()
        results = compute_centrality(G)
        self.assertEqual(results, [])

    def test_simple_chain(self) -> None:
        G = nx.DiGraph()
        G.add_node(1, arxiv_id="2101.00001", title="A")
        G.add_node(2, arxiv_id="2101.00002", title="B")
        G.add_node(3, arxiv_id="2101.00003", title="C")
        G.add_edge(1, 2)
        G.add_edge(2, 3)

        results = compute_centrality(G)
        self.assertEqual(len(results), 3)

        by_id = {r["paper_id"]: r for r in results}
        self.assertGreater(by_id[2]["betweenness"], by_id[1]["betweenness"])
        self.assertGreater(by_id[2]["betweenness"], by_id[3]["betweenness"])

        self.assertEqual(by_id[1]["in_degree"], 0)
        self.assertEqual(by_id[2]["in_degree"], 1)
        self.assertEqual(by_id[3]["in_degree"], 1)

    def test_star_graph(self) -> None:
        G = nx.DiGraph()
        for i in range(1, 5):
            G.add_node(i, arxiv_id=f"2101.0000{i}", title=f"Paper {i}")

        for i in range(2, 5):
            G.add_edge(i, 1)

        results = compute_centrality(G)
        by_id = {r["paper_id"]: r for r in results}

        self.assertEqual(by_id[1]["in_degree"], 3)
        self.assertGreater(by_id[1]["pagerank"], by_id[2]["pagerank"])


if __name__ == "__main__":
    unittest.main()