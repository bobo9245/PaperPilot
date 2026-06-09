from __future__ import annotations

from paperpilot.agents.searcher import SearcherAgent, propose_broader_queries
from paperpilot.tools.arxiv import ArxivSearchError


def test_propose_broader_queries_removes_specificity() -> None:
    assert propose_broader_queries("retrieval augmented generation systems") == (
        "retrieval augmented generation",
        "retrieval augmented",
        "retrieval",
    )


def test_searcher_replans_when_results_are_too_few(make_paper) -> None:
    calls: list[str] = []

    def fake_search(query: str, *, days: int, max_results: int, **kwargs):
        calls.append(query)
        if query == "retrieval augmented generation systems":
            return (make_paper(source_id="one"),)
        return (make_paper(source_id="two"), make_paper(source_id="three"))

    agent = SearcherAgent(fake_search, min_results=2, max_replans=2)
    result = agent.run("retrieval augmented generation systems", days=7, max_results=10)

    assert calls == ["retrieval augmented generation systems", "retrieval augmented generation"]
    assert [attempt.status for attempt in result.attempts] == ["too_few_results", "success"]
    assert len(result.papers) == 3


def test_searcher_replans_after_arxiv_error(make_paper) -> None:
    calls: list[str] = []

    def fake_search(query: str, *, days: int, max_results: int, **kwargs):
        calls.append(query)
        if query == "multimodal retrieval augmented generation":
            raise ArxivSearchError("temporary failure")
        return (make_paper(source_id="two"), make_paper(source_id="three"))

    agent = SearcherAgent(fake_search, min_results=2, max_replans=2)
    result = agent.run("multimodal retrieval augmented generation", days=7, max_results=10)

    assert calls == ["multimodal retrieval augmented generation", "multimodal retrieval augmented"]
    assert result.attempts[0].status == "error"
    assert result.attempts[1].status == "success"
    assert len(result.papers) == 2


def test_searcher_passes_search_options(make_paper) -> None:
    received: dict[str, object] = {}

    def fake_search(query: str, **kwargs):
        received.update(kwargs)
        return (make_paper(source_id="one"), make_paper(source_id="two"))

    agent = SearcherAgent(fake_search, min_results=2, max_replans=0)
    agent.run(
        "retrieval augmented generation",
        days=14,
        max_results=5,
        categories=("cs.CL",),
        strict_search=False,
    )

    assert received["days"] == 14
    assert received["max_results"] == 5
    assert received["categories"] == ("cs.CL",)
    assert received["strict_search"] is False
