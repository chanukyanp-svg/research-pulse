"""
Unit tests for Semantic Scholar response parsing.
Zero network calls — everything runs against saved JSON fixtures.
"""
from __future__ import annotations

import json
import pathlib
import unittest

from enrichment.s2_client import _parse_paper_details_response, S2Paper


class TestS2Parsing(unittest.TestCase):
    def setUp(self) -> None:
        fixture_path = (
            pathlib.Path(__file__).parent / "fixtures" / "s2_batch_response.json"
        )
        self.fixture = json.loads(fixture_path.read_text())

    def test_parses_known_papers(self) -> None:
        papers = _parse_paper_details_response(self.fixture)
        self.assertEqual(len(papers), 2)

        self.assertEqual(papers[0].arxiv_id, "2101.00027")
        self.assertEqual(papers[0].s2_id, "649def34f8be52c8b66281af98ae884c09aef38b")
        self.assertEqual(papers[0].citation_count, 42)
        self.assertEqual(papers[0].reference_count, 30)
        self.assertEqual(papers[0].year, 2021)
        self.assertEqual(papers[0].venue, "ICML")

        self.assertEqual(papers[1].arxiv_id, "2102.00001")
        self.assertEqual(papers[1].citation_count, 0)
        self.assertEqual(papers[1].reference_count, 15)
        self.assertIsNone(papers[1].venue)

    def test_skips_null_entries(self) -> None:
        papers = _parse_paper_details_response(self.fixture)
        arxiv_ids = {p.arxiv_id for p in papers}
        self.assertNotIn("noarxiv999", arxiv_ids)

    def test_empty_response(self) -> None:
        papers = _parse_paper_details_response([])
        self.assertEqual(papers, [])

    def test_all_null_response(self) -> None:
        papers = _parse_paper_details_response([None, None])
        self.assertEqual(papers, [])


if __name__ == "__main__":
    unittest.main()