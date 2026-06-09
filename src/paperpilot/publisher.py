"""Markdown publishing for curation reports."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from paperpilot.models import CurationReport


class MarkdownPublisher:
    """Persist curation reports as Markdown files."""

    def __init__(self, output_dir: str | Path = "outputs") -> None:
        self.output_dir = Path(output_dir)

    def publish(self, report: CurationReport) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / _report_filename(report.query, report.generated_at.date())
        path.write_text(render_markdown(report), encoding="utf-8")
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
        f"- PDF evidence: {_format_pdf_mode(report.with_pdf, report.pdf_max_pages, report.pdf_max_chars)}",
        f"- Summary backend: {_format_summary_backend(report)}",
        "",
        "## Search Attempts",
        "",
        "| Query | Status | Results | Note |",
        "| --- | --- | ---: | --- |",
    ]

    for attempt in report.attempts:
        lines.append(
            f"| {_escape(attempt.query)} | {attempt.status} | {attempt.results_count} | {_escape(attempt.message)} |"
        )

    lines.extend(["", "## Selected Papers", ""])

    if not report.selected:
        lines.append("No papers were selected.")
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


def _report_filename(query: str, generated_date: date) -> str:
    return f"{generated_date.isoformat()}_{_slugify(query)}.md"


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
