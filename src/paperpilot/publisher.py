"""Markdown publishing for curation reports."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from urllib.parse import quote_plus

from paperpilot.models import CurationReport


class MarkdownPublisher:
    """Persist curation reports as Markdown files."""

    def __init__(self, output_dir: str | Path = "outputs") -> None:
        self.output_dir = Path(output_dir)
        self.last_log_path: Path | None = None

    def publish(self, report: CurationReport) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / _report_filename(report.query, report.generated_at.date())
        log_path = self.output_dir / _log_filename(report.query, report.generated_at.date())
        path.write_text(render_markdown(report), encoding="utf-8")
        log_path.write_text(render_log_markdown(report), encoding="utf-8")
        self.last_log_path = log_path
        return path


def render_markdown(report: CurationReport) -> str:
    lines = [
        f"# PaperPilot Curation: {report.query}",
        "",
        f"- Generated: {report.generated_at.isoformat()}",
        f"- Selected papers: {len(report.selected)}",
        f"- Min relevance: {_format_min_relevance(report.min_relevance)}",
        f"- Categories: {', '.join(report.categories) if report.categories else 'Any'}",
        f"- Search mode: {_format_search_mode(report.strict_search)}",
        f"- Agentic mode: {report.agentic_mode}, max steps {report.max_agent_steps}",
        f"- Unique candidates: {report.candidate_count}",
        f"- Duplicates merged: {report.deduped_count}",
        f"- PDF evidence: {_format_pdf_mode(report.with_pdf, report.pdf_max_pages, report.pdf_max_chars)}",
        f"- Summary backend: {_format_summary_backend(report)}",
        "",
        "## Presentation Highlights",
        "",
        *_presentation_highlights(report),
        "",
        "## Project Alignment",
        "",
        "- Problem: 연구자가 매주 쏟아지는 최신 논문을 검색하고, 중복을 제거하고, PDF를 훑어 새로움과 한계를 파악하는 과정이 반복적으로 오래 걸립니다.",
        "- User: 최신 연구 동향을 빠르게 따라가야 하는 대학원생과 연구자.",
        "- Context: 검색어가 좁으면 후보를 놓치고, 검색어가 넓으면 약한 후보가 섞이는 논문 탐색 상황.",
        "- Agentic Fit: PaperPilot은 query planning, multi-source tool use, observation, replanning, review, PDF evidence extraction, reflection/fallback을 연결해 반복 가능한 큐레이션 workflow를 만듭니다.",
    ]

    lines.extend(["", "## Selected Papers", ""])

    if not report.selected:
        lines.append("No papers were selected.")
        if report.failure_analysis:
            lines.extend(["", "## Failure Analysis", ""])
            lines.extend(_failure_analysis_lines(report))
        return "\n".join(lines).rstrip() + "\n"

    for index, item in enumerate(report.selected, start=1):
        paper = item.reviewed.paper
        score = item.reviewed.score
        lines.extend(
            [
                f"## {index}. {paper.title}",
                "",
                f"- Authors: {paper.authors_text}",
                f"- Published: {paper.published.date().isoformat()}",
                f"- URL: {paper.url}",
                f"- PDF: {paper.pdf_url or 'N/A'}",
                f"- Source: {paper.source}",
                f"- DOI: {paper.doi or 'N/A'}",
                f"- Venue: {paper.venue or 'N/A'}",
                f"- Citations: {_format_citations(paper.citation_count)}",
                *([f"- Google Scholar: {_google_scholar_link(paper.title)}"] if report.scholar_links else []),
                f"- Evidence: {_format_evidence(item.evidence)}",
                (
                    "- Reviewer score: "
                    f"{score.total:.3f} "
                    f"(relevance {score.relevance:.3f}, novelty {score.novelty:.3f}, "
                    f"experiments {score.experimental_strength:.3f})"
                ),
                f"- Selection reason: {score.reason}",
                "",
                item.summary.as_markdown(),
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def render_log_markdown(report: CurationReport) -> str:
    lines = [
        f"# PaperPilot Run Log: {report.query}",
        "",
        f"- Generated: {report.generated_at.isoformat()}",
        f"- Selected papers: {len(report.selected)}",
        f"- Min relevance: {_format_min_relevance(report.min_relevance)}",
        f"- Categories: {', '.join(report.categories) if report.categories else 'Any'}",
        f"- Search mode: {_format_search_mode(report.strict_search)}",
        f"- Agentic mode: {report.agentic_mode}, max steps {report.max_agent_steps}",
        f"- Unique candidates: {report.candidate_count}",
        f"- Duplicates merged: {report.deduped_count}",
        f"- PDF evidence: {_format_pdf_mode(report.with_pdf, report.pdf_max_pages, report.pdf_max_chars)}",
        f"- Summary backend: {_format_summary_backend(report)}",
        "",
        "## Search Attempts",
        "",
        "| Source | Query | Status | Results | Note |",
        "| --- | --- | --- | ---: | --- |",
    ]

    for attempt in report.attempts:
        lines.append(
            f"| {_escape(attempt.source)} | {_escape(attempt.query)} | {attempt.status} | "
            f"{attempt.results_count} | {_escape(attempt.message)} |"
        )

    lines.extend(["", "## Agent Trace", ""])
    if report.trace:
        for phase, events in _group_trace_by_phase(report.trace):
            lines.extend(
                [
                    f"### {phase}",
                    "",
                    "| Step | Action | Input | Observation | Decision | Status |",
                    "| --- | --- | --- | --- | --- | --- |",
                ]
            )
            for event in events:
                lines.append(
                    f"| {_escape(event.step)} | {_escape(event.action)} | {_escape(event.input)} | "
                    f"{_escape(event.observation)} | {_escape(event.decision)} | {_escape(event.status)} |"
                )
            lines.append("")
    else:
        lines.append("No trace events were recorded.")

    if report.failure_analysis and not report.selected:
        lines.extend(["", "## Failure Analysis", ""])
        lines.extend(_failure_analysis_lines(report))

    return "\n".join(lines).rstrip() + "\n"


def _report_filename(query: str, generated_date: date) -> str:
    return f"{generated_date.isoformat()}_{_slugify(query)}.md"


def _log_filename(query: str, generated_date: date) -> str:
    return f"{generated_date.isoformat()}_{_slugify(query)}_log.md"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or "curation"


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _format_min_relevance(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.3f}"


def _format_search_mode(value: bool | None) -> str:
    if value is None:
        return "N/A"
    return "strict title/abstract" if value else "broad all-fields"


def _format_pdf_mode(enabled: bool, max_pages: int | None, max_chars: int | None) -> str:
    if not enabled:
        return "Disabled"
    pages = f", max pages {max_pages}" if max_pages else ""
    chars = f", max chars {max_chars}" if max_chars else ""
    return f"Enabled{pages}{chars}"


def _format_evidence(evidence) -> str:
    if evidence is None:
        return "abstract only"
    if evidence.available:
        total = f"/{evidence.total_pages}" if evidence.total_pages is not None else ""
        return f"PDF text, pages {evidence.pages_read}{total}"
    return f"abstract only ({evidence.error or 'PDF evidence unavailable'})"


def _format_summary_backend(report: CurationReport) -> str:
    model = f", model {report.summary_model}" if report.summary_model else ""
    fallback = f", fallback: {report.summary_fallback_reason}" if report.summary_fallback_reason else ""
    return f"{report.summary_backend}, detail {report.summary_detail}{model}{fallback}"


def _format_citations(value: int | None) -> str:
    return "N/A" if value is None else str(value)


def _presentation_highlights(report: CurationReport) -> list[str]:
    query_variants = len(tuple(dict.fromkeys(attempt.query for attempt in report.attempts)))
    sources = len(tuple(dict.fromkeys(attempt.source for attempt in report.attempts)))
    expand_actions = _trace_action_count(report, "expand_query")
    broad_actions = _trace_action_count(report, "try_broad_search") + _trace_text_count(report, "broad-search")
    skipped_sources = _trace_action_count(report, "skip_rate_limited_source")
    pdf_successes = sum(1 for item in report.selected if item.evidence and item.evidence.available)
    reflection_passes = sum(1 for item in report.selected if item.summary.reflection.passed)

    recovery_parts: list[str] = []
    if expand_actions:
        recovery_parts.append(f"query expansion {expand_actions}회")
    if broad_actions:
        recovery_parts.append("broad search recovery")
    if skipped_sources:
        recovery_parts.append(f"rate-limited source skip {skipped_sources}회")
    if report.summary_fallback_reason:
        recovery_parts.append("summary fallback")
    recovery = ", ".join(recovery_parts) if recovery_parts else "별도 복구 없이 후보 pool을 안정적으로 통과"

    lines = [
        "- Demo thesis: PaperPilot은 검색 결과를 한 번 요약하는 도구가 아니라, 관찰 결과에 따라 다음 행동을 바꾸는 논문 큐레이션 agent입니다.",
        (
            f"- Agent loop evidence: {len(report.attempts)} search attempt(s), "
            f"{query_variants} query variant(s), {sources} source(s), "
            f"{report.deduped_count} duplicate merge(s)를 기록했습니다."
        ),
        f"- Recovery story: {recovery}.",
    ]
    if report.selected:
        first_title = report.selected[0].reviewed.paper.title
        lines.extend(
            [
                (
                    f"- Grounded output: {len(report.selected)} paper(s) selected, "
                    f"PDF evidence {pdf_successes}/{len(report.selected)}, "
                    f"summary reflection {reflection_passes}/{len(report.selected)} passed."
                ),
                f"- Demo path: 결과 보고서의 `{_trim_for_highlight(first_title)}` 요약과 별도 log 파일의 Search Attempts/Agent Trace를 함께 보여주면 됩니다.",
            ]
        )
    else:
        lines.extend(
            [
                "- Grounded output: 선택된 논문이 없어도 약한 후보를 억지로 채우지 않고 실패 분석을 남깁니다.",
                "- Demo path: 별도 log 파일의 Search Attempts/Agent Trace와 결과 보고서의 Failure Analysis를 함께 보여주면 됩니다.",
            ]
        )
    return lines


def _trace_action_count(report: CurationReport, action: str) -> int:
    return sum(1 for event in report.trace if event.step == "act" and action in event.action)


def _trace_text_count(report: CurationReport, needle: str) -> int:
    return sum(
        1
        for event in report.trace
        if needle.lower() in " ".join([event.action, event.observation, event.decision]).lower()
    )


def _trim_for_highlight(value: str, max_chars: int = 96) -> str:
    compact = " ".join(value.split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rstrip() + "..."


def _google_scholar_link(title: str) -> str:
    return f"https://scholar.google.com/scholar?q={quote_plus(title)}"


def _group_trace_by_phase(trace) -> tuple[tuple[str, tuple[object, ...]], ...]:
    grouped: dict[str, list[object]] = {}
    for event in trace:
        grouped.setdefault(_trace_phase(event), []).append(event)
    order = (
        "Plan",
        "Search/Observe",
        "Replan",
        "Review",
        "Evidence Recovery",
        "Summary Reflection",
        "Failure Analysis",
    )
    return tuple((phase, tuple(grouped[phase])) for phase in order if phase in grouped)


def _trace_phase(event) -> str:
    text = " ".join([event.step, event.action, event.input, event.decision]).lower()
    if event.step == "plan_query":
        return "Plan"
    if event.step in {"dedupe", "review"}:
        return "Review"
    if "pdf" in text or "abstract fallback" in text:
        return "Evidence Recovery"
    if "summary" in text or "reflection" in text or "heuristic" in text:
        return "Summary Reflection"
    if "failure" in text or "stop_with_failure_analysis" in text:
        return "Failure Analysis"
    if "expand_query" in text or "try_broad_search" in text or "skip_rate_limited_source" in text or event.step == "replan":
        return "Replan"
    return "Search/Observe"


def _failure_analysis_lines(report: CurationReport) -> list[str]:
    lines = [
        f"- Unique candidates collected: {report.candidate_count}",
        f"- Minimum relevance threshold: {_format_min_relevance(report.min_relevance)}",
    ]
    rate_limited = [
        event.input
        for event in report.trace
        if "skip_rate_limited_source" in event.action or "rate-limit" in event.observation.lower()
    ]
    if rate_limited:
        lines.append(f"- Rate-limited source observations: {', '.join(dict.fromkeys(rate_limited))}")
    if report.candidate_count == 0:
        lines.append("- Likely cause: the query was too narrow for the selected sources or all usable sources failed.")
    else:
        lines.append("- Likely cause: candidates were found but did not pass the reviewer relevance gate.")
    lines.append("- Next action: broaden the query, add sources such as OpenAlex, lower `--min-relevance`, or enable `--broad-search`.")
    return lines
