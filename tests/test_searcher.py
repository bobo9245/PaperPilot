from __future__ import annotations

from dataclasses import replace

from paperpilot.agents.policy import AdvisorAgent
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
    result = agent.run("retrieval augmented generation systems", days=7, max_results=3)

    assert calls == ["retrieval augmented generation systems", "RAG systems"]
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
    result = agent.run("multimodal retrieval augmented generation", days=7, max_results=2)

    assert calls == ["multimodal retrieval augmented generation", "multimodal RAG"]
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


def test_searcher_runs_multiple_sources_and_dedupes_by_doi(make_paper) -> None:
    calls: list[tuple[str, str]] = []

    def arxiv_search(query: str, **kwargs):
        calls.append(("arxiv", query))
        return (
            make_paper(
                title="Shared Retrieval Paper",
                source_id="2601.00001",
                source="arxiv",
                doi="10.1234/shared",
            ),
        )

    def openalex_search(query: str, **kwargs):
        calls.append(("openalex", query))
        return (
            make_paper(
                title="Shared Retrieval Paper",
                source_id="openalex-1",
                source="openalex",
                doi="10.1234/shared",
                citation_count=42,
                venue="TestConf",
            ),
        )

    agent = SearcherAgent({"arxiv": arxiv_search, "openalex": openalex_search}, min_results=1)
    result = agent.run(
        "retrieval augmented generation",
        days=7,
        max_results=10,
        sources=("arxiv", "openalex"),
        query_expansion="off",
    )

    assert calls == [
        ("arxiv", "retrieval augmented generation"),
        ("openalex", "retrieval augmented generation"),
    ]
    assert len(result.papers) == 1
    assert result.papers[0].source == "arxiv, openalex"
    assert result.papers[0].citation_count == 42
    assert result.papers[0].venue == "TestConf"
    assert [attempt.source for attempt in result.attempts] == ["arxiv", "openalex"]


def test_searcher_dedupes_same_title_when_only_one_source_has_doi(make_paper) -> None:
    title = "Learning What to Forget: Improving LLM Unlearning via Learned Token-Level Importance"

    def arxiv_search(query: str, **kwargs):
        return (
            make_paper(
                title=title,
                source_id="2606.00001",
                source="arxiv",
                doi=None,
            ),
        )

    def openalex_search(query: str, **kwargs):
        return (
            replace(
                make_paper(
                    title=title,
                    source_id="openalex-1",
                    source="openalex",
                    doi="10.1234/learning-what-to-forget",
                    citation_count=7,
                ),
                url="https://openalex.org/W123",
                pdf_url=None,
            ),
        )

    agent = SearcherAgent({"arxiv": arxiv_search, "openalex": openalex_search}, min_results=1)
    result = agent.run(
        "language model unlearning",
        days=7,
        max_results=10,
        sources=("arxiv", "openalex"),
        query_expansion="off",
    )

    assert len(result.papers) == 1
    assert result.papers[0].doi == "10.1234/learning-what-to-forget"
    assert result.papers[0].source == "arxiv, openalex"
    assert result.papers[0].citation_count == 7


def test_searcher_keeps_results_when_one_source_fails(make_paper) -> None:
    def failing_search(query: str, **kwargs):
        raise ArxivSearchError("temporary failure")

    def working_search(query: str, **kwargs):
        return (make_paper(source_id="openalex-1", source="openalex"),)

    agent = SearcherAgent({"arxiv": failing_search, "openalex": working_search}, min_results=1)
    result = agent.run(
        "retrieval augmented generation",
        days=7,
        max_results=10,
        sources=("arxiv", "openalex"),
        query_expansion="off",
    )

    assert [attempt.status for attempt in result.attempts] == ["error", "success"]
    assert len(result.papers) == 1
    assert result.papers[0].source == "openalex"


def test_searcher_query_expansion_off_uses_original_query_only(make_paper) -> None:
    calls: list[str] = []

    def fake_search(query: str, **kwargs):
        calls.append(query)
        return ()

    agent = SearcherAgent(fake_search, min_results=2, max_replans=2)
    agent.run(
        "multimodal retrieval augmented generation",
        days=7,
        max_results=10,
        query_expansion="off",
        agentic_mode="off",
    )

    assert calls == ["multimodal retrieval augmented generation"]


