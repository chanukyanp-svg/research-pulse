"""
Thin client for Semantic Scholar (S2) API.

Docs: https://api.semanticscholar.org/graph/v1
Free tier: 100 requests / 5 min without key (~1 req / 3 s).
With API key: much higher limits. Set S2_API_KEY env var if you have one.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

S2_API_BASE = "https://api.semanticscholar.org/graph/v1"
S2_API_KEY = os.environ.get("S2_API_KEY")


@dataclass(frozen=True)
class S2Paper:
    arxiv_id: str
    s2_id: str
    title: str
    citation_count: int
    reference_count: int
    year: int | None = None
    venue: str | None = None


@dataclass(frozen=True)
class CitationEdge:
    citing_s2_id: str
    cited_s2_id: str
    arxiv_id: str | None = None


def _request(
    url: str,
    data: bytes | None = None,
    method: str = "GET",
    retries: int = 3,
) -> Any:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if S2_API_KEY:
        headers["x-api-key"] = S2_API_KEY

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            time.sleep(0.2 if S2_API_KEY else 3.0)
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            raise
        except Exception as e:
            last_err = e
            time.sleep(2 ** attempt)

    raise RuntimeError(f"S2 request failed after {retries} attempts: {url}") from last_err


def _parse_paper_details_response(response: list[dict | None]) -> list[S2Paper]:
    papers: list[S2Paper] = []
    for item in response:
        if item is None:
            continue

        external_ids = item.get("externalIds") or {}
        arxiv_id = external_ids.get("ArXiv", "")
        if not arxiv_id:
            continue

        papers.append(
            S2Paper(
                arxiv_id=arxiv_id,
                s2_id=item.get("paperId", ""),
                title=item.get("title", ""),
                citation_count=item.get("citationCount", 0) or 0,
                reference_count=item.get("referenceCount", 0) or 0,
                year=item.get("year"),
                venue=item.get("venue"),
            )
        )
    return papers


def fetch_paper_details(arxiv_ids: list[str]) -> list[S2Paper]:
    if not arxiv_ids:
        return []

    # Strip version suffix (e.g. "2501.01234v1" -> "2501.01234")
    # S2 expects "ArXiv:2501.01234" (capital A, lowercase xiv)
    clean_ids = []
    for aid in arxiv_ids:
        if not aid:
            continue
        base = aid.split("v")[0]
        clean_ids.append(f"ArXiv:{base}")

    if not clean_ids:
        return []

    fields = "paperId,title,citationCount,referenceCount,year,venue,externalIds"
    url = f"{S2_API_BASE}/paper/batch?fields={fields}"

    payload = json.dumps({"ids": clean_ids}).encode("utf-8")
    response = _request(url, data=payload, method="POST")
    return _parse_paper_details_response(response)


def fetch_citations(s2_paper_id: str, limit: int = 100) -> list[CitationEdge]:
    if not s2_paper_id:
        return []

    edges: list[CitationEdge] = []
    offset = 0
    fields = "paperId,externalIds"

    while True:
        url = (
            f"{S2_API_BASE}/paper/{s2_paper_id}/citations"
            f"?fields={fields}&limit={limit}&offset={offset}"
        )
        response = _request(url)
        data = response.get("data", [])
        if not data:
            break

        for item in data:
            citing = item.get("citingPaper", {})
            if not citing:
                continue
            ext = citing.get("externalIds") or {}
            edges.append(
                CitationEdge(
                    citing_s2_id=citing.get("paperId", ""),
                    cited_s2_id=s2_paper_id,
                    arxiv_id=ext.get("ArXiv"),
                )
            )

        if len(data) < limit:
            break
        offset += limit

    return edges


def fetch_references(s2_paper_id: str, limit: int = 100) -> list[CitationEdge]:
    if not s2_paper_id:
        return []

    edges: list[CitationEdge] = []
    offset = 0
    fields = "paperId,externalIds"

    while True:
        url = (
            f"{S2_API_BASE}/paper/{s2_paper_id}/references"
            f"?fields={fields}&limit={limit}&offset={offset}"
        )
        response = _request(url)
        data = response.get("data", [])
        if not data:
            break

        for item in data:
            cited = item.get("citedPaper", {})
            if not cited:
                continue
            ext = cited.get("externalIds") or {}
            edges.append(
                CitationEdge(
                    citing_s2_id=s2_paper_id,
                    cited_s2_id=cited.get("paperId", ""),
                    arxiv_id=ext.get("ArXiv"),
                )
            )

        if len(data) < limit:
            break
        offset += limit

    return edges