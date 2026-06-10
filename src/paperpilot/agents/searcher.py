"""Search agent with observation logging and lightweight replanning."""

from __future__ import annotations

import re
from collections.abc import Callable
from collections.abc import Mapping

from paperpilot.agents.policy import AdvisorAgent, CurationPolicyAgent, validate_agentic_mode
from paperpilot.agents.query_planner import QueryPlannerAgent
from paperpilot.models import Paper, PolicyDecision, SearchAttempt, SearchResult, TraceEvent
from paperpilot.tools.arxiv import ArxivSearchError
from paperpilot.tools.openalex import OpenAlexSearchError
from paperpilot.tools.semantic_scholar import SemanticScholarSearchError


SearchFunction = Callable[..., tuple[Paper, ...]]
SearchSourceMap = Mapping[str, SearchFunction]


class SearcherAgent:
    """Run paper search and broaden the query when the first attempt is weak."""

    def __init__(
        self,
        search: SearchFunction | SearchSourceMap,
        *,
        min_results: int = 3,
        max_replans: int = 2,
        policy: CurationPolicyAgent | None = None,
        advisor: AdvisorAgent | None = None,
    ) -> None:
        self.searches = {"arxiv": search} if callable(search) else dict(search)
        self.min_results = min_results
        self.max_replans = max_replans
        self.policy = policy or CurationPolicyAgent()
        self.advisor = advisor or AdvisorAgent()

    def run(
        self,
        query: str,
        *,
        days: int,
        max_results: int,
        categories: tuple[str, ...] | list[str] = (),
        strict_search: bool = True,
        sources: tuple[str, ...] | list[str] = ("arxiv",),
        query_expansion: str = "basic",
        max_query_variants: int | None = None,
        agentic_mode: str = "policy",
        max_agent_steps: int = 6,
    ) -> SearchResult:
        validate_agentic_mode(agentic_mode)
        if max_agent_steps < 1:
            raise ValueError("max_agent_steps must be at least 1")

        attempts: list[SearchAttempt] = []
        trace: list[TraceEvent] = []
        papers_by_key: dict[str, Paper] = {}
        key_aliases: dict[str, str] = {}
        raw_results_count = 0
        max_variants = max_query_variants or self.max_replans + 1
        planner = QueryPlannerAgent(mode=query_expansion, max_variants=max_variants)
        disabled_sources: set[str] = set()
        policy_steps = 0
        broad_search_used = False
        broad_search_requested = False
        query_plan = planner.plan(query)

        for candidate_index, candidate in enumerate(query_plan):
            for source_index, source in enumerate(sources):
                if source in disabled_sources:
                    continue
                search = self.searches.get(source)
                if search is None:
                    attempt = SearchAttempt(
                        query=candidate,
                        source=source,
                        status="error",
                        results_count=0,
                        message=f"Unknown search source: {source}",
                    )
                    attempts.append(attempt)
                    decision = self.policy.decide_after_search(
                        attempt,
                        candidate_count=len(papers_by_key),
                        strict_search=strict_search,
                        broad_search_used=broad_search_used,
                        has_more_query_variants=_has_more_plan(query_plan, sources, candidate_index, source_index),
                        max_agent_steps_reached=policy_steps >= max_agent_steps,
                    )
                    decision = self._advise(decision, agentic_mode=agentic_mode)
                    broad_search_requested = broad_search_requested or decision.action == "try_broad_search"
                    policy_steps += _record_policy_trace(
                        trace,
                        decision,
                        enabled=agentic_mode != "off",
                        context=f"{source}: {candidate}",
                    )
                    continue
                try:
                    papers = search(
                        candidate,
                        days=days,
                        max_results=max_results,
                        categories=categories,
                        strict_search=strict_search,
                    )
                except (
                    ArxivSearchError,
                    SemanticScholarSearchError,
                    OpenAlexSearchError,
                    OSError,
                    ValueError,
                ) as exc:
                    if _is_rate_limit_error(exc):
                        disabled_sources.add(source)
                    attempt = SearchAttempt(
                        query=candidate,
                        source=source,
                        status="error",
                        results_count=0,
                        message=str(exc),
                    )
                    attempts.append(attempt)
                    decision = self.policy.decide_after_search(
                        attempt,
                        candidate_count=len(papers_by_key),
                        strict_search=strict_search,
                        broad_search_used=broad_search_used,
                        has_more_query_variants=_has_more_plan(query_plan, sources, candidate_index, source_index),
                        max_agent_steps_reached=policy_steps >= max_agent_steps,
                    )
                    decision = self._advise(decision, agentic_mode=agentic_mode)
                    broad_search_requested = broad_search_requested or decision.action == "try_broad_search"
                    policy_steps += _record_policy_trace(
                        trace,
                        decision,
                        enabled=agentic_mode != "off",
                        context=f"{source}: {candidate}",
                    )
                    continue

                raw_results_count += len(papers)
                for paper in papers:
                    keys = _paper_keys(paper)
                    key = _find_merge_key(keys, key_aliases, papers_by_key, paper)
                    if key is None:
                        key = next((candidate for candidate in keys if candidate not in key_aliases), keys[0])
                        papers_by_key[key] = paper
                    else:
                        papers_by_key[key] = _merge_papers(papers_by_key[key], paper)

                    for alias in keys:
                        key_aliases.setdefault(alias, key)

                status = "success" if len(papers) >= self.min_results else "too_few_results"
                attempt = SearchAttempt(
                    query=candidate,
                    source=source,
                    status=status,
                    results_count=len(papers),
                    message=(
                        "Enough recent candidates found."
                        if status == "success"
                        else "Too few recent candidates; trying another source or broader query."
                    ),
                )
                attempts.append(attempt)
                decision = self.policy.decide_after_search(
                    attempt,
                    candidate_count=len(papers_by_key),
                    strict_search=strict_search,
                    broad_search_used=broad_search_used,
                    has_more_query_variants=_has_more_plan(query_plan, sources, candidate_index, source_index),
                    max_agent_steps_reached=policy_steps >= max_agent_steps,
                )
                decision = self._advise(decision, agentic_mode=agentic_mode)
                broad_search_requested = broad_search_requested or decision.action == "try_broad_search"
                policy_steps += _record_policy_trace(
                    trace,
                    decision,
                    enabled=agentic_mode != "off",
                    context=f"{source}: {candidate}",
                )

            if query_expansion == "off" and len(papers_by_key) >= self.min_results:
                break
            if len(papers_by_key) >= max_results:
                break

        if (
            agentic_mode != "off"
            and strict_search
            and not broad_search_used
            and not papers_by_key
            and (broad_search_requested or policy_steps < max_agent_steps)
        ):
            if not broad_search_requested:
                decision = self.policy.decide_after_search(
                    SearchAttempt(
                        query=query,
                        source=", ".join(sources),
                        status="too_few_results",
                        results_count=0,
                        message="Strict search collected no candidates across planned query variants.",
                    ),
                    candidate_count=0,
                    strict_search=True,
                    broad_search_used=False,
                    has_more_query_variants=False,
                    max_agent_steps_reached=False,
                )
                decision = self._advise(decision, agentic_mode=agentic_mode)
                policy_steps += _record_policy_trace(trace, decision, enabled=True, context=query)
                broad_search_requested = decision.action == "try_broad_search"
            if broad_search_requested:
                broad_search_used = True
                extra_result, extra_raw = self._run_broad_recovery(
                    query,
                    days=days,
                    max_results=max_results,
                    categories=categories,
                    sources=sources,
                    disabled_sources=disabled_sources,
                    papers_by_key=papers_by_key,
                    key_aliases=key_aliases,
                    attempts=attempts,
                )
                raw_results_count += extra_raw
                if extra_result:
                    trace.append(
                        TraceEvent(
                            step="act",
                            action="Execute broad-search recovery",
                            input=query,
                            observation=f"{extra_result} additional result(s) collected",
                            decision="Use broad all-fields results in the same review pool.",
                            status="completed",
                        )
                    )

        return SearchResult(
            original_query=query,
            papers=tuple(papers_by_key.values())[:max_results],
            attempts=tuple(attempts),
            raw_results_count=raw_results_count,
            deduped_count=max(0, raw_results_count - len(papers_by_key)),
            trace=tuple(trace),
        )

    def _advise(self, decision: PolicyDecision, *, agentic_mode: str) -> PolicyDecision:
        if agentic_mode != "hybrid":
            return decision
        allowed_actions = tuple(dict.fromkeys((decision.action, "continue")))
        advised_action = self.advisor.advise(
            observation=decision.observation,
            policy_action=decision.action,
            allowed_actions=allowed_actions,
        )
        if advised_action == decision.action:
            return decision
        return PolicyDecision(
            action=advised_action,
            observation=decision.observation,
            decision=(
                f"AdvisorAgent suggested `{advised_action}` within guardrails; "
                f"deterministic policy suggested `{decision.action}`. {decision.decision}"
            ),
            status="advisor",
        )

    def _run_broad_recovery(
        self,
        query: str,
        *,
        days: int,
        max_results: int,
        categories: tuple[str, ...] | list[str],
        sources: tuple[str, ...] | list[str],
        disabled_sources: set[str],
        papers_by_key: dict[str, Paper],
        key_aliases: dict[str, str],
        attempts: list[SearchAttempt],
    ) -> tuple[int, int]:
        raw_results_count = 0
        collected = 0
        for source in sources:
            if source in disabled_sources:
                continue
            search = self.searches.get(source)
            if search is None:
                continue
            try:
                papers = search(
                    query,
                    days=days,
                    max_results=max_results,
                    categories=categories,
                    strict_search=False,
                )
            except (
                ArxivSearchError,
                SemanticScholarSearchError,
                OpenAlexSearchError,
                OSError,
                ValueError,
            ) as exc:
                attempts.append(
                    SearchAttempt(
                        query=query,
                        source=source,
                        status="error",
                        results_count=0,
                        message=f"Broad search failed: {exc}",
                    )
                )
                continue
            raw_results_count += len(papers)
            collected += len(papers)
            for paper in papers:
                keys = _paper_keys(paper)
                key = _find_merge_key(keys, key_aliases, papers_by_key, paper)
                if key is None:
                    key = next((candidate for candidate in keys if candidate not in key_aliases), keys[0])
                    papers_by_key[key] = paper
                else:
                    papers_by_key[key] = _merge_papers(papers_by_key[key], paper)
                for alias in keys:
                    key_aliases.setdefault(alias, key)
            attempts.append(
                SearchAttempt(
                    query=query,
                    source=source,
                    status="success" if len(papers) >= self.min_results else "too_few_results",
                    results_count=len(papers),
                    message="Broad all-fields recovery search.",
                )
            )
        return collected, raw_results_count

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