def test_searcher_continues_query_expansion_until_max_results(make_paper) -> None:
    calls: list[str] = []

    def fake_search(query: str, **kwargs):
        calls.append(query)
        if query == "diffusion language model unlearning":
            return (
                make_paper(source_id="weak-1", title="Language Model Editing", summary="A broad language model paper."),
                make_paper(source_id="weak-2", title="General Unlearning", summary="A broad unlearning paper."),
                make_paper(source_id="weak-3", title="Diffusion Models", summary="A broad diffusion paper."),
            )
        return (
            make_paper(
                source_id="strong-1",
                title="DLM Unlearning for Text Generation",
                summary="We study DLM unlearning for diffusion language models.",
            ),
        )

    agent = SearcherAgent(fake_search, min_results=2, max_replans=2)
    result = agent.run(
        "diffusion language model unlearning",
        days=7,
        max_results=5,
        max_query_variants=2,
    )

    assert calls == ["diffusion language model unlearning", "DLM unlearning"]
    assert len(result.papers) == 4


def test_searcher_exhausts_dllm_unlearning_synonym_plan_even_after_candidate_budget(make_paper) -> None:
    calls: list[str] = []

    def fake_search(query: str, **kwargs):
        calls.append(query)
        return (
            make_paper(
                source_id=query.replace(" ", "-").lower(),
                title=f"{query} candidate",
                summary=f"We study {query} with unlearning experiments.",
            ),
        )

    agent = SearcherAgent(fake_search, min_results=1)
    result = agent.run(
        "dllm unlearning",
        days=30,
        max_results=1,
        max_query_variants=5,
    )

    assert calls == [
        "dllm unlearning",
        "diffusion language model unlearning",
        "discrete diffusion language model unlearning",
        "language model unlearning",
        "LLM unlearning",
    ]
    assert len(result.papers) == 5


def test_searcher_stops_retrying_rate_limited_source(make_paper) -> None:
    calls: list[tuple[str, str]] = []

    def semantic_search(query: str, **kwargs):
        calls.append(("semantic-scholar", query))
        raise ArxivSearchError("HTTP 429: Too Many Requests")

    def openalex_search(query: str, **kwargs):
        calls.append(("openalex", query))
        return ()

    agent = SearcherAgent(
        {
            "semantic-scholar": semantic_search,
            "openalex": openalex_search,
        },
        min_results=2,
    )
    result = agent.run(
        "diffusion language model unlearning",
        days=7,
        max_results=5,
        sources=("semantic-scholar", "openalex"),
        max_query_variants=2,
    )

    assert calls == [
        ("semantic-scholar", "diffusion language model unlearning"),
        ("openalex", "diffusion language model unlearning"),
        ("openalex", "DLM unlearning"),
        ("openalex", "diffusion language model unlearning"),
    ]
    assert calls.count(("semantic-scholar", "diffusion language model unlearning")) == 1
    assert any("skip_rate_limited_source" in event.action for event in result.trace)


def test_searcher_policy_tries_broad_search_after_strict_zero_results(make_paper) -> None:
    calls: list[tuple[str, bool]] = []

    def fake_search(query: str, *, strict_search: bool, **kwargs):
        calls.append((query, strict_search))
        if strict_search:
            return ()
        return (make_paper(source_id="broad-1"),)

    agent = SearcherAgent(fake_search, min_results=1)
    result = agent.run(
        "rare agentic ai benchmark",
        days=7,
        max_results=5,
        query_expansion="off",
    )

    assert calls == [
        ("rare agentic ai benchmark", True),
        ("rare agentic ai benchmark", False),
    ]
    assert len(result.papers) == 1
    assert any("try_broad_search" in event.action for event in result.trace)


def test_searcher_agentic_mode_off_skips_policy_broad_recovery(make_paper) -> None:
    calls: list[bool] = []

    def fake_search(query: str, *, strict_search: bool, **kwargs):
        calls.append(strict_search)
        return ()

    agent = SearcherAgent(fake_search, min_results=1)
    result = agent.run(
        "rare agentic ai benchmark",
        days=7,
        max_results=5,
        query_expansion="off",
        agentic_mode="off",
    )

    assert calls == [True]
    assert not result.papers
    assert not result.trace


def test_searcher_hybrid_uses_guarded_advisor_action(make_paper) -> None:
    class ContinueAdvisor(AdvisorAgent):
        def advise(self, *, observation: str, policy_action: str, allowed_actions: tuple[str, ...]) -> str:
            return "continue"

    calls: list[bool] = []

    def fake_search(query: str, *, strict_search: bool, **kwargs):
        calls.append(strict_search)
        return ()

    agent = SearcherAgent(fake_search, min_results=1, advisor=ContinueAdvisor())
    result = agent.run(
        "rare agentic ai benchmark",
        days=7,
        max_results=5,
        query_expansion="off",
        agentic_mode="hybrid",
    )

    assert calls == [True]
    assert not result.papers
    assert any("AdvisorAgent suggested" in event.decision for event in result.trace)
