"""End-to-end PaperPilot curation workflow."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from paperpilot.agents.policy import CurationPolicyAgent, validate_agentic_mode
from paperpilot.agents.reviewer import ReviewerAgent
from paperpilot.agents.searcher import SearcherAgent
from paperpilot.agents.summarizer import (
    HeuristicSummaryBackend,
    SummarizerAgent,
    SummaryBackendError,
    build_summary_backend,
)
from paperpilot.models import (
    CurationReport,
    Paper,
    PaperEvidence,
    ReviewedPaper,
    SearchAttempt,
    SearchResult,
    SelectedPaper,
    TraceEvent,
)
from paperpilot.publisher import MarkdownPublisher
from paperpilot.tools.arxiv import ArxivSearchClient
from paperpilot.tools.openalex import OpenAlexSearchClient
from paperpilot.tools.pdf import PdfEvidenceExtractor
from paperpilot.tools.semantic_scholar import SemanticScholarSearchClient


class CurationWorkflow:
    """Coordinate search, review, summary, reflection, and publishing."""

    def __init__(
        self,
        *,
        searcher: SearcherAgent | None = None,
        reviewer: ReviewerAgent | None = None,
        summarizer: SummarizerAgent | None = None,
        publisher: MarkdownPublisher | None = None,
        pdf_extractor: PdfEvidenceExtractor | None = None,
        policy: CurationPolicyAgent | None = None,
    ) -> None:
        self.policy = policy or CurationPolicyAgent()
        self.searcher = searcher or SearcherAgent(
            {
                "arxiv": ArxivSearchClient().search,
                "semantic-scholar": SemanticScholarSearchClient().search,
                "openalex": OpenAlexSearchClient().search,
            },
            policy=self.policy,
        )
        self.reviewer = reviewer or ReviewerAgent()
        self.summarizer = summarizer or SummarizerAgent()
        self.publisher = publisher or MarkdownPublisher()
        self.pdf_extractor = pdf_extractor or PdfEvidenceExtractor()

    def run(
        self,
        query: str,
        *,
        days: int = 7,
        max_results: int = 20,
        top_k: int = 3,
        min_relevance: float = 0.8,
        categories: tuple[str, ...] | list[str] = (),
        strict_search: bool = True,
        sources: tuple[str, ...] | list[str] = ("arxiv",),
        query_expansion: str = "basic",
        max_query_variants: int = 6,
        scholar_links: bool = False,
        with_pdf: bool = False,
        pdf_max_pages: int = 6,
        pdf_max_chars: int = 16_000,
        summary_backend: str = "auto",
        summary_model: str | None = None,
        summary_detail: str = "standard",
        agentic_mode: str = "policy",
        max_agent_steps: int = 6,
        failure_analysis: bool = True,
        dry_run: bool = False,
        output_dir: str | Path | None = None,
    ) -> CurationReport:
        if not query.strip():
            raise ValueError("query is required")
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        if not 0 <= min_relevance <= 1:
            raise ValueError("min_relevance must be between 0 and 1")
        if pdf_max_pages < 1:
            raise ValueError("pdf_max_pages must be at least 1")
        if pdf_max_chars < 1:
            raise ValueError("pdf_max_chars must be at least 1")
        if summary_backend not in {"auto", "openai", "factchat", "heuristic"}:
            raise ValueError("summary_backend must be one of: auto, openai, factchat, heuristic")
        if summary_detail not in {"standard", "deep", "ultra"}:
            raise ValueError("summary_detail must be one of: standard, deep, ultra")
        normalized_sources = tuple(dict.fromkeys(source.strip() for source in sources if source.strip()))
        if not normalized_sources:
            raise ValueError("at least one search source is required")
        if query_expansion not in {"off", "basic"}:
            raise ValueError("query_expansion must be one of: off, basic")
        if max_query_variants < 1:
            raise ValueError("max_query_variants must be at least 1")
        validate_agentic_mode(agentic_mode)
        if max_agent_steps < 1:
            raise ValueError("max_agent_steps must be at least 1")

        if output_dir is not None:
            self.publisher = MarkdownPublisher(output_dir)
        self.summarizer.set_backend(
            build_summary_backend(
                summary_backend,
                model=summary_model,
                detail=summary_detail,
            )
        )

        search_result = (
            _dry_run_search(query)
            if dry_run
            else self.searcher.run(
                query,
                days=days,
                max_results=max_results,
                categories=categories,
                strict_search=strict_search,
                sources=normalized_sources,
                query_expansion=query_expansion,
                max_query_variants=max_query_variants,
                agentic_mode=agentic_mode,
                max_agent_steps=max_agent_steps,
            )
        )
        ranked = self.reviewer.rank(
            search_result.papers,
            query=query,
            min_relevance=min_relevance,
        )
        selected = tuple(
            self._select_paper(
                reviewed,
                with_pdf=with_pdf,
                pdf_max_pages=pdf_max_pages,
                pdf_max_chars=pdf_max_chars,
            )
            for reviewed in ranked[:top_k]
        )
        fallback_reason = _fallback_reason(self.summarizer.fallback_reasons)
        rate_limited_sources = _rate_limited_sources(search_result.attempts)
        trace = _build_trace(
            query=query,
            search_result=search_result,
            ranked=ranked,
            selected=selected,
            min_relevance=min_relevance,
            with_pdf=with_pdf,
            summary_backend=summary_backend,
            summary_model=self.summarizer.model,
            summary_detail=summary_detail,
            fallback_reason=fallback_reason,
            policy=self.policy,
            agentic_mode=agentic_mode,
            failure_analysis=failure_analysis,
            rate_limited_sources=rate_limited_sources,
        )
        report = CurationReport(
            query=query,
            generated_at=datetime.now(timezone.utc),
            attempts=search_result.attempts,
            selected=selected,
            trace=trace,
            min_relevance=min_relevance,
            categories=tuple(categories),
            strict_search=strict_search,
            agentic_mode=agentic_mode,
            max_agent_steps=max_agent_steps,
            failure_analysis=failure_analysis,
            candidate_count=len(search_result.papers),
            deduped_count=search_result.deduped_count,
            scholar_links=scholar_links,
            with_pdf=with_pdf,
            pdf_max_pages=pdf_max_pages if with_pdf else None,
            pdf_max_chars=pdf_max_chars if with_pdf else None,
            summary_backend=summary_backend,
            summary_model=self.summarizer.model,
            summary_detail=summary_detail,
            summary_fallback_reason=fallback_reason,
        )
        output_path = self.publisher.publish(report)
        return CurationReport(
            query=report.query,
            generated_at=report.generated_at,
            attempts=report.attempts,
            selected=report.selected,
            trace=report.trace,
            output_path=output_path,
            min_relevance=report.min_relevance,
            categories=report.categories,
            strict_search=report.strict_search,
            agentic_mode=report.agentic_mode,
            max_agent_steps=report.max_agent_steps,
            failure_analysis=report.failure_analysis,
            candidate_count=report.candidate_count,
            deduped_count=report.deduped_count,
            scholar_links=report.scholar_links,
            with_pdf=report.with_pdf,
            pdf_max_pages=report.pdf_max_pages,
            pdf_max_chars=report.pdf_max_chars,
            summary_backend=report.summary_backend,
            summary_model=report.summary_model,
            summary_detail=report.summary_detail,
            summary_fallback_reason=report.summary_fallback_reason,
        )

    def _select_paper(
        self,
        reviewed: ReviewedPaper,
        *,
        with_pdf: bool,
        pdf_max_pages: int,
        pdf_max_chars: int,
    ) -> SelectedPaper:
        evidence: PaperEvidence | None = None
        if with_pdf:
            evidence = self.pdf_extractor.fetch(
                reviewed.paper,
                max_pages=pdf_max_pages,
                max_chars=pdf_max_chars,
            )
        try:
            summary = self.summarizer.summarize(reviewed.paper, reviewed.score, evidence=evidence)
        except SummaryBackendError as exc:
            self.summarizer.fallback_reasons.append(f"Summary backend failed for `{reviewed.paper.title}`: {exc}")
            summary = HeuristicSummaryBackend().summarize(reviewed.paper, reviewed.score, evidence=evidence)
        return SelectedPaper(
            reviewed=reviewed,
            summary=summary,
            evidence=evidence,
        )


def _dry_run_search(query: str) -> SearchResult:
    now = datetime.now(timezone.utc)
    papers = (
        Paper(
            title=f"Adaptive Retrieval Pipelines for {query.title()}",
            authors=("Mina Park", "Jon Bell"),
            summary=(
                "We introduce a novel retrieval augmented generation framework that dynamically "
                "routes queries across dense and sparse retrievers. Experiments on 6 datasets show "
                "a 12.4% improvement in answer faithfulness and lower latency."
            ),
            published=now - timedelta(days=1),
            updated=now,
            url="https://arxiv.org/abs/2601.00001",
            pdf_url="https://arxiv.org/pdf/2601.00001",
            categories=("cs.CL", "cs.IR"),
            source_id="dry-run-1",
            source="dry-run",
        ),
        Paper(
            title=f"Benchmarking Long Context Methods for {query.title()}",
            authors=("Ari Kim", "Leah Stone"),
            summary=(
                "This paper proposes a benchmark for long context question answering with "
                "retrieval and generation components. The abstract describes evaluation protocols "
                "but does not report headline numeric results."
            ),
            published=now - timedelta(days=2),
            updated=now,
            url="https://arxiv.org/abs/2601.00002",
            pdf_url="https://arxiv.org/pdf/2601.00002",
            categories=("cs.CL",),
            source_id="dry-run-2",
            source="dry-run",
        ),
        Paper(
            title=f"Failure Modes in Applied {query.title()} Systems",
            authors=("Noah Singh", "Iris Chen"),
            summary=(
                "We analyze failure modes in production retrieval systems and discuss mitigation "
                "strategies. Case studies cover evaluation drift, prompt sensitivity, and source "
                "attribution gaps."
            ),
            published=now - timedelta(days=3),
            updated=now,
            url="https://arxiv.org/abs/2601.00003",
            pdf_url=None,
            categories=("cs.LG", "cs.CL"),
            source_id="dry-run-3",
            source="dry-run",
        ),
    )
    return SearchResult(
        original_query=query,
        papers=papers,
        attempts=(
            SearchAttempt(
                query=query,
                source="dry-run",
                status="dry_run",
                results_count=len(papers),
                message="Used built-in sample papers without calling arXiv.",
            ),
        ),
        raw_results_count=len(papers),
        deduped_count=0,
    )


def _fallback_reason(reasons: list[str]) -> str | None:
    if not reasons:
        return None
    deduped = list(dict.fromkeys(reasons))
    return "; ".join(deduped)


def _build_trace(
    *,
    query: str,
    search_result: SearchResult,
    ranked: tuple[ReviewedPaper, ...],
    selected: tuple[SelectedPaper, ...],
    min_relevance: float,
    with_pdf: bool,
    summary_backend: str,
    summary_model: str | None,
    summary_detail: str,
    fallback_reason: str | None,
    policy: CurationPolicyAgent,
    agentic_mode: str,
    failure_analysis: bool,
    rate_limited_sources: tuple[str, ...],
) -> tuple[TraceEvent, ...]:
    events: list[TraceEvent] = []
    query_variants = tuple(dict.fromkeys(attempt.query for attempt in search_result.attempts)) or (query,)
    events.append(
        TraceEvent(
            step="plan_query",
            action="Plan bounded query variants",
            input=query,
            observation=f"{len(query_variants)} query variant(s) attempted",
            decision="Use deterministic expansion and stop when the candidate budget is filled.",
            status="completed",
        )
    )
    events.extend(search_result.trace)

    for attempt in search_result.attempts:
        events.append(
            TraceEvent(
                step="search_source",
                action=f"Search {attempt.source}",
                input=attempt.query,
                observation=f"{attempt.results_count} result(s), status={attempt.status}",
                decision=attempt.message,
                status=attempt.status,
            )
        )
        events.append(
            TraceEvent(
                step="observe_results",
                action="Inspect result count and source status",
                input=f"{attempt.source}: {attempt.query}",
                observation=f"{attempt.results_count} candidate(s) returned",
                decision=(
                    "Keep candidates and continue merging metadata."
                    if attempt.status in {"success", "dry_run"}
                    else "Continue with another source or broader query variant."
                ),
                status=attempt.status,
            )
        )
        if attempt.status in {"too_few_results", "error"}:
            events.append(
                TraceEvent(
                    step="replan",
                    action="Recover from weak observation",
                    input=f"{attempt.source}: {attempt.query}",
                    observation=attempt.message,
                    decision="Try the remaining planned source/query combinations.",
                    status="continued",
                )
            )

    events.append(
        TraceEvent(
            step="dedupe",
            action="Merge duplicate papers across sources",
            input=f"{search_result.raw_results_count} raw result(s)",
            observation=f"{search_result.deduped_count} duplicate result(s) merged",
            decision=f"Review {len(search_result.papers)} unique candidate(s).",
            status="completed",
        )
    )
    events.append(
        TraceEvent(
            step="review",
            action="Score relevance, novelty, and experimental strength",
            input=f"{len(search_result.papers)} candidate(s)",
            observation=f"{len(ranked)} candidate(s) passed min relevance {min_relevance:.3f}",
            decision=f"Select top {len(selected)} paper(s) for summary.",
            status="completed",
        )
    )

    if with_pdf:
        pdf_successes = sum(1 for item in selected if item.evidence and item.evidence.available)
        status = "success" if selected and pdf_successes == len(selected) else "partial" if pdf_successes else "failed"
        events.append(
            TraceEvent(
                step="extract_pdf",
                action="Fetch selected-paper PDFs for grounded evidence",
                input=f"{len(selected)} selected paper(s)",
                observation=f"{pdf_successes}/{len(selected)} PDF extraction(s) succeeded",
                decision="Use PDF text when available; otherwise keep abstract-only evidence.",
                status=status if selected else "skipped",
            )
        )
        if agentic_mode != "off":
            _append_decision_trace(
                events,
                policy.decide_after_pdf(selected_count=len(selected), pdf_successes=pdf_successes),
                context="selected-paper PDFs",
            )
    else:
        events.append(
            TraceEvent(
                step="extract_pdf",
                action="Skip PDF evidence extraction",
                input=f"{len(selected)} selected paper(s)",
                observation="PDF evidence disabled",
                decision="Summarize from abstract metadata only.",
                status="skipped",
            )
        )

    events.append(
        TraceEvent(
            step="summarize",
            action="Generate Korean five-part summaries",
            input=f"backend={summary_backend}, detail={summary_detail}, model={summary_model or 'N/A'}",
            observation=f"{len(selected)} summary item(s) generated",
            decision="Keep summaries structured as problem, contribution, method, results, and limitations.",
            status="completed",
        )
    )
    passed = sum(1 for item in selected if item.summary.reflection.passed)
    status = "completed" if passed == len(selected) else "partial"
    events.append(
        TraceEvent(
            step="reflect",
            action="Validate summary quality gates",
            input=f"{len(selected)} summary item(s)",
            observation=f"{passed}/{len(selected)} summary reflection(s) passed",
            decision="Surface caveats or fallback reasons when quality checks fail.",
            status=status,
        )
    )
    if fallback_reason:
        events.append(
            TraceEvent(
                step="fallback",
                action="Use deterministic fallback summary path",
                input=summary_backend,
                observation=fallback_reason,
                decision="Preserve report generation even when an LLM backend is unavailable.",
                status="fallback",
            )
        )
    if agentic_mode != "off":
        _append_decision_trace(
            events,
            policy.decide_after_summary(
                selected_count=len(selected),
                reflection_passes=passed,
                fallback_reason=fallback_reason,
            ),
            context="summary reflection",
        )
    if failure_analysis and not selected:
        _append_decision_trace(
            events,
            policy.decide_zero_selected(
                candidate_count=len(search_result.papers),
                min_relevance=min_relevance,
                rate_limited_sources=rate_limited_sources,
            ),
            context=query,
        )
    return tuple(events)


def _append_decision_trace(events: list[TraceEvent], decision, *, context: str) -> None:
    events.append(
        TraceEvent(
            step="observe",
            action="Observe workflow state",
            input=context,
            observation=decision.observation,
            decision="Pass observation to CurationPolicyAgent.",
            status=decision.status,
        )
    )
    events.append(
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
        events.append(
            TraceEvent(
                step="act",
                action=f"Apply `{decision.action}`",
                input=context,
                observation=decision.observation,
                decision=decision.decision,
                status=decision.status,
            )
        )


def _rate_limited_sources(attempts: tuple[SearchAttempt, ...]) -> tuple[str, ...]:
    sources: list[str] = []
    for attempt in attempts:
        text = f"{attempt.status} {attempt.message}".lower()
        if "429" in text or "rate limit" in text or "too many requests" in text:
            sources.append(attempt.source)
    return tuple(dict.fromkeys(sources))
