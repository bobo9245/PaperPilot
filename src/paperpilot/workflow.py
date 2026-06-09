"""End-to-end PaperPilot curation workflow."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from paperpilot.agents.reviewer import ReviewerAgent
from paperpilot.agents.searcher import SearcherAgent
from paperpilot.agents.summarizer import SummarizerAgent, build_summary_backend
from paperpilot.models import (
    CurationReport,
    Paper,
    PaperEvidence,
    ReviewedPaper,
    SearchAttempt,
    SearchResult,
    SelectedPaper,
)
from paperpilot.publisher import MarkdownPublisher
from paperpilot.tools.arxiv import ArxivSearchClient
from paperpilot.tools.pdf import PdfEvidenceExtractor


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
    ) -> None:
        self.searcher = searcher or SearcherAgent(ArxivSearchClient().search)
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
        with_pdf: bool = False,
        pdf_max_pages: int = 6,
        pdf_max_chars: int = 16_000,
        summary_backend: str = "auto",
        summary_model: str | None = None,
        summary_detail: str = "standard",
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
        report = CurationReport(
            query=query,
            generated_at=datetime.now(timezone.utc),
            attempts=search_result.attempts,
            selected=selected,
            min_relevance=min_relevance,
            categories=tuple(categories),
            strict_search=strict_search,
            with_pdf=with_pdf,
            pdf_max_pages=pdf_max_pages if with_pdf else None,
            pdf_max_chars=pdf_max_chars if with_pdf else None,
            summary_backend=summary_backend,
            summary_model=self.summarizer.model,
            summary_detail=summary_detail,
            summary_fallback_reason=_fallback_reason(self.summarizer.fallback_reasons),
        )
        output_path = self.publisher.publish(report)
        return CurationReport(
            query=report.query,
            generated_at=report.generated_at,
            attempts=report.attempts,
            selected=report.selected,
            output_path=output_path,
            min_relevance=report.min_relevance,
            categories=report.categories,
            strict_search=report.strict_search,
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
        return SelectedPaper(
            reviewed=reviewed,
            summary=self.summarizer.summarize(reviewed.paper, reviewed.score, evidence=evidence),
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
        ),
    )
    return SearchResult(
        original_query=query,
        papers=papers,
        attempts=(
            SearchAttempt(
                query=query,
                status="dry_run",
                results_count=len(papers),
                message="Used built-in sample papers without calling arXiv.",
            ),
        ),
    )


def _fallback_reason(reasons: list[str]) -> str | None:
    if not reasons:
        return None
    deduped = list(dict.fromkeys(reasons))
    return "; ".join(deduped)