def _paper_keys(paper: Paper) -> tuple[str, ...]:
    keys: list[str] = []
    if paper.doi:
        keys.append(f"doi:{_normalize_doi(paper.doi)}")
    arxiv_id = _arxiv_id(paper)
    if arxiv_id:
        keys.append(f"arxiv:{arxiv_id}")
    title = _normalize_title(paper.title)
    if title:
        keys.append(f"title:{title}")
    return tuple(dict.fromkeys(keys)) or (f"title:{paper.title.lower().strip()}",)


def _find_merge_key(
    keys: tuple[str, ...],
    key_aliases: dict[str, str],
    papers_by_key: dict[str, Paper],
    incoming: Paper,
) -> str | None:
    for key in keys:
        canonical_key = key_aliases.get(key)
        if canonical_key is None:
            continue
        existing = papers_by_key.get(canonical_key)
        if existing is not None and _can_merge_papers(existing, incoming):
            return canonical_key
    return None


def _can_merge_papers(existing: Paper, incoming: Paper) -> bool:
    if existing.doi and incoming.doi:
        return _normalize_doi(existing.doi) == _normalize_doi(incoming.doi)

    existing_arxiv_id = _arxiv_id(existing)
    incoming_arxiv_id = _arxiv_id(incoming)
    if existing_arxiv_id and incoming_arxiv_id and existing_arxiv_id != incoming_arxiv_id:
        return False

    return True


