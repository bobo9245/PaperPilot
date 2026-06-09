"""Search agent with observation logging and lightweight replanning."""

from __future__ import annotations

import re
from collections.abc import Callable

from paperpilot.models import Paper, SearchAttempt, SearchResult
from paperpilot.tools.arxiv import ArxivSearchError


SearchFunction = Callable[..., tuple[Paper, ...]]


class SearcherAgent:
    """Run paper search and broaden the query when the first attempt is weak."""

    def __init__(
        self,
        search: SearchFunction,
        *,
        min_results: int = 3,
        max_replans: int = 2,
    ) -> None:
        self.search = search
        self.min_results = min_results
        self.max_replans = max_replans

    def run(
        self,
        query: str,
        *,
        days: int,
        max_results: int,
        categories: tuple[str, ...] | list[str] = (),
        strict_search: bool = True,
    ) -> SearchResult:
        attempts: list[SearchAttempt] = []
        papers_by_key: dict[str, Paper] = {}

        for candidate in self._query_plan(query):
            try:
                papers = self.search(
                    candidate,
                    days=days,
                    max_results=max_results,
                    categories=categories,
                    strict_search=strict_search,
                )
            except (ArxivSearchError, OSError, ValueError) as exc:
                attempts.append(
                    SearchAttempt(
                        query=candidate,
                        status="error",
                        results_count=0,
                        message=str(exc),
                    )
                )
                continue

            for paper in papers:
                papers_by_key.setdefault(_paper_key(paper), paper)

            status = "success" if len(papers) >= self.min_results else "too_few_results"
            attempts.append(
                SearchAttempt(
                    query=candidate,
                    status=status,
                    results_count=len(papers),
                    message=(
                        "Enough recent candidates found."
                        if status == "success"
                        else "Too few recent candidates; replanning with a broader query."
                    ),
                )
            )

            if len(papers_by_key) >= self.min_results:
                break

        return SearchResult(
            original_query=query,
            papers=tuple(papers_by_key.values())[:max_results],
            attempts=tuple(attempts),
        )

    def _query_plan(self, query: str) -> tuple[str, ...]:
        candidates = [query]
        for candidate in propose_broader_queries(query):
            if candidate not in candidates:
                candidates.append(candidate)
            if len(candidates) >= self.max_replans + 1:
                break
        return tuple(candidates)


def propose_broader_queries(query: str) -> tuple[str, ...]:
    """Create deterministic broader query candidates from a specific query."""

    terms = [
        term
        for term in re.findall(r"[A-Za-z0-9]+", query.lower())
        if term not in _STOPWORDS and len(term) > 1
    ]
    if not terms:
        return (query,)

    candidates: list[str] = []
    if len(terms) > 3:
        candidates.append(" ".join(terms[:3]))
    if len(terms) > 2:
        candidates.append(" ".join(terms[:2]))
    if terms:
        candidates.append(terms[0])

    return tuple(candidate for candidate in candidates if candidate and candidate != query.lower())


def _paper_key(paper: Paper) -> str:
    return paper.source_id or paper.url or paper.title.lower()


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
