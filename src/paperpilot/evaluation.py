"""Repeatable evaluation runs for the PaperPilot project report."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paperpilot.agents.searcher import SearcherAgent
from paperpilot.agents.summarizer import SummaryBackendError, get_summary_credits
from paperpilot.models import (
    EvaluationMetrics,
    EvaluationResult,
    EvaluationRun,
    EvaluationScenario,
    Paper,
    PaperEvidence,
)
from paperpilot.workflow import CurationWorkflow


EVALUATION_SCENARIOS: dict[str, EvaluationScenario] = {
    "multimodal_rag": EvaluationScenario(
        id="multimodal_rag",
        query="multimodal retrieval augmented generation",
        expected_behavior="Query expansion should recover multimodal RAG and document retrieval variants.",
    ),
    "dlm_unlearning": EvaluationScenario(
        id="dlm_unlearning",
        query="diffusion language model unlearning",
        expected_behavior="The agentic condition should broaden toward language model and LLM unlearning.",
    ),
    "agentic_ai_evaluation": EvaluationScenario(
        id="agentic_ai_evaluation",
        query="agentic ai evaluation benchmark",
        expected_behavior="The workflow should prefer benchmark/evaluation papers with explicit evidence.",
    ),
}


def run_evaluation(
    *,
    mode: str,
    scenario_ids: tuple[str, ...],
    output_dir: str | Path,
    sources: tuple[str, ...] = ("arxiv", "openalex"),
    top_k: int = 3,
    pdf_max_pages: int = 8,
    pdf_max_chars: int = 24_000,
    summary_backend: str = "heuristic",
    summary_model: str | None = None,
    summary_detail: str = "deep",
    max_agent_steps: int = 6,
    write_json: bool = False,
) -> EvaluationResult:
    """Run baseline and agentic conditions and write an evaluation report."""

    if mode not in {"fixture", "live"}:
        raise ValueError("mode must be one of: fixture, live")
    if max_agent_steps < 1:
        raise ValueError("max_agent_steps must be at least 1")

    generated_at = datetime.now(timezone.utc)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    curation_dir = output_path / "curations"
    runs: list[EvaluationRun] = []

    for scenario_id in scenario_ids:
        scenario = _scenario(scenario_id)
        runs.append(
            _run_condition(
                mode=mode,
                scenario=scenario,
                condition="baseline",
                sources=("arxiv",),
                query_expansion="off",
                with_pdf=False,
                top_k=top_k,
                pdf_max_pages=pdf_max_pages,
                pdf_max_chars=pdf_max_chars,
                summary_backend="heuristic",
                summary_model=None,
                summary_detail="standard",
                agentic_mode="off",
                max_agent_steps=max_agent_steps,
                output_dir=curation_dir,
            )
        )
        runs.append(
            _run_condition(
                mode=mode,
                scenario=scenario,
                condition="agentic",
                sources=sources,
                query_expansion="basic",
                with_pdf=True,
                top_k=top_k,
                pdf_max_pages=pdf_max_pages,
                pdf_max_chars=pdf_max_chars,
                summary_backend=summary_backend,
                summary_model=summary_model,
                summary_detail=summary_detail,
                agentic_mode="policy",
                max_agent_steps=max_agent_steps,
                output_dir=curation_dir,
            )
        )

    report = EvaluationResult(
        generated_at=generated_at,
        mode=mode,
        runs=tuple(runs),
        output_path=output_path / f"{generated_at.date().isoformat()}_eval.md",
    )
    report.output_path.write_text(render_evaluation_markdown(report), encoding="utf-8")

    if write_json:
        json_path = output_path / f"{generated_at.date().isoformat()}_eval.json"
        json_path.write_text(json.dumps(_evaluation_to_json(report), ensure_ascii=False, indent=2), encoding="utf-8")
        report = replace(report, json_path=json_path)
    return report


def render_evaluation_markdown(result: EvaluationResult) -> str:
    """Render evaluation runs as a workshop-paper-friendly table."""

    lines = [
        "# PaperPilot Evaluation",
        "",
        f"- Generated: {result.generated_at.isoformat()}",
        f"- Mode: {result.mode}",
        "",
        "## Summary Table",
        "",
        "| Scenario | Condition | Selected | Search Attempts | Replans | Deduped | PDF Success | Avg Relevance | Reflection Pass | Runtime | Fallbacks | Credits Used |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for run in result.runs:
        metrics = run.metrics
        lines.append(
            f"| {run.scenario_id} | {run.condition} | {metrics.selected_count} | "
            f"{metrics.search_attempts} | {metrics.replans} | {metrics.deduped_count} | "
            f"{metrics.pdf_success_rate:.2f} | {metrics.avg_relevance:.3f} | "
            f"{metrics.summary_reflection_pass_rate:.2f} | {metrics.runtime_seconds:.3f} | "
            f"{metrics.fallback_count} | {_format_optional_number(metrics.credits_used)} |"
        )

    lines.extend(["", "## Presentation Takeaways", ""])
    lines.extend(_presentation_takeaways(result))

    lines.extend(
        [
            "",
            "## Conditions",
            "",
            "- Baseline: arXiv only, query expansion off, PDF off, heuristic summary, agentic mode off.",
            "- Agentic: selected official sources, query expansion basic, PDF evidence on, reflection/fallback on, agentic mode policy.",
            "",
            "## Scenario Notes",
            "",
        ]
    )
    for scenario_id in dict.fromkeys(run.scenario_id for run in result.runs):
        scenario = _scenario(scenario_id)
        lines.append(f"- {scenario.id}: `{scenario.query}` - {scenario.expected_behavior}")

    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- Fixture mode is deterministic and cost-free, so it validates system behavior rather than real search recall.",
            "- Live mode depends on external API availability, source rate limits, and the selected summary backend.",
            "- Relevance is a lightweight reviewer signal for repeatable comparison, not a substitute for expert paper judgment.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _run_condition(
    *,
    mode: str,
    scenario: EvaluationScenario,
    condition: str,
    sources: tuple[str, ...],
    query_expansion: str,
    with_pdf: bool,
    top_k: int,
    pdf_max_pages: int,
    pdf_max_chars: int,
    summary_backend: str,
    summary_model: str | None,
    summary_detail: str,
    agentic_mode: str,
    max_agent_steps: int,
    output_dir: Path,
) -> EvaluationRun:
    workflow = _evaluation_workflow(mode, scenario.id)
    credits_before = _credits_used_value(summary_backend)
    started = time.perf_counter()
    report = workflow.run(
        scenario.query,
        days=14,
        max_results=20,
        top_k=top_k,
        min_relevance=0.8,
        sources=sources,
        query_expansion=query_expansion,
        max_query_variants=6,
        with_pdf=with_pdf,
        pdf_max_pages=pdf_max_pages,
        pdf_max_chars=pdf_max_chars,
        summary_backend=summary_backend,
        summary_model=summary_model,
        summary_detail=summary_detail,
        agentic_mode=agentic_mode,
        max_agent_steps=max_agent_steps,
        output_dir=output_dir,
    )
    runtime_seconds = time.perf_counter() - started
    credits_after = _credits_used_value(summary_backend)
    return EvaluationRun(
        scenario_id=scenario.id,
        condition=condition,
        query=scenario.query,
        metrics=_metrics_from_report(
            report,
            runtime_seconds=runtime_seconds,
            credits_before=credits_before,
            credits_after=credits_after,
        ),
        report_path=report.output_path,
    )


def _evaluation_workflow(mode: str, scenario_id: str) -> CurationWorkflow:
    if mode == "live":
        return CurationWorkflow()
    return CurationWorkflow(
        searcher=SearcherAgent(
            {
                "arxiv": _FixtureSearchSource(scenario_id, "arxiv"),
                "openalex": _FixtureSearchSource(scenario_id, "openalex"),
            },
            min_results=2,
        ),
        pdf_extractor=_FixturePdfExtractor(),
    )


def _metrics_from_report(
    report,
    *,
    runtime_seconds: float,
    credits_before: float | None,
    credits_after: float | None,
) -> EvaluationMetrics:
    selected_count = len(report.selected)
    avg_relevance = (
        sum(item.reviewed.score.relevance for item in report.selected) / selected_count if selected_count else 0.0
    )
    pdf_success_rate = (
        sum(1 for item in report.selected if item.evidence and item.evidence.available) / selected_count
        if selected_count
        else 0.0
    )
    reflection_pass_rate = (
        sum(1 for item in report.selected if item.summary.reflection.passed) / selected_count
        if selected_count
        else 0.0
    )
    unique_queries = {attempt.query for attempt in report.attempts}
    credits_used = (
        round(credits_after - credits_before, 6)
        if credits_before is not None and credits_after is not None and credits_after >= credits_before
        else None
    )
    return EvaluationMetrics(
        selected_count=selected_count,
        search_attempts=len(report.attempts),
        replans=max(0, len(unique_queries) - 1),
        deduped_count=report.deduped_count,
        pdf_success_rate=round(pdf_success_rate, 3),
        avg_relevance=round(avg_relevance, 3),
        summary_reflection_pass_rate=round(reflection_pass_rate, 3),
        runtime_seconds=round(runtime_seconds, 3),
        fallback_count=selected_count if report.summary_fallback_reason else 0,
        credits_before=credits_before,
        credits_after=credits_after,
        credits_used=credits_used,
    )


def _scenario(scenario_id: str) -> EvaluationScenario:
    try:
        return EVALUATION_SCENARIOS[scenario_id]
    except KeyError as exc:
        raise ValueError(f"unknown evaluation scenario: {scenario_id}") from exc


def _credits_used_value(summary_backend: str) -> float | None:
    if summary_backend != "factchat":
        return None
    try:
        balance = get_summary_credits("factchat")
    except SummaryBackendError:
        return None
    total = balance.get("total") if isinstance(balance, dict) else None
    used = total.get("used") if isinstance(total, dict) else None
    return float(used) if isinstance(used, int | float) else None


def _format_optional_number(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.3f}"


def _presentation_takeaways(result: EvaluationResult) -> list[str]:
    lines: list[str] = []
    by_scenario: dict[str, dict[str, EvaluationRun]] = {}
    for run in result.runs:
        by_scenario.setdefault(run.scenario_id, {})[run.condition] = run

    for scenario_id, runs in by_scenario.items():
        baseline = runs.get("baseline")
        agentic = runs.get("agentic")
        if baseline is None or agentic is None:
            continue
        selected_delta = agentic.metrics.selected_count - baseline.metrics.selected_count
        replan_delta = agentic.metrics.replans - baseline.metrics.replans
        dedupe_delta = agentic.metrics.deduped_count - baseline.metrics.deduped_count
        if baseline.metrics.selected_count == 0 and agentic.metrics.selected_count > 0:
            lines.append(
                f"- {scenario_id}: baseline은 0개를 선택했지만 agentic은 "
                f"{agentic.metrics.selected_count}개를 선택했습니다. 실패 회복 데모에 가장 적합합니다."
            )
        else:
            lines.append(
                f"- {scenario_id}: agentic selected delta {selected_delta:+d}, "
                f"replans delta {replan_delta:+d}, dedupe delta {dedupe_delta:+d}."
            )
        if agentic.metrics.pdf_success_rate > baseline.metrics.pdf_success_rate:
            lines.append(
                f"- {scenario_id}: agentic 조건은 PDF evidence success "
                f"{agentic.metrics.pdf_success_rate:.2f}로 요약 grounding을 추가했습니다."
            )
        if agentic.metrics.summary_reflection_pass_rate:
            lines.append(
                f"- {scenario_id}: summary reflection pass rate "
                f"{agentic.metrics.summary_reflection_pass_rate:.2f}를 기록했습니다."
            )

    if not lines:
        lines.append("- Compare each baseline/agentic row to explain whether replanning changed the outcome.")
    return lines


def _evaluation_to_json(result: EvaluationResult) -> dict[str, Any]:
    payload = asdict(result)
    payload["generated_at"] = result.generated_at.isoformat()
    payload["output_path"] = str(result.output_path) if result.output_path else None
    payload["json_path"] = str(result.json_path) if result.json_path else None
    for run in payload["runs"]:
        if run["report_path"] is not None:
            run["report_path"] = str(run["report_path"])
    return payload


class _FixturePdfExtractor:
    def fetch(self, paper: Paper, *, max_pages: int, max_chars: int) -> PaperEvidence:
        if not paper.pdf_url:
            return PaperEvidence(source="fixture-pdf", error="paper has no PDF URL")
        text = (
            f"{paper.title}. We propose an agentic paper curation workflow with tool use, "
            "query replanning, evidence extraction, benchmark evaluation, and limitation analysis. "
            "Experiments compare baseline and agentic settings on 3 scenarios."
        )
        return PaperEvidence(source="fixture-pdf", text=text[:max_chars], pages_read=min(max_pages, 3), total_pages=3)


class _FixtureSearchSource:
    def __init__(self, scenario_id: str, source: str) -> None:
        self.scenario_id = scenario_id
        self.source = source

    def __call__(self, query: str, *, days: int, max_results: int, **kwargs) -> tuple[Paper, ...]:
        papers = _fixture_papers(self.scenario_id, self.source, query.lower())
        return papers[:max_results]


def _fixture_papers(scenario_id: str, source: str, query: str) -> tuple[Paper, ...]:
    if scenario_id == "dlm_unlearning":
        dlm_fallback_queries = {"language model unlearning", "llm unlearning", "machine unlearning language models"}
        if source == "arxiv" and query in dlm_fallback_queries:
            return (
                _paper(
                    title="Learning What to Forget: Improving LLM Unlearning via Token Importance",
                    source=source,
                    source_id="2606.06320",
                    summary="We propose a language model unlearning method with experiments and ablations.",
                    doi=None,
                ),
            )
        if source == "openalex" and query in dlm_fallback_queries:
            return (
                _paper(
                    title="Learning What to Forget: Improving LLM Unlearning via Token Importance",
                    source=source,
                    source_id="openalex-dlm-1",
                    summary="We propose a language model unlearning method with experiments and ablations.",
                    doi="10.48550/arxiv.2606.06320",
                    citation_count=4,
                    venue="arXiv",
                ),
                _paper(
                    title="Benchmarking Machine Unlearning in Large Language Models",
                    source=source,
                    source_id="openalex-dlm-2",
                    summary="A benchmark for LLM unlearning evaluates forgetting and retained utility.",
                    citation_count=9,
                    venue="Workshop",
                ),
            )
        return ()

    if scenario_id == "multimodal_rag":
        if source == "arxiv" and "multimodal retrieval augmented generation" in query:
            return (
                _paper(
                    title="Multimodal RAG for Document Question Answering",
                    source=source,
                    source_id="2606.01001",
                    summary="We introduce a multimodal retrieval augmented generation pipeline with evaluation.",
                ),
            )
        if source == "openalex" and ("multimodal rag" in query or "vision-language rag" in query):
            return (
                _paper(
                    title="Multimodal RAG for Document Question Answering",
                    source=source,
                    source_id="openalex-rag-1",
                    summary="We introduce a multimodal retrieval augmented generation pipeline with evaluation.",
                    doi="10.1234/multimodal-rag",
                    citation_count=12,
                    venue="ACL Findings",
                ),
                _paper(
                    title="A Benchmark for Vision-Language Retrieval Augmented Generation",
                    source=source,
                    source_id="openalex-rag-2",
                    summary="This benchmark evaluates vision-language RAG on 5 document QA datasets.",
                    citation_count=18,
                    venue="EMNLP",
                ),
            )
        return ()

    if scenario_id == "agentic_ai_evaluation":
        if source == "arxiv" and "agentic ai evaluation benchmark" in query:
            return (
                _paper(
                    title="Evaluating Agentic AI Systems with Tool-Use Benchmarks",
                    source=source,
                    source_id="2606.02001",
                    summary="We present an agentic AI evaluation benchmark for planning, tool use, and reflection.",
                ),
            )
        if source == "openalex" and "agentic ai evaluation benchmark" in query:
            return (
                _paper(
                    title="Evaluating Agentic AI Systems with Tool-Use Benchmarks",
                    source=source,
                    source_id="openalex-agent-1",
                    summary="We present an agentic AI evaluation benchmark for planning, tool use, and reflection.",
                    doi="10.1234/agentic-eval",
                    citation_count=16,
                    venue="NeurIPS",
                ),
                _paper(
                    title="Failure Analysis for Agentic AI Evaluation",
                    source=source,
                    source_id="openalex-agent-2",
                    summary="We analyze failures in agentic AI evaluation with benchmark experiments.",
                    citation_count=6,
                    venue="ICLR Workshop",
                ),
            )
        return ()

    return ()


def _paper(
    *,
    title: str,
    source: str,
    source_id: str,
    summary: str,
    doi: str | None = None,
    citation_count: int | None = None,
    venue: str | None = None,
) -> Paper:
    published = datetime(2026, 6, 1, tzinfo=timezone.utc)
    url = f"https://arxiv.org/abs/{source_id}" if source == "arxiv" else f"https://openalex.org/{source_id}"
    pdf_url = f"https://arxiv.org/pdf/{source_id}" if source == "arxiv" else None
    return Paper(
        title=title,
        authors=("Mina Park", "Jon Bell"),
        summary=summary,
        published=published,
        updated=published,
        url=url,
        pdf_url=pdf_url,
        categories=("cs.AI", "cs.CL"),
        source_id=source_id,
        source=source,
        doi=doi,
        citation_count=citation_count,
        venue=venue,
    )
