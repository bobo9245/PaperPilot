"""arXiv Atom API client."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable
from urllib.error import URLError
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from paperpilot.models import Paper


ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivSearchError(RuntimeError):
    """Raised when arXiv search cannot be completed."""


class ArxivSearchClient:
    """Small arXiv search client that returns normalized papers."""

    def __init__(
        self,
        base_url: str = ARXIV_API_URL,
        timeout: float = 20.0,
        user_agent: str = "paperpilot/0.1",
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.user_agent = user_agent

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
        """Search arXiv and keep papers published within the requested window."""

        if days < 1:
            raise ValueError("days must be at least 1")
        if max_results < 1:
            raise ValueError("max_results must be at least 1")

        search_query = build_arxiv_search_query(
            query,
            categories=categories,
            strict_search=strict_search,
        )
        params = urlencode(
            {
                "search_query": search_query,
                "start": 0,
                "max_results": max_results,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
        )
        request = Request(
            f"{self.base_url}?{params}",
            headers={"User-Agent": self.user_agent},
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = response.read()
        except URLError as exc:
            raise ArxivSearchError(f"arXiv request failed: {exc}") from exc
        except OSError as exc:
            raise ArxivSearchError(f"arXiv request failed: {exc}") from exc

        cutoff = _as_utc(now) - timedelta(days=days)
        try:
            root = ElementTree.fromstring(payload)
        except ElementTree.ParseError as exc:
            raise ArxivSearchError(f"arXiv response was not valid Atom XML: {exc}") from exc

        papers = [
            paper
            for paper in (_parse_entry(entry) for entry in root.findall("atom:entry", ATOM_NS))
            if paper.published >= cutoff
        ]
        return tuple(papers[:max_results])


def build_arxiv_search_query(
    query: str,
    *,
    categories: tuple[str, ...] | list[str] = (),
    strict_search: bool = True,
) -> str:
    """Build an arXiv search expression for a human research query."""

    terms = _search_terms(query)
    if not terms:
        raise ValueError("query must contain at least one searchable term")

    if strict_search:
        expression = _strict_title_abstract_expression(terms)
    else:
        expression = " AND ".join(f"all:{term}" for term in terms)

    category_terms = tuple(category.strip() for category in categories if category.strip())
    if category_terms:
        category_expression = " OR ".join(f"cat:{category}" for category in category_terms)
        expression = f"({expression}) AND ({category_expression})"

    return expression


def _strict_title_abstract_expression(terms: tuple[str, ...]) -> str:
    if len(terms) == 1:
        term = terms[0]
        return f"(ti:{term} OR abs:{term})"

    phrase = " ".join(terms)
    exact_phrase = f'ti:"{phrase}" OR abs:"{phrase}"'
    title_terms = " AND ".join(f"ti:{term}" for term in terms)
    abstract_terms = " AND ".join(f"abs:{term}" for term in terms)
    mixed_terms = " AND ".join(f"(ti:{term} OR abs:{term})" for term in terms)
    return f"({exact_phrase} OR ({title_terms}) OR ({abstract_terms}) OR ({mixed_terms}))"


def _search_terms(query: str) -> tuple[str, ...]:
    seen: set[str] = set()
    terms: list[str] = []
    for term in re.findall(r"[A-Za-z0-9]+", query.lower()):
        if len(term) <= 1 or term in _STOPWORDS or term in seen:
            continue
        seen.add(term)
        terms.append(term)
    return tuple(terms)


def _parse_entry(entry: ElementTree.Element) -> Paper:
    title = _clean_text(_required_text(entry, "atom:title"))
    summary = _clean_text(_required_text(entry, "atom:summary"))
    published = _parse_datetime(_required_text(entry, "atom:published"))
    updated_text = _optional_text(entry, "atom:updated")
    updated = _parse_datetime(updated_text) if updated_text else None
    source_id = _optional_text(entry, "atom:id")
    authors = tuple(
        _clean_text(author.findtext("atom:name", default="", namespaces=ATOM_NS))
        for author in entry.findall("atom:author", ATOM_NS)
    )
    authors = tuple(author for author in authors if author)
    categories = tuple(
        category.attrib.get("term", "")
        for category in entry.findall("atom:category", ATOM_NS)
        if category.attrib.get("term")
    )
    links = _entry_links(entry)
    return Paper(
        title=title,
        authors=authors,
        summary=summary,
        published=published,
        updated=updated,
        url=links.get("abstract") or source_id or "",
        pdf_url=links.get("pdf"),
        categories=categories,
        source_id=source_id,
    )


def _entry_links(entry: ElementTree.Element) -> dict[str, str]:
    links: dict[str, str] = {}
    for link in entry.findall("atom:link", ATOM_NS):
        href = link.attrib.get("href")
        if not href:
            continue
        title = link.attrib.get("title")
        rel = link.attrib.get("rel")
        if title == "pdf":
            links["pdf"] = href
        elif rel == "alternate":
            links["abstract"] = href
    return links


def _required_text(entry: ElementTree.Element, path: str) -> str:
    value = _optional_text(entry, path)
    if value is None:
        raise ArxivSearchError(f"arXiv entry is missing {path}")
    return value


def _optional_text(entry: ElementTree.Element, path: str) -> str | None:
    text = entry.findtext(path, namespaces=ATOM_NS)
    return text.strip() if text else None


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def parse_arxiv_atom(payload: bytes | str, *, days: int, max_results: int, now: datetime) -> tuple[Paper, ...]:
    """Parse an arXiv Atom payload; useful for focused tests."""

    text = payload.encode() if isinstance(payload, str) else payload
    root = ElementTree.fromstring(text)
    cutoff = _as_utc(now) - timedelta(days=days)
    papers: Iterable[Paper] = (_parse_entry(entry) for entry in root.findall("atom:entry", ATOM_NS))
    return tuple(paper for paper in papers if paper.published >= cutoff)[:max_results]


_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}
