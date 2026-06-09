from __future__ import annotations

from datetime import datetime, timezone

from paperpilot.models import (
    CurationReport,
    PaperSummary,
    ReviewedPaper,
    ReviewScore,
    SearchAttempt,
    SelectedPaper,
)
from paperpilot.publisher import MarkdownPublisher


def test_markdown_publisher_writes_report(tmp_path, make_paper) -> None:
    reviewed = ReviewedPaper(
        paper=make_paper(),
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
        with_pdf=False,
        summary_backend="auto",
        summary_model="custom-summary-model",
        summary_detail="deep",
        summary_fallback_reason="OPENAI_API_KEY is not set",
    )

    path = MarkdownPublisher(tmp_path).publish(report)

    assert path.name == "2026-01-10_retrieval-augmented-generation.md"
    content = path.read_text(encoding="utf-8")
    assert "## Search Attempts" in content
    assert "- Min relevance: 0.800" in content
    assert "- Categories: cs.CL" in content
    assert "- Search mode: strict title/abstract" in content
    assert "- PDF evidence: Disabled" in content
    assert (
        "- Summary backend: auto, detail deep, model custom-summary-model, "
        "fallback: OPENAI_API_KEY is not set"
    ) in content
    assert "- Evidence: abstract only" in content
    assert "Reviewer score: 0.850" in content
    assert "핵심 기여" in content
