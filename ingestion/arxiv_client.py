"""
Thin client for arXiv's public Atom API.

Docs: https://info.arxiv.org/help/api/user-manual.html
No API key required. Be polite: arXiv asks for <= 1 request per 3 seconds
and a max of ~2000 results per query (use pagination via `start` for more).
"""
from __future__ import annotations

import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime

ARXIV_API_URL = "http://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


@dataclass
class Paper:
    arxiv_id: str          # e.g. "2501.01234v1"
    title: str
    abstract: str
    authors: list[str]
    published_date: datetime
    updated_date: datetime
    categories: list[str]
    primary_category: str
    source: str = "arxiv"


def _clean(text: str | None) -> str:
    return " ".join((text or "").split())


def _parse_entry(entry: ET.Element) -> Paper:
    raw_id = _clean(entry.findtext(f"{ATOM_NS}id"))
    arxiv_id = raw_id.rsplit("/abs/", 1)[-1] if raw_id else ""

    authors = [
        _clean(a.findtext(f"{ATOM_NS}name"))
        for a in entry.findall(f"{ATOM_NS}author")
    ]
    categories = [
        c.get("term", "") for c in entry.findall(f"{ATOM_NS}category")
    ]
    primary = entry.find(f"{ARXIV_NS}primary_category")
    primary_category = primary.get("term", "") if primary is not None else (
        categories[0] if categories else ""
    )

    def _parse_date(tag: str) -> datetime:
        raw = entry.findtext(f"{ATOM_NS}{tag}")
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ") if raw else datetime.min

    return Paper(
        arxiv_id=arxiv_id,
        title=_clean(entry.findtext(f"{ATOM_NS}title")),
        abstract=_clean(entry.findtext(f"{ATOM_NS}summary")),
        authors=authors,
        published_date=_parse_date("published"),
        updated_date=_parse_date("updated"),
        categories=categories,
        primary_category=primary_category,
    )


def fetch_papers(
    search_query: str,
    max_results: int = 100,
    start: int = 0,
    sort_by: str = "submittedDate",
    sort_order: str = "descending",
    _retries: int = 3,
) -> list[Paper]:
    """
    Fetch papers matching an arXiv search query.

    search_query examples:
      - 'cat:q-bio.NC AND abs:EEG'
      - 'abs:"brain-computer interface" AND abs:fNIRS'
      - 'cat:quant-ph AND abs:"quantum machine learning"'

    See https://info.arxiv.org/help/api/user-manual.html#query_details
    for the full query grammar (field prefixes, AND/OR/ANDNOT, phrase quoting).
    """
    params = {
        "search_query": search_query,
        "start": start,
        "max_results": max_results,
        "sortBy": sort_by,
        "sortOrder": sort_order,
    }
    url = f"{ARXIV_API_URL}?{urllib.parse.urlencode(params)}"

    last_err: Exception | None = None
    for attempt in range(_retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                raw = resp.read()
            break
        except Exception as e:  # noqa: BLE001 - arXiv occasionally 503s under load
            last_err = e
            time.sleep(3 * (attempt + 1))
    else:
        raise RuntimeError(f"arXiv request failed after {_retries} attempts") from last_err

    root = ET.fromstring(raw)
    entries = root.findall(f"{ATOM_NS}entry")
    return [_parse_entry(e) for e in entries]


def fetch_all(search_query: str, page_size: int = 100, max_total: int = 1000) -> list[Paper]:
    """Paginate through results, respecting arXiv's rate-limit etiquette."""
    papers: list[Paper] = []
    start = 0
    while start < max_total:
        batch = fetch_papers(search_query, max_results=page_size, start=start)
        if not batch:
            break
        papers.extend(batch)
        start += page_size
        time.sleep(3)  # be polite between paginated calls
    return papers
