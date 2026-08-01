"""
Unit tests for arxiv_client parsing logic, run against a saved fixture
so tests don't depend on network access to export.arxiv.org.
"""
import pathlib
import xml.etree.ElementTree as ET

from ingestion.arxiv_client import _parse_entry, ATOM_NS

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "sample_response.xml"


def _load_entries():
    root = ET.fromstring(FIXTURE.read_text())
    return root.findall(f"{ATOM_NS}entry")


def test_parses_expected_number_of_entries():
    entries = _load_entries()
    assert len(entries) == 2


def test_parses_paper_fields_correctly():
    entries = _load_entries()
    paper = _parse_entry(entries[0])

    assert paper.arxiv_id == "2501.01234v1"
    assert paper.title == "Cross-Subject EEG-fNIRS Fusion via Self-Supervised Contrastive Learning"
    assert paper.authors == ["Jane A. Smith", "Rahul Mehta", "Wei Chen"]
    assert paper.primary_category == "q-bio.NC"
    assert "cs.LG" in paper.categories
    assert paper.published_date.year == 2025
    assert paper.published_date.month == 1
    assert "contrastive" in paper.abstract.lower()


def test_second_entry_quantum_paper():
    entries = _load_entries()
    paper = _parse_entry(entries[1])

    assert paper.arxiv_id == "2412.09876v2"
    assert paper.primary_category == "quant-ph"
    assert paper.authors == ["Alex Turner", "Priya Nair"]


if __name__ == "__main__":
    test_parses_expected_number_of_entries()
    test_parses_paper_fields_correctly()
    test_second_entry_quantum_paper()
    print("All tests passed.")