def _merge_papers(existing: Paper, incoming: Paper) -> Paper:
    sources = tuple(dict.fromkeys(_split_sources(existing.source) + _split_sources(incoming.source)))
    citation_count = _max_optional(existing.citation_count, incoming.citation_count)
    summary = existing.summary if len(existing.summary) >= len(incoming.summary) else incoming.summary
    return Paper(
        title=existing.title or incoming.title,
        authors=existing.authors or incoming.authors,
        summary=summary,
        published=min(existing.published, incoming.published),
        updated=existing.updated or incoming.updated,
        url=_prefer_url(existing, incoming),
        pdf_url=_prefer_pdf_url(existing, incoming),
        categories=tuple(dict.fromkeys(existing.categories + incoming.categories)),
        source_id=existing.source_id or incoming.source_id,
        source=", ".join(sources),
        doi=existing.doi or incoming.doi,
        citation_count=citation_count,
        venue=existing.venue or incoming.venue,
    )


def _prefer_url(existing: Paper, incoming: Paper) -> str:
    if "arxiv" in incoming.source and incoming.url:
        return incoming.url
    return existing.url or incoming.url


def _prefer_pdf_url(existing: Paper, incoming: Paper) -> str | None:
    if "arxiv" in incoming.source and incoming.pdf_url:
        return incoming.pdf_url
    return existing.pdf_url or incoming.pdf_url


