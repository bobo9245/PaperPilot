from __future__ import annotations

from datetime import datetime, timezone

from paperpilot.models import (
    CurationReport,
    PaperSummary,
    ReviewedPaper,
    ReviewScore,
    SearchAttempt,
    SelectedPaper,
    TraceEvent,
)
from paperpilot.publisher import MarkdownPublisher


def test_markdown_publisher_writes_report(tmp_path, make_paper) -> None:
    reviewed = ReviewedPaper(
        paper=make_paper(
            source="arxiv, openalex",
            doi="10.1234/test",
            citation_count=12,
            venue="ACL",
        ),
        score=ReviewScore(
            relevance=1.0,
            novelty=0.7,
            experimental_strength=0.8,
            total=0.85,
            reason="query terms are strongly represented",
        ),
    )
    report = CurationReport(
        query="retrieval augmented generation",
        generated_at=datetime(2026, 1, 10, tzinfo=timezone.utc),
        attempts=(
            SearchAttempt(
                query="retrieval augmented generation",
                status="success",
                results_count=3,
                message="Enough recent candidates found.",
            ),
        ),
        trace=(
            TraceEvent(
                step="review",
                action="Score relevance, novelty, and experimental strength",
                input="1 candidate(s)",
                observation="1 candidate(s) passed",
                decision="Select top 1 paper(s).",
                status="completed",
            ),
        ),
        selected=(
            SelectedPaper(
                reviewed=reviewed,
                summary=PaperSummary(
                    problem="문제: test",
                    contribution="핵심 기여: test",
                    method="방법: test",
                    experiments="실험/결과: 5 datasets",
                    limitations="한계: test",
                ),
            ),
        ),
        min_relevance=0.8,
        categories=("cs.CL",),
        strict_search=True,
        candidate_count=1,
        deduped_count=0,
        with_pdf=False,
        summary_backend="auto",
        summary_model="custom-summary-model",
        summary_detail="deep",
        summary_fallback_reason="OPENAI_API_KEY is not set",
        scholar_links=True,
    )

    path = MarkdownPublisher(tmp_path).publish(report)
    log_path = tmp_path / "2026-01-10_retrieval-augmented-generation_log.md"

    assert path.name == "2026-01-10_retrieval-augmented-generation.md"
    assert log_path.exists()
    content = path.read_text(encoding="utf-8")
    assert "- Min relevance: 0.800" in content
    assert "- Categories: cs.CL" in content
    assert "- Search mode: strict title/abstract" in content
    assert "- Unique candidates: 1" in content
    assert "- Duplicates merged: 0" in content
    assert "- PDF evidence: Disabled" in content
    assert (
        "- Summary backend: auto, detail deep, model custom-summary-model, "
        "fallback: OPENAI_API_KEY is not set"
    ) in content
    assert "- Evidence: abstract only" in content
    assert "## Presentation Highlights" in content
    assert "Agent loop evidence" in content
    assert "## Project Alignment" in content
    assert "## Search Attempts" not in content
    assert "## Agent Trace" not in content
    assert "- Source: arxiv, openalex" in content
    assert "- DOI: 10.1234/test" in content
    assert "- Venue: ACL" in content
    assert "- Citations: 12" in content
    assert "- Google Scholar: https://scholar.google.com/scholar?q=Adaptive+Retrieval+Augmented+Generation" in content
    assert "Reviewer score: 0.850" in content
    assert "핵심 기여" in content

    log_content = log_path.read_text(encoding="utf-8")
    assert "# PaperPilot Run Log: retrieval augmented generation" in log_content
    assert "## Search Attempts" in log_content
    assert "| Source | Query | Status | Results | Note |" in log_content
    assert "## Agent Trace" in log_content
    assert "| review | Score relevance, novelty, and experimental strength |" in log_content
