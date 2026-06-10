"""OpenAlex Works API client."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from paperpilot.models import Paper


OPENALEX_WORKS_URL = "https://api.openalex.org/works"


class OpenAlexSearchError(RuntimeError):
    """Raised when OpenAlex search cannot be completed."""


class OpenAlexSearchClient:
    """Small OpenAlex works search client returning normalized papers."""

    def __init__(
        self,
        base_url: str = OPENALEX_WORKS_URL,
        timeout: float = 20.0,
        user_agent: str = "paperpilot/0.1",
        mailto: str | None = None,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.user_agent = user_agent
        self.mailto = mailto if mailto is not None else os.environ.get("OPENALEX_MAILTO")

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

        cutoff = _as_utc(now) - timedelta(days=days)
        params = {
            "search": query,
            "per-page": max_results,
            "sort": "publication_date:desc",
            "filter": f"from_publication_date:{cutoff.date().isoformat()}",
        }
        if self.mailto:
            params["mailto"] = self.mailto
        request = Request(
            f"{self.base_url}?{urlencode(params)}",
            headers={"User-Agent": self.user_agent},
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise OpenAlexSearchError(f"OpenAlex request failed with HTTP {exc.code}: {body}") from exc
        except (OSError, URLError, json.JSONDecodeError) as exc:
            raise OpenAlexSearchError(f"OpenAlex request failed: {exc}") from exc

        return parse_openalex_response(payload, days=days, max_results=max_results, now=_as_utc(now))


def parse_openalex_response(
    payload: dict,
    *,
    days: int,
    max_results: int,
    now: datetime,
) -> tuple[Paper, ...]:
    cutoff = _as_utc(now) - timedelta(days=days)
    results = payload.get("results")
    if not isinstance(results, list):
        return ()

    papers: list[Paper] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        paper = _parse_work(item)
        if paper and paper.published >= cutoff:
            papers.append(paper)
        if len(papers) >= max_results:
            break
    return tuple(papers)


def _parse_work(item: dict) -> Paper | None:
    title = _clean_text(item.get("display_name") or item.get("title"))
    if not title:
        return None
    published = _publication_datetime(item)
    if not published:
        return None

    best_oa_location = item.get("best_oa_location") if isinstance(item.get("best_oa_location"), dict) else {}
    primary_location = item.get("primary_location") if isinstance(item.get("primary_location"), dict) else {}
    return Paper(
        title=title,
        authors=_authors(item.get("authorships")),
        summary=_abstract_text(item.get("abstract_inverted_index")),
        published=published,
        updated=None,
        url=_clean_text(item.get("doi")) or _location_url(best_oa_location) or _clean_text(item.get("id")),
        pdf_url=_pdf_url(best_oa_location) or _pdf_url(primary_location),
        categories=_topics(item),
        source_id=f"openalex:{item.get('id')}" if item.get("id") else None,
        source="openalex",
        doi=_clean_doi(item.get("doi")),
        citation_count=_int_or_none(item.get("cited_by_count")),
        venue=_venue(best_oa_location) or _venue(primary_location),
    )


def _publication_datetime(item: dict) -> datetime | None:
    publication_date = _clean_text(item.get("publication_date"))
    if publication_date:
        try:
            return datetime.fromisoformat(publication_date).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    year = _int_or_none(item.get("publication_year"))
    if year:
        return datetime(year, 1, 1, tzinfo=timezone.utc)
    return None


def _abstract_text(index) -> str:
    if not isinstance(index, dict):
        return ""
    positions: dict[int, str] = {}
    for word, values in index.items():
        if not isinstance(values, list):
            continue
        for position in values:
            if isinstance(position, int):
                positions[position] = str(word)
    return " ".join(positions[position] for position in sorted(positions))


def _authors(value) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    authors: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        author = item.get("author")
        if isinstance(author, dict):
            name = _clean_text(author.get("display_name"))
            if name:
                authors.append(name)
    return tuple(authors)


def _topics(item: dict) -> tuple[str, ...]:
    topics = item.get("topics")
    if not isinstance(topics, list):
        return ()
    names: list[str] = []
    for topic in topics[:5]:
        if isinstance(topic, dict):
            name = _clean_text(topic.get("display_name"))
            if name:
                names.append(name)
    return tuple(names)


def _pdf_url(location: dict) -> str | None:
    return _clean_text(location.get("pdf_url")) or None


def _location_url(location: dict) -> str | None:
    return _clean_text(location.get("landing_page_url")) or None


def _venue(location: dict) -> str | None:
    source = location.get("source")
    if isinstance(source, dict):
        return _clean_text(source.get("display_name")) or None
    return None


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