def _split_sources(value: str) -> tuple[str, ...]:
    return tuple(source.strip() for source in value.split(",") if source.strip())


def _max_optional(left: int | None, right: int | None) -> int | None:
    values = [value for value in (left, right) if value is not None]
    return max(values) if values else None


def _normalize_doi(doi: str) -> str:
    return doi.lower().removeprefix("https://doi.org/").removeprefix("doi:").strip()


def _arxiv_id(paper: Paper) -> str | None:
    values = tuple(value for value in (paper.source_id, paper.url, paper.pdf_url) if value)
    for value in values:
        match = re.search(r"arxiv:(?P<id>[A-Za-z0-9.\-/]+)$", value)
        if match:
            return _clean_arxiv_id(match.group("id"))
        match = re.search(r"arxiv\.org/(?:abs|pdf)/(?P<id>[A-Za-z0-9.\-/]+)", value)
        if match:
            return _clean_arxiv_id(match.group("id"))
    return None


def _clean_arxiv_id(value: str) -> str:
    return value.removesuffix(".pdf").lower()


def _normalize_title(title: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", title.lower()))


def _is_rate_limit_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "429" in text or "rate limit" in text or "too many requests" in text


def _has_more_plan(
    query_plan: tuple[str, ...],
    sources: tuple[str, ...] | list[str],
    candidate_index: int,
    source_index: int,
) -> bool:
    return candidate_index < len(query_plan) - 1 or source_index < len(sources) - 1


def _record_policy_trace(
    trace: list[TraceEvent],
    decision,
    *,
    enabled: bool,
    context: str,
) -> int:
    if not enabled:
        return 0
    trace.append(
        TraceEvent(
            step="observe",
            action="Observe search result",
            input=context,
            observation=decision.observation,
            decision="Pass observation to CurationPolicyAgent.",
            status=decision.status,
        )
    )
    trace.append(
        TraceEvent(
            step="decide",
            action=f"CurationPolicyAgent selected `{decision.action}`",
            input=context,
            observation=decision.observation,
            decision=decision.decision,
            status=decision.status,
        )
    )
    if decision.action != "continue":
        trace.append(
            TraceEvent(
                step="act",
                action=f"Apply `{decision.action}`",
                input=context,
                observation=decision.observation,
                decision=decision.decision,
                status=decision.status,
            )
        )
        return 1
    return 0


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
