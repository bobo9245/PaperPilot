from __future__ import annotations

from paperpilot.agents.searcher import SearcherAgent
from paperpilot.models import PaperEvidence
from paperpilot.workflow import CurationWorkflow


def test_workflow_fetches_pdf_evidence_for_selected_papers(make_paper, tmp_path) -> None:
    paper = make_paper(
        title="Retrieval Augmented Generation with Evidence",
        summary="We propose a retrieval augmented generation model with evaluation.",
    )

    def fake_search(query: str, **kwargs):
        return (paper,)

    class FakePdfExtractor:
        def fetch(self, paper, *, max_pages: int, max_chars: int):
            assert max_pages == 2
            assert max_chars == 32_000
            return PaperEvidence(
                source="pdf",
                text=(
                    "We propose a retrieval augmented generation pipeline. "
                    "Our approach uses a reranking model. "
                    "Experiments improve answer faithfulness by 32%. "
                    "Limitations include sensitivity to noisy retrieved documents."
                ),
                pages_read=2,
                total_pages=10,
            )

    workflow = CurationWorkflow(
        searcher=SearcherAgent(fake_search, min_results=1),
        pdf_extractor=FakePdfExtractor(),
    )

    report = workflow.run(
        "retrieval augmented generation",
        top_k=1,
        with_pdf=True,
        pdf_max_pages=2,
        pdf_max_chars=32_000,
        summary_backend="heuristic",
        output_dir=tmp_path,
    )

    assert report.with_pdf
    assert report.pdf_max_pages == 2
    assert report.pdf_max_chars == 32_000
    assert report.selected[0].evidence is not None
    assert report.selected[0].evidence.available
    assert "PDF 본문" in report.selected[0].summary.method
    assert "32%" in report.selected[0].summary.experiments
    assert report.output_path is not None
    content = report.output_path.read_text(encoding="utf-8")
    assert "- PDF evidence: Enabled, max pages 2, max chars 32000" in content


def test_workflow_records_auto_summary_fallback(make_paper, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("FACTCHAT_API_KEY", raising=False)
    monkeypatch.delenv("PAPERPILOT_FACTCHAT_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    paper = make_paper(
        title="Retrieval Augmented Generation with Evidence",
        summary="We propose a retrieval augmented generation model with evaluation on 6 datasets.",
    )

    def fake_search(query: str, **kwargs):
        return (paper,)

    workflow = CurationWorkflow(searcher=SearcherAgent(fake_search, min_results=1))

    report = workflow.run(
        "retrieval augmented generation",
        top_k=1,
        summary_backend="auto",
        summary_model="custom-summary-model",
        output_dir=tmp_path,
    )

    assert report.summary_backend == "auto"
    assert report.summary_model == "custom-summary-model"
    assert report.summary_detail == "standard"
    assert report.summary_fallback_reason == "FACTCHAT_API_KEY and OPENAI_API_KEY are not set"
    assert "핵심 기여" in report.selected[0].summary.contribution
    assert "OpenAI 요약 backend" not in report.selected[0].summary.contribution
