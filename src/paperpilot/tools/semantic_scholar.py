"""Semantic Scholar Academic Graph API client."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from paperpilot.models import Paper


SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_FIELDS = ",".join(
    (
        "paperId",
        "title",
        "abstract",
        "authors",
        "url",
        "publicationDate",
        "year",
        "openAccessPdf",
        "externalIds",
        "citationCount",
        "venue",
        "fieldsOfStudy",
    )
)


class SemanticScholarSearchError(RuntimeError):
    """Raised when Semantic Scholar search cannot be completed."""


class SemanticScholarSearchClient:
    """Small Semantic Scholar search client returning normalized papers."""

    def __init__(
        self,
        base_url: str = SEMANTIC_SCHOLAR_API_URL,
        timeout: float = 20.0,
        user_agent: str = "paperpilot/0.1",
        api_key: str | None = None,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.user_agent = user_agent
        self.api_key = api_key if api_key is not None else os.environ.get("SEMANTIC_SCHOLAR_API_KEY")

    def search(
        self,
        query: str,
        *,
        days: int = 7,
        max_results: int = 20,
        categories: tuple[str, ...] | list[str] = (),
        strict_search: bool = True,
        now: datetime | None = None,
    ) -> tuple[Paper, ...]:
        if days < 1:
            raise ValueError("days must be at least 1")
        if max_results < 1:
            raise ValueError("max_results must be at least 1")

        params = urlencode(
            {
                "query": query,
                "limit": max_results,
                "fields": SEMANTIC_SCHOLAR_FIELDS,
            }
        )
        headers = {"User-Agent": self.user_agent}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        request = Request(f"{self.base_url}?{params}", headers=headers)

        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise SemanticScholarSearchError(f"Semantic Scholar request failed with HTTP {exc.code}: {body}") from exc
        except (OSError, URLError, json.JSONDecodeError) as exc:
            raise SemanticScholarSearchError(f"Semantic Scholar request failed: {exc}") from exc

        return parse_semantic_scholar_response(payload, days=days, max_results=max_results, now=_as_utc(now))


def parse_semantic_scholar_response(
    payload: dict,
    *,
    days: int,
    max_results: int,
    now: datetime,
) -> tuple[Paper, ...]:
    cutoff = _as_utc(now) - timedelta(days=days)
    data = payload.get("data")
    if not isinstance(data, list):
        return ()

    papers: list[Paper] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        paper = _parse_paper(item)
        if paper and paper.published >= cutoff:
            papers.append(paper)
        if len(papers) >= max_results:
            break
    return tuple(papers)


def _parse_paper(item: dict) -> Paper | None:
    title = _clean_text(item.get("title"))
    if not title:
        return None
    published = _publication_datetime(item)
    if not published:
        return None

    external_ids = item.get("externalIds") if isinstance(item.get("externalIds"), dict) else {}
    open_access_pdf = item.get("openAccessPdf") if isinstance(item.get("openAccessPdf"), dict) else {}
    fields = item.get("fieldsOfStudy") if isinstance(item.get("fieldsOfStudy"), list) else []
    return Paper(
        title=title,
        authors=_authors(item.get("authors")),
        summary=_clean_text(item.get("abstract")),
        published=published,
        updated=None,
        url=_clean_text(item.get("url")) or _semantic_scholar_url(item.get("paperId")),
        pdf_url=_clean_text(open_access_pdf.get("url")),
        categories=tuple(str(field) for field in fields if field),
        source_id=f"semantic-scholar:{item.get('paperId')}" if item.get("paperId") else None,
        source="semantic-scholar",
        doi=_clean_doi(external_ids.get("DOI")),
        citation_count=_int_or_none(item.get("citationCount")),
        venue=_clean_text(item.get("venue")),
    )


def _publication_datetime(item: dict) -> datetime | None:
    publication_date = _clean_text(item.get("publicationDate"))
    if publication_date:
        try:
            return datetime.fromisoformat(publication_date).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    year = _int_or_none(item.get("year"))
    if year:
        return datetime(year, 1, 1, tzinfo=timezone.utc)
    return None


def _authors(value) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    authors: list[str] = []
    for item in value:
        if isinstance(item, dict):
            name = _clean_text(item.get("name"))
            if name:
                authors.append(name)
    return tuple(authors)


def _semantic_scholar_url(paper_id) -> str:
    return f"https://www.semanticscholar.org/paper/{paper_id}" if paper_id else ""


def _clean_doi(value) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    return text.removeprefix("https://doi.org/").removeprefix("doi:").lower()


def _clean_text(value) -> str:
    return " ".join(str(value).split()) if value else ""


def _int_or_none(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
